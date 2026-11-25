package network

import (
	"bytes"
	"context"
	"encoding/hex"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"net/url"
	aws "nvms/lib/awspin"
	"sort"
	"strconv"
	"strings"
	"time"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
)

func NewALB(config aws.Config) (*Client, error) {
	u, err := url.Parse(config.Endpoint)
	if err != nil {
		return nil, fmt.Errorf("failed to parse endpoint: %w", err)
	}
	usePathStyle := strings.Contains(u.Host, "localhost") || strings.Contains(u.Host, "127.0.0.1")

	client := &Client{
		config:       config,
		endpointURL:  u.String(),
		usePathStyle: usePathStyle,
	}

	return client, nil
}

func (c *Client) newRequest(ctx context.Context, method string, params map[string]string, body []byte) (*http.Request, error) {
	furl, err := c.buildEndpoint(params["Action"])
	if err != nil {
		return nil, err
	}
	u, err := url.Parse(furl)
	if err != nil {
		return nil, err
	}

	var awsDate aws.AwsDate
	awsDate.Time = time.Now()

	params["Version"] = "2015-12-01"
	params["X-Amz-Algorithm"] = "AWS4-HMAC-SHA256"
	params["X-Amz-Date"] = awsDate.GetTime()

	// Build credential scope
	credentialScope := fmt.Sprintf("%s/%s/%s/aws4_request",
		awsDate.GetDate(),
		c.config.Region,
		c.config.Service)

	params["X-Amz-Credential"] = fmt.Sprintf("%s/%s",
		c.config.AccessKeyId,
		credentialScope)

	// Set signed headers
	params["X-Amz-SignedHeaders"] = "host"

	// Add security token if present
	if c.config.SessionToken != "" {
		params["X-Amz-Security-Token"] = c.config.SessionToken
	}

	// Build canonical query string for signing
	canonicalQueryString := GetCanonicalQueryString(params)

	// Create string to sign
	canonicalRequest := strings.Join([]string{
		method,
		"/",
		canonicalQueryString,
		fmt.Sprintf("host:%s\n", u.Host), // Canonical headers
		"host",                           // Signed headers
		"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // Empty payload hash
	}, "\n")

	stringToSign := strings.Join([]string{
		"AWS4-HMAC-SHA256",
		awsDate.GetTime(),
		credentialScope,
		aws.GetSHA256Hash([]byte(canonicalRequest)),
	}, "\n")

	// Calculate signature
	dateKey := aws.HmacSHA256([]byte("AWS4"+c.config.SecretAccessKey), []byte(awsDate.GetDate()))
	regionKey := aws.HmacSHA256(dateKey, []byte(c.config.Region))
	serviceKey := aws.HmacSHA256(regionKey, []byte(c.config.Service))
	signingKey := aws.HmacSHA256(serviceKey, []byte("aws4_request"))
	signature := hex.EncodeToString(aws.HmacSHA256(signingKey, []byte(stringToSign)))

	// Add signature to parameters
	params["X-Amz-Signature"] = signature

	// Build final URL with all parameters
	query := u.Query()
	for k, v := range params {
		query.Set(k, v)
	}
	u.RawQuery = query.Encode()

	// Create request with minimal headers
	req, err := http.NewRequestWithContext(ctx, method, u.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("host", u.Host)
	req.Header.Set("user-agent", "byteport")

	fmt.Printf("ALB request prepared: method=%s host=%s action=%s\n", method, u.Host, params["Action"])

	return req, nil
}
func (c *Client) buildEndpoint(action string) (string, error) {
	u, err := url.Parse(c.endpointURL)
	if err != nil {
		return "", fmt.Errorf("failed to parse endpoint: %w", err)
	}

	if c.usePathStyle {
		// LocalStack: http://localhost:4566/elasticloadbalancing/
		u = u.JoinPath("elasticloadbalancing")
	}

	// Both AWS and LocalStack use query parameters for ELB API
	q := u.Query()
	q.Set("Action", action)
	q.Set("Version", "2015-12-01") // ELB API version
	u.RawQuery = q.Encode()

	return u.String(), nil
}

// Helper function to create canonical query string
func GetCanonicalQueryString(params map[string]string) string {
	// Get sorted list of parameter names
	paramNames := make([]string, 0, len(params))
	for name := range params {
		paramNames = append(paramNames, name)
	}
	sort.Strings(paramNames)

	// Build canonical query string
	pairs := make([]string, 0, len(params))
	for _, name := range paramNames {
		pairs = append(pairs, fmt.Sprintf("%s=%s",
			url.QueryEscape(name),
			url.QueryEscape(params[name]),
		))
	}

	return strings.Join(pairs, "&")
}

func (c *Client) do(req *http.Request) (*http.Response, error) {

	resp, err := spinhttp.Send(req)
	if err != nil {
		fmt.Println("Error sending request: ", err)
		return nil, fmt.Errorf("failed to send request: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		fmt.Println("Code: ", resp.StatusCode)
		fmt.Println("Response: ", resp)
		var errorResponse aws.ErrorResponse
		if err := xml.NewDecoder(resp.Body).Decode(&errorResponse); err != nil {
			fmt.Println("Error parsing response: ", err)
			return nil, fmt.Errorf("failed to parse error response: %w", err)
		}
		fmt.Println("Error response: ", errorResponse)
		return nil, errorResponse
	}
	fmt.Println("Request sent successfully")
	return resp, nil
}
func (c *Client) CreateListener(ctx context.Context, name string, loadBalancerArn string, targetGroupArn string) (*CreateListenerResponse, error) {
	fmt.Println("Creating listener: ", name)
	fmt.Println("LoadBalancerArn: ", loadBalancerArn)
	fmt.Println("TargetGroupArn: ", targetGroupArn)
	params := map[string]string{
		"Action":                                 "CreateListener",
		"LoadBalancerArn":                        loadBalancerArn,
		"Protocol":                               "HTTP",
		"Port":                                   "80",
		"DefaultActions.member.1.Type":           "forward",
		"DefaultActions.member.1.TargetGroupArn": targetGroupArn,
		"Version":                                "2015-12-01",
	}
	req, err := c.newRequest(ctx, http.MethodGet, params, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return nil, err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error creating listener: ", err)
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
	var listenerResponse CreateListenerResponse
	if err := xml.NewDecoder(resp.Body).Decode(&listenerResponse); err != nil {
		fmt.Println("Error creating request: ", err)
		return nil, err
	}
	fmt.Println("Built Listener: ", listenerResponse.CreateListenerResult.Listeners.Member.ListenerArn)
	return &listenerResponse, nil

}
func (c *Client) CreateTargetGroup(ctx context.Context, name string, vpcId string) (string, error) {
	fmt.Println("Creating target group: ", name)
	serviceName := name
	params := map[string]string{
		"Action":     "CreateTargetGroup",
		"Name":       serviceName,
		"Protocol":   "HTTP",
		"Port":       "80",
		"VpcId":      vpcId,
		"TargetType": "instance",
		"Version":    "2015-12-01",
	}
	req, err := c.newRequest(ctx, http.MethodGet, params, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return " ", err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error creating target group: ", err)
		return " ", err
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response body: %w", err)
	}
	//fmt.Println("Response Body:", string(bodyBytes))

	// Reset the response body for decoding
	resp.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	var targetGroupResponse CreateTargetGroupResponse
	if err := xml.NewDecoder(resp.Body).Decode(&targetGroupResponse); err != nil {
		fmt.Println("Error parsing response: ", err)
		return " ", fmt.Errorf("failed to parse response: %w", err)
	}
	fmt.Println("Created target group: ", targetGroupResponse.CreateTargetGroupResult.TargetGroups.Member.TargetGroupArn)
	return targetGroupResponse.CreateTargetGroupResult.TargetGroups.Member.TargetGroupArn, nil

}
func (c *Client) RegisterTarget(ctx context.Context, targetGroupArn string, instanceId string, port int) error {
	fmt.Println("Registering target: ", instanceId)
	//fmt.Println("Port: ", port)
	params := map[string]string{
		"Action":                "RegisterTargets",
		"TargetGroupArn":        targetGroupArn,
		"Targets.member.1.Id":   instanceId,
		"Targets.member.1.Port": strconv.Itoa(port),
		"Version":               "2015-12-01",
	}
	//fmt.Println("Port: ", port)
	//fmt.Println("Str: ", string(port))
	req, err := c.newRequest(ctx, http.MethodGet, params, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error registering target: ", err)
		return err
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}
	//fmt.Println("Response Body:", string(bodyBytes))

	// Reset the response body for decoding
	resp.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	fmt.Println("Target registered")
	return nil

}

func (c *Client) CreateListenerRule(ctx context.Context, ListenerArn string, targetGroupArn string, serviceName string, priority int) error {
	fmt.Println("Creating listener rule: ", serviceName)
	params := map[string]string{
		"Action":                              "CreateRule",
		"ListenerArn":                         ListenerArn,
		"Priority":                            strconv.Itoa(priority),
		"Conditions.member.1.Field":           "path-pattern",
		"Conditions.member.1.Values.member.1": "/" + serviceName + "/*",
		"Actions.member.1.Type":               "forward",
		"Actions.member.1.TargetGroupArn":     targetGroupArn,
		"Version":                             "2015-12-01",
	}
	req, err := c.newRequest(ctx, http.MethodGet, params, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error creating listener rule: ", err)
		return err
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}
	//fmt.Println("Response Body:", string(bodyBytes))

	// Reset the response body for decoding
	resp.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	fmt.Println("Rule Built")
	return nil

}
func (c *Client) CreateInternetApplicationLoadbalancer(ctx context.Context, name string, vpcsgId string, subnet1 string, subnet2 string) (*CreateLoadBalancerResponse, error) {
	fmt.Println("Creating internet application load balancer: ", name)
	req, err := c.newRequest(ctx, http.MethodPut, map[string]string{
		"Action":                  "CreateLoadBalancer",
		"Name":                    name + "-byteport",
		"Scheme":                  "internet-facing",
		"Type":                    "application",
		"Subnets.member.1":        subnet1,
		"Subnets.member.2":        subnet2,
		"SecurityGroups.member.1": vpcsgId,
	}, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return nil, err
	}

	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error creating internet application load balancer: ", err)
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
	var albResponse CreateLoadBalancerResponse
	if err := xml.NewDecoder(resp.Body).Decode(&albResponse); err != nil {
		fmt.Println("Error parsing response: ", err)
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}
	fmt.Println("Created internet application load balancer: ", albResponse.CreateLoadBalancerResult.LoadBalancers.Member.LoadBalancerArn)
	return &albResponse, nil
}
func (c *Client) DeleteLoadbalancer(ctx context.Context, arn string) error {

	req, err := c.newRequest(ctx, http.MethodPut, map[string]string{
		"Action":          "DeleteLoadBalancer",
		"LoadBalancerArn": arn,
	}, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return err
	}

	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error Deleting load balancer: ", err)
		return err
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}
	//fmt.Println("Response Body:", string(bodyBytes))

	// Reset the response body for decoding
	resp.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	return nil
}
func (c *Client) DeleteTargetGroup(ctx context.Context, arn string) error {

	params := map[string]string{
		"Action":         "DeleteTargetGroup",
		"TargetGroupArn": arn,
	}
	req, err := c.newRequest(ctx, http.MethodGet, params, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return err
	}
	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error Deleting target group: ", err)
		return err
	}
	defer resp.Body.Close()

	return nil

}
