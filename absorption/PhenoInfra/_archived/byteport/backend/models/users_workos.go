package models

import "time"

// WorkOSUser represents the new user model for WorkOS AuthKit integration
// This will eventually replace the existing User model
type WorkOSUser struct {
	UUID      string     `json:"uuid" gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	WorkOSID  string     `json:"workos_id" gorm:"column:work_os_id;type:varchar(255);uniqueIndex;not null"` // WorkOS user ID
	Name      string     `json:"name" gorm:"type:varchar(255);not null"`
	Email     string     `json:"email" gorm:"type:varchar(255);uniqueIndex;not null"`
	Projects  []Project  `json:"projects" gorm:"foreignKey:Owner;references:UUID"`
	Instances []Instance `json:"instances" gorm:"foreignKey:Owner;references:UUID"`
	CreatedAt time.Time  `json:"created_at" gorm:"autoCreateTime"`
	UpdatedAt time.Time  `json:"updated_at" gorm:"autoUpdateTime"`
}

// TableName specifies the table name for WorkOSUser
func (WorkOSUser) TableName() string {
	return "workos_users" // Use different table name during migration
}

// WorkOSAuthRequest represents the OAuth callback request from WorkOS
type WorkOSAuthRequest struct {
	Code  string `json:"code" binding:"required"`
	State string `json:"state"`
}

// WorkOSUserInfo represents user information received from WorkOS
type WorkOSUserInfo struct {
	ID        string `json:"id"`
	Email     string `json:"email"`
	FirstName string `json:"first_name"`
	LastName  string `json:"last_name"`
}

// MigrateToWorkOSUser converts an existing User to a WorkOSUser
func (u *User) MigrateToWorkOSUser(workosID string) *WorkOSUser {
	updatedAt := time.Now()
	if !updatedAt.After(u.CreatedAt) {
		updatedAt = u.CreatedAt.Add(time.Nanosecond)
	}

	return &WorkOSUser{
		UUID:      u.UUID,
		WorkOSID:  workosID,
		Name:      u.Name,
		Email:     u.Email,
		Projects:  u.Projects,
		Instances: u.Instances,
		CreatedAt: u.CreatedAt,
		UpdatedAt: updatedAt,
	}
}

// Migration functions for database schema updates

// GetUserByWorkOSID finds a user by their WorkOS ID
func GetUserByWorkOSID(workosID string) (*WorkOSUser, error) {
	var user WorkOSUser
	err := DB.Where("work_os_id = ?", workosID).First(&user).Error
	return &user, err
}

// CreateUserFromWorkOS creates a new user from WorkOS user info
func CreateUserFromWorkOS(workosUserInfo *WorkOSUserInfo) (*WorkOSUser, error) {
	user := &WorkOSUser{
		WorkOSID:  workosUserInfo.ID,
		Name:      workosUserInfo.FirstName + " " + workosUserInfo.LastName,
		Email:     workosUserInfo.Email,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	err := DB.Create(user).Error
	return user, err
}

// FindOrCreateUserFromWorkOS finds an existing user or creates a new one
func FindOrCreateUserFromWorkOS(workosUserInfo *WorkOSUserInfo) (*WorkOSUser, error) {
	user, err := GetUserByWorkOSID(workosUserInfo.ID)
	if err == nil {
		return user, nil
	}

	// Try to find by email in case of existing user migration
	var existingUser WorkOSUser
	err = DB.Where("email = ?", workosUserInfo.Email).First(&existingUser).Error
	if err == nil {
		existingUser.WorkOSID = workosUserInfo.ID
		err = DB.Save(&existingUser).Error
		return &existingUser, err
	}

	// Create new user
	return CreateUserFromWorkOS(workosUserInfo)
}
