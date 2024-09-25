from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_rds as rds,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_servicediscovery as servicediscovery,
    Stack,
    Duration,
    SecretValue
)
from constructs import Construct

class TestKeycloakEcsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "Vpc", max_azs=2)

        # ECS Cluster
        ecs_cluster = ecs.Cluster(self, "EcsCluster", vpc=vpc)

        # Security Groups
        ecs_security_group = ec2.SecurityGroup(self, 'EcsSecurityGroup', vpc=vpc)
        rds_security_group = ec2.SecurityGroup(self, 'RdsSecurityGroup', vpc=vpc)
        lb_security_group = ec2.SecurityGroup(self, 'LBSecurityGroup', vpc=vpc)
        ecs_security_group.add_ingress_rule(lb_security_group, ec2.Port.tcp(8080), "Allow traffic from Load Balancer")
        rds_security_group.add_ingress_rule(ecs_security_group, ec2.Port.tcp(3306), "Allow MySQL access from ECS")
        


        # MySQL RDS Instance
        db_instance = rds.DatabaseInstance(self, "RDSInstance",
                                           engine=rds.DatabaseInstanceEngine.mysql(
                                               version=rds.MysqlEngineVersion.VER_8_0_35
                                           ),
                                           vpc=vpc,
                                           credentials=rds.Credentials.from_username(
                                               username="dbuser",
                                               password=SecretValue.plain_text("dbpassword")
                                           ),
                                           database_name='keycloak',
                                           vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                           security_groups=[rds_security_group]
                                           )

        # Log Group for Keycloak
        log_group = logs.LogGroup(self, 'KeycloakLogGroup', retention=logs.RetentionDays.ONE_WEEK)
        
        # Task execution role
        execution_role = iam.Role(self, "TaskExecutionRole",
                          assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
                         )
        execution_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"))

        # Fargate Task Definition with ARM64 architecture
        task_definition = ecs.FargateTaskDefinition(self, "TaskDef", memory_limit_mib=2048, cpu=1024, 
                                                    execution_role=execution_role,
                                                    runtime_platform=ecs.RuntimePlatform(
                                                        operating_system_family=ecs.OperatingSystemFamily.LINUX,
                                                        cpu_architecture=ecs.CpuArchitecture.ARM64  # Set ARM64
                                                    ))

        # Keycloak Container
        container = task_definition.add_container("KeycloakContainer",
                                                  image=ecs.ContainerImage.from_registry("878518084785.dkr.ecr.us-east-1.amazonaws.com/keycloak-ecs-fargate"),
                                                  environment={
                                                      'KC_DB_URL': f'jdbc:mysql://{db_instance.db_instance_endpoint_address}:3306/keycloak',
                                                      'KEYCLOAK_ADMIN': 'admin',
                                                      'KEYCLOAK_ADMIN_PASSWORD': 'admin',
                                                      'KC_DB_VENDOR': 'mysql',
                                                      'KC_DB_USER': 'dbuser',
                                                      'KC_DB_PASSWORD': 'dbpassword',
                                                      'KC_DB_DATABASE': 'keycloak'
                                                  },
                                                  logging=ecs.AwsLogDriver(
                                                      log_group=log_group,
                                                      stream_prefix="keycloak"
                                                  ),
                                                  command=["start-dev"]
                                                  )

        container.add_port_mappings(ecs.PortMapping(container_port=8080))

        # Fargate Service
        ecs_service = ecs.FargateService(self, "KeycloakService",
                                         cluster=ecs_cluster,
                                         task_definition=task_definition,
                                         desired_count=1,
                                         security_groups=[ecs_security_group],
                                         vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS))

        # Application Load Balancer
        lb = elbv2.ApplicationLoadBalancer(self, "LB", vpc=vpc, internet_facing=True, security_group=lb_security_group)

        listener = lb.add_listener("PublicListener", port=80, open=True)
        listener.add_targets("ECS",
                             port=8080,
                             targets=[ecs_service],
                             health_check=elbv2.HealthCheck(path="/auth"))
        

        # EC2 Instance for testing (internal access to VPC)
        ec2_security_group = ec2.SecurityGroup(self, 'EC2SecurityGroup', vpc=vpc)
        ec2_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "Allow SSH access from anywhere")
        rds_security_group.add_ingress_rule(ec2_security_group, ec2.Port.tcp(3306), "Allow MySQL access from EC2")

        ec2_instance = ec2.Instance(self, 'TestEC2Instance',
                                    instance_type=ec2.InstanceType('t3.micro'),
                                    machine_image=ec2.AmazonLinuxImage(),
                                    vpc=vpc,
                                    key_name='my-key-pair',  # Set your EC2 key pair name here
                                    vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                    security_group=ec2_security_group)

        # Output the Load Balancer DNS Name and EC2 instance public IP
        self.lb_dns = lb.load_balancer_dns_name
        self.ec2_public_ip = ec2_instance.instance_public_ip
