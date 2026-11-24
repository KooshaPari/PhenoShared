package models

// add owning user uuid

type Instance struct {
	UUID   string
	Name   string
	Status string
	Owner  string

	Resources []AWSResource
}
