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

        # ALB
        self.lb = elbv2.ApplicationLoadBalancer(self, 'LB',
                                                vpc=vpc,
                                                vpc_subnets=ec2.SubnetSelection(
                                                    subnet_type=ec2.SubnetType.PUBLIC
                                                    ),
                                                internet_facing=True
                                                )
        
        self.listener = self.lb.add_listener('Listener',
                                             port=80,
                                             open=True
                                             )
        
        # DB (auroraPostgreSQL)
        db_cluster = rds.DatabaseCluster(self, 'AuroraCluster',
                                         engine=rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_16_1),
                                         vpc=vpc,
                                         credentials=rds.Credentials.from_username(
                                             username='keycloak',
                                             # This for testing
                                             password=SecretValue.unsafe_plain_text('password')
                                         ),
                                         deletion_protection=False,
                                        #  security_groups=[aurora_security_group],
                                         vpc_subnets=ec2.SubnetSelection(
                                             subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                                         ),
                                         writer=rds.ClusterInstance.serverless_v2(
                                             'ClusterInstance',
                                             scale_with_writer=True
                                             )
        )

        # ecsCluster
        self.ecs_cluster = ecs.Cluster(self, 'EcsCluster',
                                       cluster_name='keycloak-ecs-cluster',
                                       container_insights=True,
                                       enable_fargate_capacity_providers=True,
                                       vpc=vpc
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
        #                                  cluster=ecs_cluster,
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
        #             listener,
        #             protocol=elbv2.ApplicationProtocol.HTTP
        #         )
        #     )
        # )
        # #################################################################################################