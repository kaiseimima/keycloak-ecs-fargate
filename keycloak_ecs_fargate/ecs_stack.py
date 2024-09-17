from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    Stack
)

CUSTOM_IMAGE = 'quay.io/3sky/keycloak-aurora:latest'

class EcsStack(Stack):

    # Setting for ECS/Fargate
    # Fargate Task Definition, Container, ECS Service, ALB TargetGroup

    def __init__(self, scope: Construct, construct_id: str, ecs_cluster: ecs.Cluster, listener: elbv2.ApplicationListener, **kwards) -> None:
        super().__init__(scope, construct_id, **kwards)

        # Fargate Task Definition
        ecs_task_definition = ecs.FargateTaskDefinition(self, 'TaskDefinition',
                                                        runtime_platform=ecs.RuntimePlatform(
                                                        operating_system_family=ecs.OperatingSystemFamily.LINUX,
                                                        cpu_architecture=ecs.CpuArchitecture.X86_64
                                                        ),
                                                        cpu=256,
                                                        memory_limit_mib=512
        )

        # Container
        container = ecs_task_definition.add_container('keycloak',
                                                      image=ecs.ContainerImage.from_registry('quay.io/keycloak/keycloak:24.0'),
                                                      port_mappings=[
                                                          ecs.PortMapping(
                                                              container_port=80,
                                                              protocol=ecs.Protocol.TCP
                                                          )
                                                      ]
        )

        # Ecs Service
        ecs_service = ecs.FargateService(self, 'EcsService',
                                         cluster=ecs_cluster,
                                         task_definition=ecs_task_definition,
                                         vpc_subnets=ec2.SubnetSelection(
                                             subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                                         )
                                         )
        
        # ALB TargetGroup
        ecs_service.register_load_balancer_targets(
            ecs.EcsTarget(
                container_name='keycloak',
                container_port=80,
                new_target_group_id='ECS',
                listener=ecs.ListenerConfig.application_listener(
                    listener,
                    protocol=elbv2.ApplicationProtocol.HTTP
                )
            )
        )