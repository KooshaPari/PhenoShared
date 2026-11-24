package projectManager

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"nvms/lib"
	"nvms/models"
	"strings"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
	"github.com/google/uuid"
)

func DeployProject(w http.ResponseWriter, r *http.Request) {
	/*  Deploying a Project is the Most Complex Operation in the System
	*   General High Level Process
	*   Receive a Project(user, repo, header) ->
		locate nvms/readme and codebase (Send to Provisioner Route)
	*   Unmarshal the NVMS(yaml) as an Object and Validate/Process it
	*   Begin Generating a Resource Plan -> Send to Builder Route
	*   Build VPC/Network, Configure Security Groups, Setup Load  *  *   Balancers, Go down the line of the Resource Plan/NVMS Object
	*   Validate Resources and Send Status -> Deployment Module
	*   Config/Deploy MicroVM(FireCracker), Config Services, Setup
	*   Monitoring call portfolio route (Repository, Readme, NVMS)
	*   Analyze Project (Get Details for Prompting, Read Playground Type from NVMS), Pull Templates from Portfolio, Pick appropriate template given args and build and send back.
	*   Open appropriate connections for playground and rpovide to route, deployed.
	*/

	// sec 1
	project, user, err := readBody(w, r)
	if err != nil {
		http.Error(w, "Error parsing request", http.StatusBadRequest)
		return
	}
	nvmsString, readMeString, codebase, files, err := ProvisionFiles(w, r, project)
	if err != nil {
		http.Error(w, "Error provisioning files", http.StatusInternalServerError)
	}
	fmt.Println("Got files")
	//ln(response)

	// add new deployment to project

	// NVMS manifest is parsed and validated below (parseNVMSConfig at line 67)

	//fmt.Println("Project: ", project)

	fmt.Println("ReadMe: ", readMeString)
	if project.GetDeploys() == nil {
		project.CreateDeploys()
	}

	deployID := uuid.New().String()
	project.AppendDeploy(deployID, models.Instance{
		UUID:   deployID,
		Name:   "main",
		Status: "initializing",
		Owner:  user.UUID,

		Resources: make([]models.AWSResource, 0), // Initialize slice
	})
	//fmt.Println("Files: ", files)
	//fmt.Println("Codebase: ", codebase)

	nvmsConfig, err := parseNVMSConfig(nvmsString)
	if err != nil {
		fmt.Println("Error parsing NVMS: ", err)
		http.Error(w, "Error parsing NVMS: "+err.Error(), http.StatusBadRequest)
	}
	project.NvmsConfig = *nvmsConfig
	project.Readme = readMeString
	// sec 3
	accesskey, secretkey, err := lib.GetAWSCredentials(user)
	if err != nil {
		http.Error(w, "Error getting AWS credentials", http.StatusInternalServerError)
		return
	}

	bucket, err := lib.PushToS3(codebase, accesskey, secretkey, project.Name)

	if err != nil {
		fmt.Println("Error pushing to S3: ", err)
		http.Error(w, "Error pushing to S3: "+err.Error(), http.StatusInternalServerError)
		return
	}
	instance := project.GetDeploy(deployID)
	instance.Resources = append(instance.Resources, models.AWSResource{
		Name:    "S3-CodeBase Store",
		ARN:     bucket.BucketARN,
		Status:  "deployed",
		Region:  bucket.Region,
		ID:      bucket.BucketName,
		Type:    "S3",
		Service: "general",
	})
	project.AppendDeploy(deployID, instance)

	ServiceInstances := make(map[string][]lib.EC2InstanceInfo)
	serviceMap := make(map[string]models.Service)
	for _, service := range nvmsConfig.Services {
		/* So here we need to deploy 2x services into a vm, for now just a basic ec2, that will then be run with X command and have the following ports opened publicly for it. */
		fmt.Println("Serve")
		instances, err := DeployNVMSService(accesskey, secretkey, bucket, service, files)
		if err != nil {
			fmt.Println("Error deploying service: ", err)
			http.Error(w, "Error deploying service: "+err.Error(), http.StatusInternalServerError)
			return
		}
		res := project.GetDeploy(deployID)
		var instanceIDs []string
		for _, inst := range instances {
			instanceIDs = append(instanceIDs, inst.InstanceID)
		}
		res.Resources = append(project.GetDeploy(deployID).Resources, models.AWSResource{
			Name:    service.Name + "-Deployment",
			ARN:     instances[0].InstanceID,
			Status:  "deployed",
			Region:  instances[0].Region,
			ID:      strings.Join(instanceIDs, ","),
			Type:    "EC2",
			Service: service.Name,
		})
		project.AppendDeploy(deployID, res)
		serviceMap[service.Name] = service
		ServiceInstances[service.Name] = instances
	}
	fmt.Println("Handling Net...")

	fmt.Println("Service Instances: ", ServiceInstances)
	// wind down services since this is for debug.
	// await deployment then setup network
	// write service Instances to bodyservBody, err = json.Marshal(ServiceInstances)
	// run a for loop on service instances, for each await deploy then register services, prov network and finally listener rules.
	var instIDs []string
	fmt.Println("Waiting for Initialization")
	// add short wait
	fmt.Println("Initializing")
	for name, instances := range ServiceInstances {
		fmt.Println("Initializing ids: ", name)
		instIDs = []string{}
		for _, instance := range instances {
			instIDs = append(instIDs, instance.InstanceID)
		}
		fmt.Println("Initializing: ", name)
		err := lib.AwaitInitialization(accesskey, secretkey, instIDs)

		if err != nil {
			http.Error(w, "Error Checking init", http.StatusBadRequest)
			return
		}

		fmt.Println("Intialized: ", name)
	}

	alb, vpcId, accessURL, err := lib.ProvisionNetwork(accesskey, secretkey, project.Name)
	lbArn := alb.CreateLoadBalancerResult.LoadBalancers.Member.LoadBalancerArn
	res := project.GetDeploy(deployID)
	res.Resources = append(project.GetDeploy(deployID).Resources, models.AWSResource{
		Name:    "ALB",
		ARN:     lbArn,
		Status:  "deployed",
		Region:  "us-east-1",
		ID:      lbArn,
		Type:    "ALB",
		Service: "general",
	})
	project.AppendDeploy(deployID, res)

	project.AccessURL = accessURL
	if err != nil {
		fmt.Println("Error provisioning network", err)
		http.Error(w, "Error provisioning network: "+err.Error(), http.StatusInternalServerError)
	}
	var listenArn, targetGArn string
	// Create listener only for the first main instance
	if len(ServiceInstances["main"]) > 0 {
		instance := ServiceInstances["main"][0]
		fmt.Println("building main listener(s)")
		listenArn, targetGArn, err = lib.CreateALBListener(accesskey, secretkey, project.Name, lbArn, vpcId, instance.InstanceID, serviceMap["main"].Port)

		if err != nil {
			fmt.Println("Error Creating Listener  ", err)
			http.Error(w, "Error Creating Listener  : "+err.Error(), http.StatusInternalServerError)
		}
		fmt.Println("SSSListener ARN: ", listenArn)

		res := project.GetDeploy(deployID)
		res.Resources = append(project.GetDeploy(deployID).Resources, models.AWSResource{
			Name:    "ALBListener",
			ARN:     listenArn,
			Status:  "deployed",
			Region:  "us-east-1",
			ID:      listenArn,
			Type:    "Listener",
			Service: "general",
		})
		fmt.Println("POST APPEND LISTENER", listenArn)
		res.Resources = append(project.GetDeploy(deployID).Resources, models.AWSResource{
			Name:    "TargetGroup",
			ARN:     targetGArn,
			Status:  "deployed",
			Region:  "us-east-1",
			ID:      targetGArn,
			Type:    "TargetGroup",
			Service: "main",
		})
		project.AppendDeploy(deployID, res)
		fmt.Println("Built main listener(s) for instance: ", instance.InstanceID)
	}

	priority := 1
	for name, instances := range ServiceInstances {
		service := serviceMap[name]
		if name != "main" {
			for _, instance := range instances {

				tgArn, err := lib.RegisterService(accesskey, secretkey, lbArn, project.Name, name, vpcId, instance.InstanceID, service.Port)
				if err != nil {
					fmt.Println("Error registering service: ", err)
					http.Error(w, "Error registering service: "+err.Error(), http.StatusInternalServerError)
					return
				}
				res := project.GetDeploy(deployID)
				res.Resources = append(project.GetDeploy(deployID).Resources, models.AWSResource{
					Name:    service.Name + "-TargetGroup",
					ARN:     tgArn,
					Status:  "deployed",
					Region:  "us-east-1",
					Type:    "TargetGroup",
					ID:      tgArn,
					Service: name,
				})
				project.AppendDeploy(deployID, res)
				fmt.Println("registered service")
				fmt.Println("Listener ARN: ", listenArn)
				err = lib.SetListenerRules(accesskey, secretkey, listenArn, tgArn, name, priority)
				if err != nil {
					fmt.Println("Error creating listener rule: ", err)
					http.Error(w, "Error creating listener rule: "+err.Error(), http.StatusInternalServerError)
					return
				}
				priority++
				fmt.Println("Created Listener Rule")
			}
		}

	}

	if !strings.HasPrefix(project.AccessURL, "http") {
		project.AccessURL = "http://" + project.AccessURL
	}
	fmt.Println("Completed EC2-Deploy.")
	fmt.Println("Project: ", project)
	if err := project.BeforeSave(); err != nil {
		http.Error(w, "Error saving project", http.StatusInternalServerError)
	}
	err = addToDemo(project)
	if err != nil {
		fmt.Println("error generating demo: ", err)
		http.Error(w, "error generating demo"+err.Error(), http.StatusInternalServerError)
	}
	projectJSON, err := json.Marshal(project)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Write(projectJSON)
}
func addToDemo(project models.Project) error {
	reqBody, err := json.Marshal(project)
	if err != nil {
		return fmt.Errorf("error marshaling project: %w", err)
	}
	req, err := http.NewRequest("GET", "/generate", bytes.NewReader(reqBody))
	if err != nil {
		return fmt.Errorf("error creating request: %w", err)
	}
	_, err = spinhttp.Send(req)
	if err != nil {
		return fmt.Errorf("error sending request: %w", err)
	}
	return nil
}
func DeployNVMSService(AccessKey string, SecretKey string, Bucket lib.S3DeploymentInfo, service models.Service, fileMap []string) ([]lib.EC2InstanceInfo, error) {
	instances, err := lib.DeployEC2(AccessKey, SecretKey, Bucket, service, fileMap)
	if err != nil {
		fmt.Println("Error deploying EC2: ", err)
		return nil, err
	}
	//fmt.Println("Deployed EC2 Instances: ", instances)
	fmt.Println("Building Services: ", service)

	return instances, nil
}
