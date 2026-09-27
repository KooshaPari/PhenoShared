# Day 3 — AWS Lambda Webhook Fanout

Stand up `aws-lambda` as the receiver for GitHub webhooks, forwarding them to Forgejo's mirror-trigger API.

**Estimated wall-clock:** ~1 hour.

## Prerequisites

- AWS account with free-tier Lambda + API Gateway available.
- GitHub App created (private key = `GH-02` in Vaultwarden).
- Forgejo admin token (for mirror-trigger API calls) in Vaultwarden.

## Step 1 — Terraform apply

```
cd iac/terraform/aws
bw get notes aws/terraform-env | source /dev/stdin
terraform init
terraform plan -out=lambda.plan
terraform apply lambda.plan
```

Records:
- Lambda function ARN.
- API Gateway URL (public) — this becomes the webhook endpoint.

## Step 2 — Configure GitHub webhook

For each Phenotype repo:

1. Settings → Webhooks → Add webhook.
2. Payload URL: `<api-gw-url>/github-fanout`.
3. Content type: `application/json`.
4. Secret: use `GH-02`-derived HMAC key.
5. Events: Push, Pull Request, Release.

## Step 3 — Lambda logic (pseudocode)

The Lambda function (Rust, `aws-lambda-rust-runtime`):

1. Verify HMAC signature using `GH-02`.
2. Parse payload; extract repo + branch.
3. POST to Forgejo mirror-sync endpoint: `https://git.phenotype.io/api/v1/repos/<owner>/<repo>/mirror-sync` with Forgejo admin token.
4. Return 200.

## Step 4 — Smoke test

```
git commit --allow-empty -m "test: webhook fanout"
git push origin main
# Observe:
# 1. GitHub webhook delivery (green check in repo settings → Webhooks → Recent Deliveries)
# 2. Lambda CloudWatch log entry
# 3. Forgejo mirror updates within ~30s
```

## Rollback

- Disable webhooks in GitHub repo settings.
- `terraform destroy -target=module.aws_lambda` (Lambda + API GW + IAM role go away).
