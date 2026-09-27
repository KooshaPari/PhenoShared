package lib

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"path/filepath"

	aws "nvms/lib/awspin"
	ec2 "nvms/lib/awspin/ec2"
	awsnet "nvms/lib/awspin/network"
	r53 "nvms/lib/awspin/network/route53"
	"nvms/lib/awspin/s3"
	"nvms/models"
	"strings"

	"github.com/google/uuid"
)

// getAWSRegion returns the AWS region from environment variable or defaults to us-east-1
func getAWSRegion() string {
	if region := os.Getenv("AWS_REGION"); region != "" {
		return region
	}
	return "us-east-1"
}

var AWSEndpointBase string = "https://%s." + getAWSRegion() + ".amazonaws.com" /* "http://localhost.localstack.cloud:4566"*/
func PushToS3(zipBall []byte, AccessKey string, SecretKey string, ProjectName string) (S3DeploymentInfo, error) {
	log.Println("Uploading to S3...")
	cfg := aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("s3"),
		Region:          getAWSRegion(),
		Service:         "s3",
	}
	ctx := context.Background()
	s3Client, err := s3.NewS3(cfg)
	if err != nil {
		log.Printf("S3 client creation failed: %v\n", err)
		return S3DeploymentInfo{}, err
	}
	log.Println("S3 client created")
	bucketName := strings.ToLower(ProjectName) + "-bytebucket-" + uuid.New().String()
	err = s3Client.CreateBucket(ctx, bucketName)
	if err != nil {
		log.Printf("Bucket creation failed: %v\n", err)
		return S3DeploymentInfo{}, err
	}

	log.Printf("Bucket created: %s\n", bucketName)
	err = s3Client.PutObject(ctx, bucketName, "src.zip", zipBall)
	if err != nil {
		log.Printf("PutObject failed: %v\n", err)
		return S3DeploymentInfo{}, err
	}
	log.Printf("Uploaded to S3: %s\n", bucketName)
	// return uri/bucket name for later use

	info := S3DeploymentInfo{
		BucketName: bucketName,
		ObjectKey:  "src.zip",
		Region:     getAWSRegion(),
		BucketARN:  fmt.Sprintf("arn:aws:s3:::%s", bucketName),
		//ObjectURL:   fmt.Sprintf("http://localhost:4566/%s/%s", bucketName, "src.zip"),
		ObjectURL:   fmt.Sprintf("https://%s.s3.amazonaws.com/%s", bucketName, "src.zip"),
		ContentHash: aws.GetPayloadHash(zipBall),
	}
	return info, nil

}

func DeployEC2(AccessKey string, SecretKey string, bucket S3DeploymentInfo, service models.Service, fileMap []string) ([]EC2InstanceInfo, error) {
	client, err := ec2.NewEC2(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("ec2"),
		Region:          getAWSRegion(),
		Service:         "ec2",
	})
	if err != nil {
		log.Printf("EC2 client creation failed: %v\n", err)
		return []EC2InstanceInfo{}, err
	}

	buildScript, err := generateBuildScript(bucket, service, AccessKey, SecretKey, fileMap)
	if err != nil {
		log.Printf("Error generating build script: %v\n", err)
		return []EC2InstanceInfo{}, err
	}
	log.Println("EC2 client created")
	params := map[string]string{
		"ImageId": "ami-01816d07b1128cd2d",
		//"ImageId": "ami-024f768332f0",
		"InstanceType": "t2.micro",
		"UserData":     buildScript,
		"MinCount":     "1",
		"MaxCount":     "1",
	}
	log.Println("Creating EC2 instance")
	resp, err := client.RunInstances(context.Background(), params)
	//fmt.Println(resp)
	var instances []EC2InstanceInfo
	for _, instance := range resp.Instances {
		newInstance := EC2InstanceInfo{
			InstanceID: instance.InstanceId,
			PrivateIP:  instance.PrivateIpAddress,
			State:      instance.State.Name,
			Region:     getAWSRegion(),
		}
		instances = append(instances, newInstance)
	}
	return instances, nil
}

