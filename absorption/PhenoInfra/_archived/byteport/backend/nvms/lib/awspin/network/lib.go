package network

import (
	"encoding/xml"
	aws "nvms/lib/awspin"
)

type Client struct {
	config       aws.Config
	endpointURL  string
	usePathStyle bool
}

type CreateLoadBalancerResponse struct {
	XMLName                  xml.Name `xml:"CreateLoadBalancerResponse"`
	CreateLoadBalancerResult struct {
		LoadBalancers struct {
			Member struct {
				LoadBalancerArn   string `xml:"LoadBalancerArn"`
				Scheme            string `xml:"Scheme"`
				AvailabilityZones struct {
					Member []struct {
						SubnetId              string `xml:"SubnetId"`
						ZoneName              string `xml:"ZoneName"`
						LoadBalancerAddresses string `xml:"LoadBalancerAddresses"`
					} `xml:"member"`
				} `xml:"AvailabilityZones"`
				DNSName               string `xml:"DNSName"`
				Type                  string `xml:"Type"`
				IpAddressType         string `xml:"IpAddressType"`
				LoadBalancerName      string `xml:"LoadBalancerName"`
				VpcId                 string `xml:"VpcId"`
				CanonicalHostedZoneId string `xml:"CanonicalHostedZoneId"`
				CreatedTime           string `xml:"CreatedTime"`
				SecurityGroups        struct {
					Member []string `xml:"member"`
				} `xml:"SecurityGroups"`
				State struct {
					Code string `xml:"Code"`
				} `xml:"State"`
			} `xml:"member"`
		} `xml:"LoadBalancers"`
	} `xml:"CreateLoadBalancerResult"`
	ResponseMetadata struct {
		RequestId string `xml:"RequestId"`
	} `xml:"ResponseMetadata"`
}

type CreateListenerResponse struct {
	XMLName              xml.Name `xml:"CreateListenerResponse"`
	CreateListenerResult struct {
		Listeners struct {
			Member struct {
				LoadBalancerArn string `xml:"LoadBalancerArn"`
				Protocol        string `xml:"Protocol"`
				Port            string `xml:"Port"`
				ListenerArn     string `xml:"ListenerArn"`
				DefaultActions  struct {
					Member []struct {
						Type           string `xml:"Type"`
						TargetGroupArn string `xml:"TargetGroupArn"`
					} `xml:"member"`
				} `xml:"DefaultActions"`
			} `xml:"member"`
		} `xml:"Listeners"`
	} `xml:"CreateListenerResult"`
	ResponseMetadata struct {
		RequestId string `xml:"RequestId"`
	} `xml:"ResponseMetadata"`
}

type CreateTargetGroupResponse struct {
	XMLName                 xml.Name `xml:"CreateTargetGroupResponse"`
	CreateTargetGroupResult struct {
		TargetGroups struct {
			Member struct {
				TargetGroupArn             string `xml:"TargetGroupArn"`
				TargetGroupName            string `xml:"TargetGroupName"`
				Protocol                   string `xml:"Protocol"`
				Port                       string `xml:"Port"`
				VpcId                      string `xml:"VpcId"`
				HealthCheckProtocol        string `xml:"HealthCheckProtocol"`
				HealthCheckPort            string `xml:"HealthCheckPort"`
				HealthCheckPath            string `xml:"HealthCheckPath"`
				HealthCheckTimeoutSeconds  string `xml:"HealthCheckTimeoutSeconds"`
				HealthyThresholdCount      string `xml:"HealthyThresholdCount"`
				UnhealthyThresholdCount    string `xml:"UnhealthyThresholdCount"`
				HealthCheckIntervalSeconds string `xml:"HealthCheckIntervalSeconds"`
				Matcher                    struct {
					HttpCode string `xml:"HttpCode"`
				} `xml:"Matcher"`
			} `xml:"member"`
		} `xml:"TargetGroups"`
	} `xml:"CreateTargetGroupResult"`
	ResponseMetadata struct {
		RequestId string `xml:"RequestId"`
	} `xml:"ResponseMetadata"`
}

type CreateRuleResponse struct {
	XMLName          xml.Name `xml:"CreateRuleResponse"`
	CreateRuleResult struct {
		Rules struct {
			Member struct {
				RuleArn    string `xml:"RuleArn"`
				Priority   string `xml:"Priority"`
				IsDefault  string `xml:"IsDefault"`
				Conditions struct {
					Member []struct {
						Field  string `xml:"Field"`
						Values struct {
							Member []string `xml:"member"`
						} `xml:"Values"`
					} `xml:"member"`
				} `xml:"Conditions"`
				Actions struct {
					Member []struct {
						Type           string `xml:"Type"`
						TargetGroupArn string `xml:"TargetGroupArn"`
					} `xml:"member"`
				} `xml:"Actions"`
			} `xml:"member"`
		} `xml:"Rules"`
	} `xml:"CreateRuleResult"`
	ResponseMetadata struct {
		RequestId string `xml:"RequestId"`
	} `xml:"ResponseMetadata"`
}
