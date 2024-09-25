#!/usr/bin/env python3
import os

import aws_cdk as cdk

# from keycloak_ecs_fargate.keycloak_ecs_fargate_stack import KeycloakEcsFargateStack
from keycloak_ecs_fargate.keycloak_infrastructure_stack import KeycloakInfrastructureStack
from keycloak_ecs_fargate.ecs_stack import EcsStack
from keycloak_ecs_fargate.test_keycloak_ecs import TestKeycloakEcsStack
# from keycloak_ecs_fargate.example_infra_stack import ExampleInfraStack
# from keycloak_ecs_fargate.example_ecs_stack import ExampleEcsStack, ECSStackProps


app = cdk.App()
# infrastructure_stack = KeycloakInfrastructureStack(app, "KeycloakInfrastructureStack")
# ecs_stack = EcsStack(app, "EcsStack",
#                      ecs_cluster=infrastructure_stack.ecs_cluster,
#                      listener=infrastructure_stack.listener,
#                     #  db_cluster=infrastructure_stack.db_cluster,
#                      db_instance=infrastructure_stack.db_instance,
#                      sg=infrastructure_stack.ecsSecurityGroup
# )

test = TestKeycloakEcsStack(app, "TestKeycloakEcsStack")

app.synth()





























# # Main ExampleInfraStack
# main_stack = ExampleInfraStack(app, 'ExampleInfraStack', env={
#     'region': 'us-east-1',
#     'account': '878518084785'
# })

# ecs_stack = ExampleEcsStack(app, 'ExampleEcsStack', 
#     props=ECSStackProps(
#         db_cluster=main_stack.aurora_cluster,
#         sg=main_stack.private_security_group,
#         listener=main_stack.listener,
#         ecs_cluster=main_stack.ecs_cluster
#     ),
#     env={
#         'region': 'us-east-1',
#         'account': '878518084785'
#     }
# )


