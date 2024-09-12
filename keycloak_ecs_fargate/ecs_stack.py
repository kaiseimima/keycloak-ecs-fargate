from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    Stack
)

CUSTOM_IMAGE = 'quay.io/3sky/keycloak-aurora:latest'

class EcsStack(Stack):

    # Setting for ECS/Fargate
    # Fargate Task Definition, Container, ECS Service, ALB TargetGroup

    def __init__(self, scope: Construct, construct_id: str, **kwards) -> None:
        super().__init__(scope, construct_id, **kwards)

        # Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(self, 'TaskDefinition',
                                                    runtime_platform=ecs.RuntimePlatform(
                                                        operating_system_family=ecs.OperatingSystemFamily.LINUX,
                                                        cpu_architecture=ecs.CpuArchitecture.X86_64
                                                    ),
                                                    cpu=256,
                                                    memory_limit_mib=512
        )

        # Container
        container = task_definition.add_container