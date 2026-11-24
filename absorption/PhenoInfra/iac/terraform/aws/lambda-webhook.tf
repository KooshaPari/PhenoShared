# lambda-webhook.tf — aws-lambda webhook fanout: GitHub → Forgejo mirror-sync.

variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "aws_account_id" { type = string /* <AWS_ACCOUNT_ID> */ }

provider "aws" {
  region = var.aws_region
}

# resource "aws_lambda_function" "github_fanout" {
#   function_name = "github-fanout"
#   role          = aws_iam_role.lambda_exec.arn
#   handler       = "bootstrap"
#   runtime       = "provided.al2"
#   architectures = ["arm64"]    # Graviton; free tier
#   filename      = "${path.module}/artifacts/github-fanout.zip"
#   timeout       = 10
#
#   environment {
#     variables = {
#       FORGEJO_API_URL = "https://git.phenotype.io/api/v1"
#       FORGEJO_TOKEN_PARAM = "/phenotype/forgejo/mirror-sync-token"   # from SSM
#       GITHUB_WEBHOOK_SECRET_PARAM = "/phenotype/github/webhook-secret"
#     }
#   }
# }
#
# resource "aws_apigatewayv2_api" "github_fanout" {
#   name          = "github-fanout"
#   protocol_type = "HTTP"
# }
#
# (integration, route, stage, IAM role omitted — stub only)
