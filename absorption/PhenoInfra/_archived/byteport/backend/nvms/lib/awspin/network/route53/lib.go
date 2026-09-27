package route53

import aws "nvms/lib/awspin"

type Client struct {
	config       aws.Config
	endpointURL  string
	usePathStyle bool
}
