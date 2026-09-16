// Package lib provides core functionality for NVMS (NVM Service) including
// AWS infrastructure management, authentication, and LLM provider integration.
//
// # Exports
//
// This package exports the following public functions:
//
// AWS Infrastructure Management:
//
//	PushToS3(zipBall []byte, AccessKey, SecretKey, ProjectName string) (S3DeploymentInfo, error)
//	DeployEC2(AccessKey, SecretKey string, bucket S3DeploymentInfo, service models.Service, fileMap []string) ([]EC2InstanceInfo, error)
//	ProvisionNetwork(AccessKey, SecretKey, projectName string) (*awsnet.CreateLoadBalancerResponse, string, string, error)
//	CreateALBListener(AccessKey, SecretKey, projectName, loadBalancerArn, vpcId, instanceId string, port int) (string, string, error)
//	SetListenerRules(AccessKey, SecretKey, ListenerArn, TargetArn, serviceName string, priority int) error
//	RegisterService(AccessKey, SecretKey, loadBalancerArn, projectName, serviceName, vpcId, instanceId string, port int) (string, error)
//	AddNewRecord(AccessKey, SecretKey, domainName, zoneID, projectName, value string) (string, error)
//	AwaitInitialization(AccessKey, SecretKey string, instanceIDs []string) error
//	TerminateS3(resource models.AWSResource, AccessKey, SecretKey string) error
//	TerminateEC2(resource models.AWSResource, AccessKey, SecretKey string) error
//	TerminateALB(resource models.AWSResource, AccessKey, SecretKey string) error
//	TerminateTargetGroup(resource models.AWSResource, AccessKey, SecretKey string) error
//
// Build Pack Detection:
//
//	DetectBuildPack(files []string, service models.Service) (*models.BuildPack, error)
//
// Credential Management:
//
//	GetAWSCredentials(user models.User) (string, string, error)
//
// Authentication:
//
//	InitAuthSystem() error
//	GenerateSymmetricKey() string
//	GenerateNVMSToken(project models.Project) (string, error)
//	ValidateServiceToken(encryptedToken string) (bool, *paseto.Token, error)
//	AuthMiddleware(w http.ResponseWriter, r *http.Request) error
//	EncryptSecret(secret string) (string, error)
//	DecryptSecret(cipherText string) (string, error)
//	GetDecodedEncryptionKey() ([]byte, error)
//
// LLM Provider Integration:
//
//	RequestCompletion(prompt, strStruct string, config models.LLM) (string, error)
//
// Types:
//
//	S3DeploymentInfo - Information about deployed S3 resources
//	EC2InstanceInfo - Information about deployed EC2 instances
//	BuilderReq - Request structure for building resources
//
// Subpackages:
//
//	awspin - AWS service abstractions (S3, EC2, Network)
//	providers - LLM provider implementations (OpenAI, Anthropic, Gemini, Local)
package lib