func generateBuildScript(s3Info S3DeploymentInfo, service models.Service, accessKey, secretKey string, files []string) (string, error) {
	log.Println("Getting Buildpack")
	buildpack, err := DetectBuildPack(files, service)
	if err != nil {
		log.Printf("Error detecting buildpack: %v\n", err)
		log.Printf("Warning: No specific buildpack detected, using default behavior")
		buildpack = &models.BuildPack{
			Name:            "Generic",
			Packages:        []string{},
			PreBuild:        []string{},
			Build:           service.Build,
			EnvVars:         map[string]string{},
			Start:           strings.Join(service.Build, " && "),
			DetectFiles:     []string{},
			RuntimeVersions: map[string]string{},
		}
		return "", err
	}
	//fmt.Println("Got Buildpack: ", buildpack)
	heading := `#!/bin/bash
set -e

# Configure logging
exec 1> >(logger -s -t $(basename $0)) 2>&1
BUILD_LOG="/var/log/user-data-build.log"
touch $BUILD_LOG
chmod 644 $BUILD_LOG

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a $BUILD_LOG
}`
	script := `

log "Starting build process for %s application..."

# Update system
log "Updating system packages..."
dnf update -y

# Install AWS CLI and required tools
log "Installing required tools..."
dnf install -y unzip tar gzip

# Install AWS CLI v2
log "Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -f awscliv2.zip
rm -rf aws/

# Configure AWS credentials
log "Configuring AWS credentials..."
mkdir -p /root/.aws
cat > /root/.aws/credentials << EOF
[default]
aws_access_key_id = %s
aws_secret_access_key = %s
region = us-east-1
EOF

# Verify AWS configuration
aws configure list

# Create working directory
log "Creating working directory..."
mkdir -p /app
cd /app

# Download code from S3
log "Downloading code from S3..."
aws s3 cp s3://%s/%s src.zip

# Unzip the code
log "Extracting code..."
unzip src.zip
rm src.zip

# Find the actual directory
SERVICE_PATH=%s
EXTRACT_DIR=$(ls -d */ | head -n 1)
cd "$EXTRACT_DIR"

# Navigate to service directory
log "Navigating to service directory: %s"
cd %s
# Install detected runtime packages
log "Installing detected runtime packages..."
dnf install -y %s

# Set up environment variables
log "Configuring environment..."
%s

# Run pre-build commands
log "Running pre-build setup..."
%s

# Run build commands
log "Running build process..."
%s

# Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/%s.service << EOF
[Unit]
Description=%s Service (%s)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/app/$EXTRACT_DIR/%s
ExecStart=%s
Restart=always
Environment=PORT=%d
%s

[Install]
WantedBy=multi-user.target
EOF


# Start service
log "Starting service..."
systemctl daemon-reload
systemctl enable %s
systemctl start %s

log "Build and deployment complete!"
`
	log.Println("Building script...")
	envVarsList := make([]string, 0, len(buildpack.EnvVars))
	for k, v := range buildpack.EnvVars {
		envVarsList = append(envVarsList, fmt.Sprintf("export %s=%s", k, v))
	}
	environmentVars := strings.Join(envVarsList, "\n")
	// Format script with actual values
	formattedScript := heading + fmt.Sprintf(script,
		buildpack.Name,    // %s for application type
		accessKey,         // %s for AWS access key
		secretKey,         // %s for AWS secret key
		s3Info.BucketName, // %s for bucket name
		s3Info.ObjectKey,  // %s for object key
		filepath.Base(strings.Trim(service.Path, "/")),
		service.Path,                           // %s for service path (logging)
		service.Path,                           // %s for service path (cd)
		strings.Join(buildpack.Packages, " "),  // %s for packages
		environmentVars,                        // %s for env vars
		strings.Join(buildpack.PreBuild, "\n"), // %s for prebuild
		strings.Join(buildpack.Build, " && "),  // %s for build commands
		service.Name,                           // %s for service name
		service.Name,                           // %s for service name in Description
		buildpack.Name,                         // %s for buildpack name
		service.Path,                           // %s for WorkingDirectory
		buildpack.Start,                        // %s for ExecStart
		service.Port,                           // %d for PORT
		strings.Join(func() []string { // %s for systemd env vars
			var envs []string
			for k, v := range buildpack.EnvVars {
				envs = append(envs, fmt.Sprintf("Environment=%s=%s", k, v))
			}
			return envs
		}(), "\n"),
		service.Name, // %s for enable
		service.Name, // %s for start
	)
	// Debug: log service and buildpack info
	log.Printf("Service: %+v\n", service)
	log.Printf("Build Pack: %s\n", buildpack)
	return base64.StdEncoding.EncodeToString([]byte(formattedScript)), nil
}

