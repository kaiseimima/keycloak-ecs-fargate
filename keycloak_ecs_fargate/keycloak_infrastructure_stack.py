from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_rds as rds,
    aws_route53 as route53,
    aws_secretsmanager as secretmanager,
    aws_certificatemanager as acme,
    aws_logs as logs,
    Stack, SecretValue
)

class KeycloakInfrastructureStack(Stack):

    # setting for infrastructure
    # vpc, alb, db(rds), cluster
    
    def __init__(self, scope: Construct, construct_id: str, **kwards) -> None:
        super().__init__(scope, construct_id, **kwards)

        # VPC
        vpc = ec2.Vpc(
            self, "Vpc",
            ip_addresses=ec2.IpAddresses.cidr('10.1.0.0/20'),
            max_azs=2,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            restrict_default_security_group=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=28,
                    name='public',
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=28,
                    name='private',
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=28,
                    name='database',
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                )
            ]
        )
        
        
        # ALB SecurityGroup
        lbSecurityGroup = ec2.SecurityGroup(self, 'LBSecurityGroup',
                                            vpc=vpc,
                                            description='ALB Securitygroup: Allow HTTP traffic to ALB',
                                            allow_all_outbound=True
                                            )
        # lbSecurityGroup.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), 'Allow HTTPS traffic from anywhere')
        lbSecurityGroup.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), 'ALB Securitygroup: Allow HTTP traffic from anywhere')
        
        
        # ECS SecurityGroup
        self.ecsSecurityGroup = ec2.SecurityGroup(self, 'EcsSecurityGroup',
                                                  vpc=vpc,
                                                  description='Ecs Securitygroup: Allow access from private network',
                                                  allow_all_outbound=True
                                                  )
        self.ecsSecurityGroup.add_ingress_rule(lbSecurityGroup, ec2.Port.tcp(9000), 'Allow traffic for health checks')
        self.ecsSecurityGroup.add_ingress_rule(lbSecurityGroup, ec2.Port.tcp(80), 'Allow traffic from ALB to Fargate')
        # self.ecsSecurityGroup.add_ingress_rule(lbSecurityGroup, ec2.Port.tcp(8443), 'Allow traffic from ALB to Fargate')
        
        # EC2 Security Group for SSH access
        ec2_security_group = ec2.SecurityGroup(self, 'EC2SecurityGroup',
                                               vpc=vpc,
                                               description='Ec2 Securitygroup: Allow SSH access to EC2 instance',
                                               allow_all_outbound=True
                                               )
        ec2_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), 'Allow SSH access from anywhere')
        
        
        # RDS SecurityGroup
        dbSecurityGroup = ec2.SecurityGroup(self, 'MySQLSG',
                                                vpc=vpc,
                                                # description='Allow access to Postgresql from private network',
                                                description='MySQL Securitygroup: Allow access to Mysql from private network'
                                                )
        dbSecurityGroup.add_ingress_rule(self.ecsSecurityGroup, ec2.Port.tcp(3306), 'Allow mysql access from private network')
        dbSecurityGroup.add_ingress_rule(ec2_security_group, ec2.Port.tcp(3306), 'Allow EC2 to access MySQL')
        
        
        # ALB
        self.lb = elbv2.ApplicationLoadBalancer(self, 'LB',
                                                vpc=vpc,
                                                vpc_subnets=ec2.SubnetSelection(
                                                    subnet_type=ec2.SubnetType.PUBLIC
                                                    ),
                                                internet_facing=True,
                                                security_group=lbSecurityGroup
                                                )
        
        self.listener = self.lb.add_listener('Listener',
                                             port=80,
                                             open=True
                                             )
        
        # EC2 Instance (Bastion Host)
        ec2_instance = ec2.Instance(self, 'BastionHost',
                                    instance_type=ec2.InstanceType('t3.micro'),
                                    machine_image=ec2.AmazonLinuxImage(),
                                    vpc=vpc,
                                    security_group=ec2_security_group,
                                    key_name='my-key-pair',
                                    vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
                                    )
        
        
        # mysql (db_instance)
        self.db_instance = rds.DatabaseInstance(self, 'RDSInstance',
                                         engine=rds.DatabaseInstanceEngine.mysql(
                                             version=rds.MysqlEngineVersion.VER_8_0_35
                                         ),
                                         vpc=vpc,
                                         instance_type=ec2.InstanceType.of(
                                            ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
                                        ),
                                         database_name='keycloak',
                                         credentials=rds.Credentials.from_username(
                                             username='dbuser',
                                            #  password='dbpassword'
                                             password=SecretValue.plain_text('dbpassword')
                                         ),
                                         deletion_protection=False,
                                         security_groups=[dbSecurityGroup],
                                         vpc_subnets=ec2.SubnetSelection(
                                             subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                                         ),
                                         cloudwatch_logs_exports=['error', 'general', 'slowquery'],  # エクスポートするログ
                                         cloudwatch_logs_retention=logs.RetentionDays.ONE_WEEK,  # ログの保持期間
        )

        # ecsCluster
        self.ecs_cluster = ecs.Cluster(self, 'EcsCluster',
                                       cluster_name='keycloak-ecs-cluster',
                                       container_insights=True,
                                       enable_fargate_capacity_providers=True,
                                       vpc=vpc
                                       )
        
        # test keycloak
        
        ecs_task_definition = ecs.FargateTaskDefinition(self, 'TaskDefinition',
                                                        runtime_platform=ecs.RuntimePlatform(
                                                            operating_system_family=ecs.OperatingSystemFamily.LINUX,
                                                            cpu_architecture=ecs.CpuArchitecture.ARM64
                                                        ),
                                                        cpu=512,
                                                        memory_limit_mib=1024
                                                        )
        
        
        container = ecs_task_definition.add_container('keycloak',
                                                      image=ecs.ContainerImage.from_registry('878518084785.dkr.ecr.us-east-1.amazonaws.com/keycloak-ecs-fargate:latest'),
                                                      environment={
                                                          'KC_DB_URL': f'jdbc:mysql://{self.db_instance.instance_endpoint.hostname}:3306/keycloak',
                                                          'KEYCLOAK_ADMIN': 'admin',
                                                          'KEYCLOAK_ADMIN_PASSWORD': 'admin',
                                                          'KC_DB_VENDOR': 'mysql',
                                                          'KC_DB_USER': 'dbuser',
                                                          'KC_DB_PASSWORD': 'dbpassword',
                                                          'KC_DB_DATABASE': 'keycloak',
                                                          'KC_HOSTNAME_STRICT': 'false', 
                                                      },
                                                      port_mappings=[
                                                          ecs.PortMapping(
                                                              container_port=8080,
                                                              protocol=ecs.Protocol.TCP
                                                          )
                                                      ],
                                                      logging=ecs.AwsLogDriver(
                                                          log_group=logs.LogGroup(self, 'KeycloakLogGroup',
                                                                                  retention=logs.RetentionDays.ONE_DAY),
                                                          stream_prefix='keycloak',
                                                          mode=ecs.AwsLogDriverMode.NON_BLOCKING
                                                          ),
                                                    #   command=['start', '--optimized']  
                                                      command=['start-dev']                               
                                                      )
        
        ecs_service = ecs.FargateService(self, 'EcsService',
                                         cluster=self.ecs_cluster,
                                         task_definition=ecs_task_definition,
                                         vpc_subnets=ec2.SubnetSelection(
                                             subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                                         ),
                                         security_groups=[self.ecsSecurityGroup]
                                         )
        
        ecs_service.register_load_balancer_targets(
            ecs.EcsTarget(
                container_name='keycloak',
                container_port=8080,
                new_target_group_id='ECS',
                listener=ecs.ListenerConfig.application_listener(
                    self.listener,
                    protocol=elbv2.ApplicationProtocol.HTTP
                )
            )
        )
        

        # ##################################  test with using nginx ######################################
        # # Fargate Task Definition
        # ecs_task_definition = ecs.FargateTaskDefinition(self, 'TaskDefinition',
        #                                                 runtime_platform=ecs.RuntimePlatform(
        #                                                     operating_system_family=ecs.OperatingSystemFamily.LINUX,
        #                                                     cpu_architecture=ecs.CpuArchitecture.X86_64
        #                                                 ),
        #                                                 cpu=256,
        #                                                 memory_limit_mib=512
        # )

        # # log_group = logs.LogGroup(self, 'EcsLogGroup', 
        # #                           retention=logs.RetentionDays.ONE_WEEK  # ログの保持期間を設定
        # #                           )

        # # Container
        # container = ecs_task_definition.add_container('nginx',
        #                                             image=ecs.ContainerImage.from_registry('nginx'),
        #                                             # logging=ecs.LogDriver.aws_logs(
        #                                             #     stream_prefix='nginx',  # CloudWatch Logsに表示されるログのプレフィックス
        #                                             #     log_group=log_group
        #                                             #     ),
        #                                             port_mappings=[
        #                                                 ecs.PortMapping(
        #                                                     container_port=80,
        #                                                      protocol=ecs.Protocol.TCP
        #                                                 )
        #                                             ]
        # )

        # # Ecs Service
        # ecs_service = ecs.FargateService(self, 'EcsService',
        #                                  cluster=self.ecs_cluster,
        #                                  task_definition=ecs_task_definition,
        #                                  vpc_subnets=ec2.SubnetSelection(
        #                                      subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        #                                      )
        #                                      )
        
        # # ALB TargetGroup
        # ecs_service.register_load_balancer_targets(
        #     ecs.EcsTarget(
        #         container_name='nginx',
        #         container_port=80,
        #         new_target_group_id='ECS',
        #         listener=ecs.ListenerConfig.application_listener(
        #             self.listener,
        #             protocol=elbv2.ApplicationProtocol.HTTP
        #         )
        #     )
        # )
        # #################################################################################################
        
        
        
        
        
        
        