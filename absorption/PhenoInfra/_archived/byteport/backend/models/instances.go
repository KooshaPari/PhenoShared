package models

import "time"

// add owning user uuid
type Instance struct {
	UUID          string        `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	Owner         string        `gorm:"type:uuid;not null;index"`
	ProjectUUID   string        `gorm:"type:uuid;index"`
	Name          string        `gorm:"not null"`
	Status        string        `gorm:"not null"`
	ResUUID       string        `gorm:"not null"`
	ResourcesJSON string        `gorm:"type:jsonb;column:resources"`
	Resources     []AWSResource `gorm:"foreignKey:InstanceID;references:UUID"`
	CreatedAt     time.Time     `gorm:"autoCreateTime"`
	UpdatedAt     time.Time     `gorm:"autoUpdateTime"`
}
