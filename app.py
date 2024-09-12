#!/usr/bin/env python3
import os

import aws_cdk as cdk

# from keycloak_ecs_fargate.keycloak_ecs_fargate_stack import KeycloakEcsFargateStack
from keycloak_ecs_fargate.keycloak_infrastructure_stack import KeycloakInfrastructureStack


app = cdk.App()
KeycloakInfrastructureStack(app, "KeycloakInfrastructureStack")

app.synth()
