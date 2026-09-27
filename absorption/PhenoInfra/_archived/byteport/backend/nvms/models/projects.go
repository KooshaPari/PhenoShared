package models

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
)

type Project struct {
	UUID  string `json:"uuid"`
	Owner string `json:"owner"`
	User  User   `json:"user"`
	Name  string `json:"name"`

	RepositoryID    string     `json:"repository_id"`
	Repository      Repository `json:"repository"`
	DeploymentsJSON string     `gorm:"type:jsonb;column:deployments"`
	NvmsConfig      NVMS       `json:"nvms_config"`
	Readme          string     `json:"readme"`
	Description     string     `json:"description"`
	LastUpdated     time.Time  `json:"last_updated"`
	Platform        string     `json:"platform"`
	AccessURL       string     `json:"access_url"`
	Type            string     `json:"type"`

	deployments map[string]Instance
}

func (p *Project) GetDeploys() map[string]Instance {
	return p.deployments
}
func (p *Project) GetDeploy(key string) Instance {
	return p.deployments[key]
}
func (p *Project) SetDeploy(deploy map[string]Instance) {
	p.deployments = deploy
}
func (p *Project) AppendDeploy(key string, deploy Instance) {
	p.deployments[key] = deploy
}
func (p *Project) DeleteDeploy(key string) {
	delete(p.deployments, key)
}
func (p *Project) SetDeploys(deploy map[string]Instance) {
	p.deployments = deploy
}
func (p *Project) CreateDeploys() {
	p.deployments = make(map[string]Instance)
}
func (p *Project) BeforeSave() error {
	fmt.Println("BeforeSave")
	if p.deployments != nil {
		fmt.Println("Saving deployments: ", p.deployments)
		data, err := json.Marshal(p.deployments)
		if err != nil {
			return err
		}
		p.DeploymentsJSON = string(data)
		fmt.Println("Saving deployments: ", p.DeploymentsJSON)
	}
	if p.UUID == "" {
		fmt.Println("Generating UUID")
		p.UUID = uuid.New().String()
	}
	return nil
}
