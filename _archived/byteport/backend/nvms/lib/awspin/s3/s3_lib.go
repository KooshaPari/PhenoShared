package s3

import (
	"bytes"
	"context"
	"encoding/xml"
	"fmt"
	"net/http"
	"net/url"
	aws "nvms/lib/awspin"
	"strings"
	"time"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
)

// https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListBuckets.html#API_ListBuckets_ResponseSyntax
type ListBucketsResponse struct {
	Buckets []BucketInfo `xml:"Buckets>Bucket"`
	Owner   Owner
}

// https://docs.aws.amazon.com/AmazonS3/latest/API/API_Bucket.html
type BucketInfo struct {
	Name         string
	CreationDate time.Time
}

// https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html#API_ListObjects_ResponseSyntax
type ListObjectsResponse struct {
	CommonPrefixes []CommonPrefix
	Contents       []ObjectInfo
	Delimiter      string
	EncodingType   string
	IsTruncated    bool
	Marker         string
	MaxKeys        int
	Name           string
	NextMarker     string
	Prefix         string
}

// https://docs.aws.amazon.com/AmazonS3/latest/API/API_CommonPrefix.html
type CommonPrefix struct {
	Prefix string
}

// https://docs.aws.amazon.com/AmazonS3/latest/API/API_Object.html
type ObjectInfo struct {
	Key          string
	ETag         string
	Size         int
	LastModified time.Time
	StorageClass string
	Owner        Owner
}

// https://docs.aws.amazon.com/AmazonS3/latest/API/API_Owner.html
type Owner struct {
	DisplayName string
	ID          string
}

// ObjectMetadata contains metadata about an S3 object.
// This struct is returned along with the object content when fetching objects.
type ObjectMetadata struct {
	ETag         string
	LastModified time.Time
	Size         int64
	ContentType  string
	StorageClass string
}
type Client struct {
	config       aws.Config
	endpointURL  string
	usePathStyle bool
}

// New creates a new Client.
func NewS3(config aws.Config) (*Client, error) {
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
func (c *Client) buildEndpoint(bucketName, path string) (string, error) {
	u, err := url.Parse(c.endpointURL)
	if err != nil {
		return "", fmt.Errorf("failed to parse endpoint: %w", err)
	}

	if bucketName != "" {
		if c.usePathStyle {
			// LocalStack style: http://localhost:4566/bucket-name/path
			u = u.JoinPath(bucketName)
		} else {
			// AWS style: http://bucket-name.s3.amazonaws.com/path
			u.Host = bucketName + "." + u.Host
		}
	}

	if path != "" {
		u = u.JoinPath(path)
	}

	return u.String(), nil
}

func (c *Client) newRequest(ctx context.Context, method, bucketName, path string, body []byte) (*http.Request, error) {
	endpointURL, err := c.buildEndpoint(bucketName, path)
	if err != nil {
		return nil, err
	}

	u, err := url.Parse(endpointURL)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, method, endpointURL, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	var awsDate aws.AwsDate
	awsDate.Time = time.Now()

	payloadHash := aws.GetPayloadHash(body)
	req.Header.Set("host", u.Host)
	req.Header.Set("content-length", fmt.Sprintf("%d", len(body)))
	req.Header.Set("x-amz-content-sha256", payloadHash)
	req.Header.Set("x-amz-date", awsDate.GetTime())
	req.Header.Set("x-amz-security-token", c.config.SessionToken)
	req.Header.Set("user-agent", "byteport")
	req.Header.Set("authorization", aws.GetAuthorizationHeader(&c.config, req, &awsDate, payloadHash))
	//fmt.Println("Request: ", req)
	return req, nil
}

// do sends the request and handles any error response.
func (c *Client) do(req *http.Request) (*http.Response, error) {
	resp, err := spinhttp.Send(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}

	// Only checking for a status of 200 feels too specific.
	if resp.StatusCode != http.StatusOK {
		var errorResponse aws.ErrorResponse
		if err := xml.NewDecoder(resp.Body).Decode(&errorResponse); err != nil {
			return nil, fmt.Errorf("failed to parse response: %w", err)
		}
		if resp.StatusCode != http.StatusNotFound {
			return nil, errorResponse
		}
	}
	return resp, nil
}