func ProvisionNetwork(AccessKey string, SecretKey string, projectName string) (*awsnet.CreateLoadBalancerResponse, string, string, error) {
	albClient, err := awsnet.NewALB(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("elasticloadbalancing"),
		Region:          "us-east-1",
		Service:         "elasticloadbalancing",
	})
	if err != nil {
		log.Printf("ALB client creation failed: %v\n", err)
		return nil, "", "", err
	}
	ec2Client, err := ec2.NewEC2(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("ec2"),
		Region:          "us-east-1",
		Service:         "ec2"})
	if err != nil {
		log.Printf("EC2 client creation failed: %v\n", err)
		return nil, "", "", err
	}
	subnet1, subnet2, sgId, vpcId, err := ec2Client.GetAlbNetworkInfo(context.Background())
	if err != nil {
		log.Printf("GetAlbNetworkInfo failed: %v\n", err)
		return nil, "", "", err
	}
	/*targetArn, err := albClient.CreateTargetGroup(context.Background(), base+"-"+projectName+"-Byteport", vpcId)
	if err != nil {
		log.Printf("CreateTargetGroup failed: %v\n", err)
		return  "","",err
	}*/
	//fmt.Println("VPC: ", vpcId);
	albInstance, err := albClient.CreateInternetApplicationLoadbalancer(context.Background(), projectName, sgId, subnet1, subnet2)
	if err != nil {
		log.Printf("CreateInternetApplicationLoadbalancer failed: %v\n", err)
		return nil, "", "", err
	}
	//loadBalancerArn := albInstance.CreateLoadBalancerResult.LoadBalancers.Member.LoadBalancerArn
	publicDNS := albInstance.CreateLoadBalancerResult.LoadBalancers.Member.DNSName

	// for each service create targetgroup service-TG -> ALB Listener Rule Path /service/* -> service-TG

	log.Printf("ALB created with DNS: %s\n", publicDNS)

	return albInstance, vpcId, publicDNS, nil

}
func CreateALBListener(AccessKey string, SecretKey string, projectName string, loadBalancerArn string, vpcId string, instanceId string, port int) (string, string, error) {
	albClient, err := awsnet.NewALB(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("elasticloadbalancing"),
		Region:          "us-east-1",
		Service:         "elasticloadbalancing",
	})
	targetArn, err := RegisterService(AccessKey, SecretKey, loadBalancerArn, projectName, "main", vpcId, instanceId, port)
	listenerResponse, err := albClient.CreateListener(context.Background(), projectName, loadBalancerArn, targetArn)
	if err != nil {
		log.Printf("CreateListener failed: %v\n", err)
		return "", "", err
	}
	listenerArn := listenerResponse.CreateListenerResult.Listeners.Member.ListenerArn
	log.Printf("ALB Listener created: %s\n", listenerArn)
	return listenerArn, targetArn, nil

}
func SetListenerRules(AccessKey string, SecretKey string, ListenerArn string, TargetArn string, serviceName string, priority int) error {
	c, err := awsnet.NewALB(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("elasticloadbalancing"),
		Region:          "us-east-1",
		Service:         "elasticloadbalancing",
	})
	if err != nil {
		log.Printf("ALB client creation failed: %v\n", err)
		return err
	}
	err = c.CreateListenerRule(context.Background(), ListenerArn, TargetArn, serviceName, priority)
	if err != nil {
		log.Printf("CreateListenerRule failed: %v\n", err)
		return err
	}
	return nil
}
func RegisterService(AccessKey string, SecretKey string, loadBalancerArn string, projectName string, serviceName string, vpcId string, instanceId string, port int) (string, error) {
	albClient, err := awsnet.NewALB(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("elasticloadbalancing"),
		Region:          "us-east-1",
		Service:         "elasticloadbalancing",
	})
	if err != nil {
		log.Printf("ALB client creation failed: %v\n", err)
		return "", err
	}
	targetArn, err := albClient.CreateTargetGroup(context.Background(), serviceName+"-"+projectName+"-Byteport", vpcId)
	if err != nil {
		log.Printf("CreateTargetGroup failed: %v\n", err)
		return "", err
	}
	err = albClient.RegisterTarget(context.Background(), targetArn, instanceId, port)
	if err != nil {
		log.Printf("RegisterTarget failed: %v\n", err)
		return "", err
	}
	log.Printf("Service registered: %s\n", targetArn)
}
func AddNewRecord(AccessKey string, SecretKey string, domainName string, zoneID string, projectName string, value string) (string, error) {
	c, err := r53.NewRoute53(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("route53"),
		Region:          "us-east-1",
		Service:         "route53",
	})
	if err != nil {
		log.Printf("Route53 client creation failed: %v\n", err)
		return "", err
	}

	err = c.CreateRecordSet(context.Background(), zoneID, domainName, "A", value, 300, projectName)
	if err != nil {
		log.Printf("CreateRecordSet failed: %v\n", err)
		return "", err
	}
	log.Println("Record set created successfully")
	return "Success", nil

}
func AwaitInitialization(AccessKey string, SecretKey string, instanceIDs []string) error {
	log.Println("Waiting for instances to initialize...")
	c, err := ec2.NewEC2(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("ec2"),
		Region:          "us-east-1",
		Service:         "ec2",
	})
	if err != nil {
		log.Printf("EC2 client creation failed: %v\n", err)
		return err
	}
	log.Println("EC2 client created")
	err = c.WaitForEC2Running(instanceIDs, context.Background())
	if err != nil {
		log.Printf("WaitForEC2Running failed: %v\n", err)
		return err
	}
	log.Println("Instances initialized")
	return nil
}

