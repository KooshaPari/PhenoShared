package s3

import (
	"context"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
)

// Client provides an interface for interacting with the S3 API.

func (c *Client) CreateBucket(ctx context.Context, name string) error {
	fmt.Println("Creating bucket: ", name)
	req, err := c.newRequest(ctx, http.MethodPut, "", name, nil)
	if err != nil {
		fmt.Println("Error creating request: ", err)
		return err
	}

	resp, err := c.do(req)
	if err != nil {
		fmt.Println("Error creating bucket: ", err)
		return err
	}
	defer resp.Body.Close()
	return nil
}

// ListBuckets returns a list of buckets.
func (c *Client) ListBuckets(ctx context.Context) (*ListBucketsResponse, error) {
	req, err := c.newRequest(ctx, http.MethodGet, "", "", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var results ListBucketsResponse
	if err := xml.NewDecoder(resp.Body).Decode(&results); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &results, nil
}

// ListObjects returns a list of objects within a specified bucket.
func (c *Client) ListObjects(ctx context.Context, bucketName string) (*ListObjectsResponse, error) {
	req, err := c.newRequest(ctx, http.MethodGet, bucketName, "", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var results ListObjectsResponse
	if err := xml.NewDecoder(resp.Body).Decode(&results); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &results, nil
}

// PutObject uploads an object to the specified bucket.
func (c *Client) PutObject(ctx context.Context, bucketName, objectName string, data []byte) error {
	req, err := c.newRequest(ctx, http.MethodPut, bucketName, objectName, data)
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

// GetObject fetches an object from the specified bucket.
// GetObject fetches an object from the specified bucket along with its metadata.
func (c *Client) GetObject(ctx context.Context, bucketName, objectName string) (io.ReadCloser, *ObjectMetadata, error) {
	req, err := c.newRequest(ctx, http.MethodGet, bucketName, objectName, nil)
	if err != nil {
		return nil, nil, err
	}

	resp, err := c.do(req)
	if err != nil {
		return nil, nil, err
	}

	// Extract metadata from response headers
	metadata := &ObjectMetadata{
		ETag:         resp.Header.Get("ETag"),
		LastModified: resp.Header.Get("Last-Modified"),
		Size:         resp.ContentLength,
		ContentType:  resp.Header.Get("Content-Type"),
		StorageClass: resp.Header.Get("x-amz-storage-class"),
	}

	return resp.Body, metadata, nil
}

// DeleteObject deletes an object from the specified bucket.
func (c *Client) DeleteObject(ctx context.Context, bucketName, objectName string) error {
	req, err := c.newRequest(ctx, http.MethodDelete, bucketName, objectName, nil)
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
func (c *Client) DeleteBucket(ctx context.Context, bucketName string) error {
	req, err := c.newRequest(ctx, http.MethodDelete, bucketName, "", nil)
	if err != nil {
		return err
	}

	resp, err := c.do(req)
	if err != nil {
		// check for NoSuchBucket error
		fmt.Println("Error deleting bucket: ", err)
		return err
	}
	defer resp.Body.Close()

	return nil
}
