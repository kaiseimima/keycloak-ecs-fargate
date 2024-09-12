import aws_cdk as core
import aws_cdk.assertions as assertions

from keycloak_ecs_fargate.keycloak_ecs_fargate_stack import KeycloakEcsFargateStack

# example tests. To run these tests, uncomment this file along with the example
# resource in keycloak_ecs_fargate/keycloak_ecs_fargate_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = KeycloakEcsFargateStack(app, "keycloak-ecs-fargate")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
