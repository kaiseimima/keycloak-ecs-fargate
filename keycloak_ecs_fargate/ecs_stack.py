from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_rds as rds,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    Stack
)

KEYCLOAK_IMAGE = 'ecr'

class EcsStack(Stack):

    # Setting for ECS/Fargate
    # Fargate Task Definition, Container, ECS Service, ALB TargetGroup

    # def __init__(self, scope: Construct, construct_id: str, ecs_cluster: ecs.Cluster, listener: elbv2.ApplicationListener, db_cluster: rds.DatabaseCluster, sg:ec2.SecurityGroup, **kwards) -> None:
    def __init__(self, scope: Construct, construct_id: str, ecs_cluster: ecs.Cluster, listener: elbv2.ApplicationListener, db_instance: rds.DatabaseInstance, sg:ec2.SecurityGroup, **kwards) -> None:
        super().__init__(scope, construct_id, **kwards)

        # Fargate Task Definition
        ecs_task_definition = ecs.FargateTaskDefinition(self, 'TaskDefinition',
                                                        runtime_platform=ecs.RuntimePlatform(
                                                            operating_system_family=ecs.OperatingSystemFamily.LINUX,
                                                            cpu_architecture=ecs.CpuArchitecture.X86_64
                                                        ),
                                                        cpu=1024,
                                                        memory_limit_mib=2048
                                                        )

        # Container
        container = ecs_task_definition.add_container('keycloak',
                                                      image=ecs.ContainerImage.from_registry('878518084785.dkr.ecr.us-east-1.amazonaws.com/keycloak-ecs-fargate:latest'),
                                                      environment={
                                                          'KC_DB_URL': f'jdbc:mysql://{db_instance.instance_endpoint.hostname}:3306/keycloak',
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
                                                          stream_prefix='keycloak',
                                                          log_retention=logs.RetentionDays.ONE_DAY
                                                          ),
                                                    #   command=['start', '--optimized']  
                                                      command=['start-dev']                               
                                                      )

        # Ecs Service
        ecs_service = ecs.FargateService(self, 'EcsService',
                                         cluster=ecs_cluster,
                                         task_definition=ecs_task_definition,
                                         vpc_subnets=ec2.SubnetSelection(
                                             subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                                         ),
                                         security_groups=[sg]
                                         )
        
        # ALB TargetGroup
        # ecs_service.register_load_balancer_targets(
        #     ecs.EcsTarget(
        #         container_name='keycloak',
        #         container_port=80,
        #         new_target_group_id='ECS',
        #         listener=ecs.ListenerConfig.application_listener(
        #             listener,
        #             protocol=elbv2.ApplicationProtocol.HTTP
        #         )
        #     )
        # )
        
        
        listener.add_targets('ECS',
                             port=8080,
                             targets=[ecs_service.load_balancer_target(
                                 container_name='keycloak',
                                 container_port=8080
                             )]
                             )