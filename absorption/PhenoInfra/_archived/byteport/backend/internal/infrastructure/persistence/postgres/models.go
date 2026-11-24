package postgres

import (
	"time"

	"gorm.io/gorm"
)

// DeploymentModel represents the GORM model for deployments
type DeploymentModel struct {
	ID           uint           `gorm:"primaryKey"`
	UUID         string         `gorm:"uniqueIndex;not null"`
	Name         string         `gorm:"not null"`
	Owner        string         `gorm:"index;not null"`
	ProjectUUID  *string        `gorm:"index"`
	Status       string         `gorm:"index;not null"`
	Providers    string         `gorm:"type:jsonb"` // JSON-encoded map
	Services     string         `gorm:"type:jsonb"` // JSON-encoded array
	EnvVars      string         `gorm:"type:jsonb"` // JSON-encoded map
	BuildConfig  string         `gorm:"type:jsonb"` // JSON-encoded struct
	CostInfo     string         `gorm:"type:jsonb"` // JSON-encoded struct
	CreatedAt    time.Time
	UpdatedAt    time.Time
	DeployedAt   *time.Time
	TerminatedAt *time.Time
	DeletedAt    gorm.DeletedAt `gorm:"index"`
}

// TableName specifies the table name for GORM
func (DeploymentModel) TableName() string {
	return "deployments"
}
