package ec2

import (
	"context"
	"encoding/hex"
	"encoding/xml"
	"fmt"
	"net/http"
	"net/url"
	aws "nvms/lib/awspin"
	"sort"
	"strings"
	"time"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
)

// NewEC2 creates a new EC2 Client
func NewEC2(config aws.Config) (*Client, error) {
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

	// Add required AWS Query API parameters
	params["Version"] = "2016-11-15"
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

	//fmt.Printf("Request URL: %s\n", u.String())

	// Create request with minimal headers
	req, err := http.NewRequestWithContext(ctx, method, u.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("host", u.Host)
	req.Header.Set("user-agent", "byteport")

	//fmt.Printf("Request headers: %+v\n", req.Header)
	return req, nil
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

// Client provides an interface for interacting with the EC2 API
type Client struct {
	config       aws.Config
	endpointURL  string
	usePathStyle bool
}

// Instance represents an EC2 instance
type Instance struct {
	InstanceId string `xml:"instanceId"`
	ImageId    string `xml:"imageId"`
	State      struct {
		Code int    `xml:"code"`
		Name string `xml:"name"`
	} `xml:"instanceState"`
	PrivateDnsName string   `xml:"privateDnsName"`
	DnsName        string   `xml:"dnsName"`
	Reason         string   `xml:"reason"`
	KeyName        string   `xml:"keyName"`
	AmiLaunchIndex int      `xml:"amiLaunchIndex"`
	ProductCodes   []string `xml:"productCodes"`
	InstanceType   string   `xml:"instanceType"`
	LaunchTime     string   `xml:"launchTime"`
	Placement      struct {
		AvailabilityZone string `xml:"availabilityZone"`
		GroupName        string `xml:"groupName"`
	} `xml:"placement"`
	Monitoring struct {
		State string `xml:"state"`
	} `xml:"monitoring"`
	SubnetId         string `xml:"subnetId"`
	VpcId            string `xml:"vpcId"`
	PrivateIpAddress string `xml:"privateIpAddress"`
	SourceDestCheck  bool   `xml:"sourceDestCheck"`
	GroupSet         []struct {
		GroupId   string `xml:"groupId"`
		GroupName string `xml:"groupName"`
	} `xml:"groupSet>item"`
	Architecture       string `xml:"architecture"`
	RootDeviceType     string `xml:"rootDeviceType"`
	RootDeviceName     string `xml:"rootDeviceName"`
	BlockDeviceMapping []struct {
		DeviceName string `xml:"deviceName"`
		Ebs        struct {
			VolumeId            string `xml:"volumeId"`
			Status              string `xml:"status"`
			AttachTime          string `xml:"attachTime"`
			DeleteOnTermination bool   `xml:"deleteOnTermination"`
		} `xml:"ebs"`
	} `xml:"blockDeviceMapping>item"`
	VirtualizationType string `xml:"virtualizationType"`
	ClientToken        string `xml:"clientToken"`
	TagSet             []struct {
		Key   string `xml:"key"`
		Value string `xml:"value"`
	} `xml:"tagSet>item"`
	Hypervisor          string `xml:"hypervisor"`
	NetworkInterfaceSet []struct {
		NetworkInterfaceId string `xml:"networkInterfaceId"`
		SubnetId           string `xml:"subnetId"`
		VpcId              string `xml:"vpcId"`
		Description        string `xml:"description"`
		OwnerId            string `xml:"ownerId"`
		Status             string `xml:"status"`
		MacAddress         string `xml:"macAddress"`
		PrivateIpAddress   string `xml:"privateIpAddress"`
		SourceDestCheck    bool   `xml:"sourceDestCheck"`
		GroupSet           []struct {
			GroupId   string `xml:"groupId"`
			GroupName string `xml:"groupName"`
		} `xml:"groupSet>item"`
		Attachment struct {
			AttachmentId        string `xml:"attachmentId"`
			DeviceIndex         int    `xml:"deviceIndex"`
			Status              string `xml:"status"`
			AttachTime          string `xml:"attachTime"`
			DeleteOnTermination bool   `xml:"deleteOnTermination"`
		} `xml:"attachment"`
		PrivateIpAddressesSet []struct {
			PrivateIpAddress string `xml:"privateIpAddress"`
			Primary          bool   `xml:"primary"`
		} `xml:"privateIpAddressesSet>item"`
	} `xml:"networkInterfaceSet>item"`
	EbsOptimized bool `xml:"ebsOptimized"`
}

// RunInstancesResponse represents the response from RunInstances
type RunInstancesResponse struct {
	XMLName       xml.Name   `xml:"RunInstancesResponse"`
	ReservationId string     `xml:"reservationId"`
	OwnerId       string     `xml:"ownerId"`
	Instances     []Instance `xml:"instancesSet>item"`
}

// DescribeInstancesResponse represents the response from DescribeInstances
type DescribeInstancesResponse struct {
	XMLName      xml.Name `xml:"DescribeInstancesResponse"`
	Reservations []struct {
		Instances []Instance `xml:"instancesSet>item"`
	} `xml:"reservationSet>item"`
}
type DescribeVpcsResponse struct {
	XMLName xml.Name `xml:"DescribeVpcsResponse"`
	Vpcs    []struct {
		VpcId                   string `xml:"vpcId"`
		OwnerId                 string `xml:"ownerId"`
		State                   string `xml:"state"`
		CidrBlock               string `xml:"cidrBlock"`
		CidrBlockAssociationSet []struct {
			CidrBlock      string `xml:"cidrBlock"`
			AssociationId  string `xml:"associationId"`
			CidrBlockState struct {
				State string `xml:"state"`
			} `xml:"cidrBlockState"`
		} `xml:"cidrBlockAssociationSet>item"`
		DhcpOptionsId string `xml:"dhcpOptionsId"`
		TagSet        []struct {
			Key   string `xml:"key"`
			Value string `xml:"value"`
		} `xml:"tagSet>item"`
		InstanceTenancy string `xml:"instanceTenancy"`
		IsDefault       bool   `xml:"isDefault"`
	} `xml:"vpcSet>item"`
}

type DescribeSecurityGroupsResponse struct {
	XMLName           xml.Name `xml:"DescribeSecurityGroupsResponse"`
	SecurityGroupInfo struct {
		Item struct {
			OwnerId          string `xml:"ownerId"`
			GroupId          string `xml:"groupId"`
			GroupName        string `xml:"groupName"`
			GroupDescription string `xml:"groupDescription"`
			VpcId            string `xml:"vpcId"`
			IpPermissions    []struct {
				Item struct {
					IpProtocol string `xml:"ipProtocol"`
					FromPort   int    `xml:"fromPort"`
					ToPort     int    `xml:"toPort"`
					Groups     []struct {
						Item struct {
							SecurityGroupRuleId    string `xml:"securityGroupRuleId"`
							UserId                 string `xml:"userId"`
							GroupId                string `xml:"groupId"`
							VpcId                  string `xml:"vpcId"`
							VpcPeeringConnectionId string `xml:"vpcPeeringConnectionId"`
							PeeringStatus          string `xml:"peeringStatus"`
						} `xml:"item"`
					} `xml:"groups"`
					IpRanges []struct {
						Item struct {
							CidrIp string `xml:"cidrIp"`
						} `xml:"item"`
					} `xml:"ipRanges"`
					PrefixListIds []struct {
						Item struct {
							PrefixListId string `xml:"prefixListId"`
						} `xml:"item"`
					} `xml:"prefixListIds"`
				} `xml:"item"`
			} `xml:"ipPermissions"`
			IpPermissionsEgress []struct {
				Item struct {
					IpProtocol string `xml:"ipProtocol"`
					Groups     []struct {
						Item struct {
							SecurityGroupRuleId    string `xml:"securityGroupRuleId"`
							UserId                 string `xml:"userId"`
							GroupId                string `xml:"groupId"`
							VpcId                  string `xml:"vpcId"`
							VpcPeeringConnectionId string `xml:"vpcPeeringConnectionId"`
							PeeringStatus          string `xml:"peeringStatus"`
						} `xml:"item"`
					} `xml:"groups"`
					IpRanges []struct {
						Item struct {
							CidrIp string `xml:"cidrIp"`
						} `xml:"item"`
					} `xml:"ipRanges"`
					PrefixListIds []struct {
						Item struct {
							PrefixListId string `xml:"prefixListId"`
						} `xml:"item"`
					} `xml:"prefixListIds"`
				} `xml:"item"`
			} `xml:"ipPermissionsEgress"`
		} `xml:"item"`
	} `xml:"securityGroupInfo"`
}
type DescribeSubnetsResponse struct {
	XMLName   xml.Name `xml:"DescribeSubnetsResponse"`
	SubnetSet []Subnet `xml:"subnetSet>item"`
}

type Subnet struct {
	SubnetId                    string                     `xml:"subnetId"`
	SubnetArn                   string                     `xml:"subnetArn"`
	State                       string                     `xml:"state"`
	OwnerId                     string                     `xml:"ownerId"`
	VpcId                       string                     `xml:"vpcId"`
	CidrBlock                   string                     `xml:"cidrBlock"`
	Ipv6CidrBlockAssociationSet []Ipv6CidrBlockAssociation `xml:"ipv6CidrBlockAssociationSet>item"`
	AvailableIpAddressCount     int                        `xml:"availableIpAddressCount"`
	AvailabilityZone            string                     `xml:"availabilityZone"`
	AvailabilityZoneId          string                     `xml:"availabilityZoneId"`
	DefaultForAz                bool                       `xml:"defaultForAz"`
	MapPublicIpOnLaunch         bool                       `xml:"mapPublicIpOnLaunch"`
	AssignIpv6AddressOnCreation bool                       `xml:"assignIpv6AddressOnCreation"`
}

type Ipv6CidrBlockAssociation struct {
	Ipv6CidrBlock      string `xml:"ipv6CidrBlock"`
	AssociationId      string `xml:"associationId"`
	Ipv6CidrBlockState struct {
		State string `xml:"state"`
	} `xml:"ipv6CidrBlockState"`
}
