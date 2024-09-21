from constructs import Construct
from aws_cdk import (
    aws_ecr as ecr,
    RemovalPolicy, Stack
)

class EcrStack(Stack):
    
    # Setting for ECR
    
    def __init__(self, scope: Construct, construct_id: str, **kwards) -> None:
        super().__init__(scope, construct_id, **kwards)
        
        # Create ECR Repository
        self.ecr_repository = ecr.Repository(self, "EcrRepository",
                                             repository_name="keycloak-ecr-repository",
                                             removal_policy=RemovalPolicy.DESTROY,  # スタック削除時にECRも削除
                                             auto_delete_images=True  # ECRリポジトリにあるイメージも削除
                                             )