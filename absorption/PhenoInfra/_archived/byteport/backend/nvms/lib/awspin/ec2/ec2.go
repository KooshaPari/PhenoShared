package ec2

import (
	"bytes"
	"context"
	"encoding/xml"
	"fmt"
	"io"
	aws "nvms/lib/awspin"
	"time"
)

// RunInstances launches new EC2 instances
func (c *Client) RunInstances(ctx context.Context, params map[string]string) (*RunInstancesResponse, error) {
	params["Action"] = "RunInstances"
	//fmt.Println("Creating instance: ", params)

	req, err := c.newRequest(ctx, "POST", params, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return nil, err
	}

	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error creating instance: ", err)
		return nil, err
	}
	defer resp.Body.Close()

	var result RunInstancesResponse
	if err := xml.NewDecoder(resp.Body).Decode(&result); err != nil {
		fmt.Println("Error decoding response: ", err)
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	fmt.Println("Instance created")
	return &result, nil
}

// DescribeInstances gets information about EC2 instances
func (c *Client) DescribeInstances(ctx context.Context, instanceIds []string) (*DescribeInstancesResponse, error) {
	params := map[string]string{
		"Action": "DescribeInstances",
	}

	for i, id := range instanceIds {
		params[fmt.Sprintf("InstanceId.%d", i+1)] = id
	}

	req, err := c.newRequest(ctx, "GET", params, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result DescribeInstancesResponse
	if err := xml.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// TerminateInstances terminates EC2 instances
func (c *Client) TerminateInstances(ctx context.Context, instanceIds []string) error {
	params := map[string]string{
		"Action": "TerminateInstances",
	}

	for i, id := range instanceIds {
		params[fmt.Sprintf("InstanceId.%d", i+1)] = id
	}

	req, err := c.newRequest(ctx, "POST", params, nil)
	if err != nil {
		return err
	}

	resp, err := c.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}
func (c *Client) describeDefaultVPC(ctx context.Context) (string, error) {
	/*
		    curl "https://ec2.us-east-1.amazonaws.com/?Action=DescribeVpcs&Filter.1.Name=isDefault&Filter.1.Value.1=true&Version=2016-11-15" \
		-H "Content-Type: application/x-www-form-urlencoded" \
		--aws-sigv4 "aws:amz:us-east-1:ec2" \
		--user "YOUR_ACCESS_KEY:YOUR_SECRET_KEY"
	*/
	fmt.Println("getting vpc")
	params := map[string]string{
		"Action":           "DescribeVpcs",
		"Filter.1.Name":    "isDefault",
		"Filter.1.Value.1": "true",
		"Version":          "2016-11-15"}
	req, err := c.newRequest(ctx, "GET", params, nil)
	if err != nil {
		fmt.Println("Err Getting VPC Req: ", err)
		return "", err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error getting VPC: ", err)
		return "", err
	}

	defer resp.Body.Close()
	var defaultVPC DescribeVpcsResponse
	//fmt.Println("Resp: ", resp)
	if err := xml.NewDecoder(resp.Body).Decode(&defaultVPC); err != nil {
		fmt.Println("Error decoding response: ", err)
		return "", fmt.Errorf("failed to decode response: %w", err)
	}
	return defaultVPC.Vpcs[0].VpcId, nil

}
func (c *Client) DescribeSubnets(ctx context.Context, vpcId string) (*DescribeSubnetsResponse, error) {

	params := map[string]string{
		"Action":           "DescribeSubnets",
		"Filter.1.Name":    "vpc-id",
		"Filter.1.Value.1": vpcId,

		"Version": "2016-11-15",
	}
	req, err := c.newRequest(ctx, "GET", params, nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error getting Subnet: ", err)
		return nil, err
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}
	//fmt.Println("Response Body:", string(bodyBytes))

	// Reset the response body for decoding
	resp.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	var subnets DescribeSubnetsResponse
	if err := xml.NewDecoder(resp.Body).Decode(&subnets); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	return &subnets, nil
}
func (c *Client) DescribeSecurityGroups(ctx context.Context, vpcId string) (*DescribeSecurityGroupsResponse, error) {
	/*
		    curl "https://ec2.us-east-1.amazonaws.com/?Action=DescribeSecurityGroups&Filter.1.Name=vpc-id&Filter.1.Value.1=vpc-xxxxx&Version=2016-11-15" \
		-H "Content-Type: application/x-www-form-urlencoded" \
		--aws-sigv4 "aws:amz:us-east-1:ec2" \
		--user "YOUR_ACCESS_KEY:YOUR_SECRET_KEY"*/
	params := map[string]string{
		"Action":           "DescribeSecurityGroups",
		"Filter.1.Name":    "vpc-id",
		"Filter.1.Value.1": vpcId,
		// filter by azn e.g. us-east 1

		"Version": "2016-11-15"}
	req, err := c.newRequest(ctx, "GET", params, nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error getting VPC: ", err)
		return nil, err
	}
	defer resp.Body.Close()

	var securityGroups DescribeSecurityGroupsResponse
	if err := xml.NewDecoder(resp.Body).Decode(&securityGroups); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	return &securityGroups, nil
}
func (c *Client) GetAlbNetworkInfo(ctx context.Context) (string, string, string, string, error) {
	fmt.Println("Getting VPC")
	vpcId, err := c.describeDefaultVPC(ctx)
	if err != nil {
		return "", "", "", "", err
	}
	fmt.Println("Getting Subnets")
	subnets, err := c.DescribeSubnets(ctx, vpcId)
	if err != nil {
		return "", "", "", "", err
	}
	fmt.Println("Getting Security Groups")
	securityGroups, err := c.DescribeSecurityGroups(ctx, vpcId)
	if err != nil {
		return "", "", "", "", err
	}
	fmt.Println("Got ALB NetInfo")
	//fmt.Println("Subnets: ", subnets)
	//fmt.Println("Security Groups: ", securityGroups)
	//fmt.Println("VPC: ", vpcId)
	subnet1, subnet2 := subnets.SubnetSet[0].SubnetId, subnets.SubnetSet[1].SubnetId
	return subnet1, subnet2, securityGroups.SecurityGroupInfo.Item.GroupId, vpcId, nil
}
func (c *Client) WaitForEC2Running(instanceIDs []string, ctx context.Context) error {
	maxAttempts := 60 // Adjust as needed
	fmt.Println("Waiting for EC2 to initialize: ", instanceIDs)

	for attempt := 0; attempt < maxAttempts; attempt++ {
		fmt.Printf("Attempt %d: Checking EC2 instance statuses\n", attempt+1)
		resp, err := c.DescribeInstances(ctx, instanceIDs)
		if err != nil {
			// Check if error is InvalidInstanceID.NotFound and retry
			if awsErr, ok := err.(*aws.ErrorResponse); ok && awsErr.Code == "InvalidInstanceID.NotFound" {
				fmt.Println("Instance not yet available, retrying...")
			} else {
				fmt.Println("Instance not yet available, retrying...")
				//return fmt.Errorf("error checking instance status: %v", err)
			}
		} else {
			allRunning := true
			for _, reservation := range resp.Reservations {
				for _, instance := range reservation.Instances {
					if instance.State.Name != "running" {
						allRunning = false
						break
					}
				}
				if !allRunning {
					break
				}
			}

			if allRunning {
				fmt.Println("EC2 instances initialized: ", instanceIDs)
				return nil
			}
		}

		// Implement a non-blocking wait without using time.Sleep
		start := time.Now()
		waitDuration := 5 * time.Second
		for {
			elapsed := time.Since(start)
			if elapsed >= waitDuration {
				break
			}
		}
	}
	fmt.Println("Timeout waiting for running instances")

	return fmt.Errorf("timeout waiting for instances to reach running state")
}
