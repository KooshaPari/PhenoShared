# NVMS Library

Core functionality for NVM Service (NVMS) including AWS infrastructure management, authentication, and LLM provider integration.

## Features

### AWS Infrastructure Management

- **S3 Operations**: Upload deployment packages to S3 buckets
- **EC2 Deployment**: Launch and manage EC2 instances with automatic build scripts
- **Load Balancing**: Create ALBs with target groups and listener rules
- **DNS Management**: Configure Route53 record sets
- **Build Pack Detection**: Automatic detection of runtime (Go, Node.js, Python, etc.)

### Authentication

- **Service Tokens**: PASETO v4-based service authentication
- **Secret Encryption**: AES-CFB encryption for sensitive credentials
- **Key Management**: Environment variable and keyring integration

### LLM Provider Integration

- **Multi-Provider Support**: OpenAI, Anthropic, Gemini, DeepSeek, and local models
- **Unified Interface**: Single `RequestCompletion` function for all providers

## Usage

```go
import "nvms/lib"

// Deploy to AWS
s3Info, err := lib.PushToS3(zipBall, accessKey, secretKey, projectName)
instances, err := lib.DeployEC2(accessKey, secretKey, s3Info, service, files)

// Initialize authentication
if err := lib.InitAuthSystem(); err != nil {
    log.Fatal(err)
}

// Generate service token
token, err := lib.GenerateNVMSToken(project)

// Request LLM completion
response, err := lib.RequestCompletion(prompt, structStr, config)
```

## Subpackages

| Package | Description |
|---------|-------------|
| `awspin` | AWS service abstractions |
| `awspin/ec2` | EC2 instance management |
| `awspin/network` | VPC, ALB, Route53 management |
| `awspin/s3` | S3 bucket operations |
| `providers` | LLM provider implementations |
| `providers/openai` | OpenAI API integration |
| `providers/anthropic` | Anthropic Claude API |
| `providers/gemini` | Google Gemini API |
| `providers/local` | Local LLM support |
| `providers/deepseek` | DeepSeek API |

## Exports

| Category | Functions |
|----------|----------|
| AWS | `PushToS3`, `DeployEC2`, `ProvisionNetwork`, `CreateALBListener`, `SetListenerRules`, `RegisterService`, `AddNewRecord`, `AwaitInitialization`, `TerminateS3`, `TerminateEC2`, `TerminateALB`, `TerminateTargetGroup` |
| Build | `DetectBuildPack`, `GetAWSCredentials` |
| Auth | `InitAuthSystem`, `GenerateSymmetricKey`, `GenerateNVMSToken`, `ValidateServiceToken`, `AuthMiddleware`, `EncryptSecret`, `DecryptSecret`, `GetDecodedEncryptionKey` |
| LLM | `RequestCompletion` |

## Dependencies

- `github.com/google/uuid` - UUID generation
- `aidanwoods.dev/go-paseto` - PASETO token generation/validation
- `github.com/zalando/go-keyring` - Secure key storage