func TerminateS3(resource models.AWSResource, AccessKey string, SecretKey string) error {
	c, err := s3.NewS3(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("s3"),
		Region:          "us-east-1",
		Service:         "s3",
	})
	if err != nil {
		fmt.Println(err)
		return err
	}

	err = c.DeleteBucket(context.Background(), resource.ID)
	if err != nil {
		err = c.DeleteObject(context.Background(), resource.ID, "src.zip")
		if err != nil {
			fmt.Println(err)
			return err
		}
		err = c.DeleteBucket(context.Background(), resource.ID)
		if err != nil {
			fmt.Println(err)
			return err
		}
		return err
	}
	fmt.Println("Record set created successfully.")
	return nil
}

func TerminateEC2(resource models.AWSResource, AccessKey string, SecretKey string) error {
	c, err := ec2.NewEC2(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		Endpoint:        getServiceEndpoint("ec2"),
		Region:          "us-east-1",
		Service:         "ec2",
	})
	if err != nil {
		fmt.Println(err)
		return err
	}

	err = c.TerminateInstances(context.Background(), []string{resource.ID})
	if err != nil {
		fmt.Println(err)
		return err
	}
	fmt.Println("Record set created successfully.")

	return nil
}

func TerminateALB(resource models.AWSResource, AccessKey string, SecretKey string) error {
	c, err := awsnet.NewALB(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("elasticloadbalancing"),
		Region:          "us-east-1",
		Service:         "elasticloadbalancing",
	})
	if err != nil {
		fmt.Println(err)
		return err
	}

	err = c.DeleteLoadbalancer(context.Background(), resource.ID)
	if err != nil {
		fmt.Println(err)
		return err
	}
	fmt.Println("Record set created successfully.")
	return nil
}

func TerminateTargetGroup(resource models.AWSResource, AccessKey string, SecretKey string) error {
	c, err := awsnet.NewALB(aws.Config{
		AccessKeyId:     AccessKey,
		SecretAccessKey: SecretKey,
		SessionToken:    "",
		Endpoint:        getServiceEndpoint("elasticloadbalancing"),
		Region:          "us-east-1",
		Service:         "elasticloadbalancing",
	})
	if err != nil {
		fmt.Println(err)
		return err
	}

	err = c.DeleteTargetGroup(context.Background(), resource.ID)
	if err != nil {
		fmt.Println(err)
		return err
	}

	fmt.Println("Record set created successfully.")
	return nil
}
