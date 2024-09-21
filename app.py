#!/usr/bin/env python3
import os

import aws_cdk as cdk

# from keycloak_ecs_fargate.keycloak_ecs_fargate_stack import KeycloakEcsFargateStack
from keycloak_ecs_fargate.keycloak_infrastructure_stack import KeycloakInfrastructureStack
from keycloak_ecs_fargate.ecs_stack import EcsStack


app = cdk.App()
infrastructure_stack = KeycloakInfrastructureStack(app, "KeycloakInfrastructureStack")
# ecs_stack = EcsStack(app, "EcsStack",
#                      ecs_cluster=infrastructure_stack.ecs_cluster,
#                      listener=infrastructure_stack.listener,
#                     #  db_cluster=infrastructure_stack.db_cluster,
#                      db_instance=infrastructure_stack.db_instance,
#                      sg=infrastructure_stack.ecsSecurityGroup
# )

app.synth()
