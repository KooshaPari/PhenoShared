package deployment

// Status represents a deployment status value object
type Status string

const (
	StatusPending      Status = "pending"
	StatusDetecting    Status = "detecting"
	StatusProvisioning Status = "provisioning"
	StatusDeploying    Status = "deploying"
	StatusDeployed     Status = "deployed"
	StatusFailed       Status = "failed"
	StatusTerminated   Status = "terminated"
)

// IsValid checks if the status is valid
func (s Status) IsValid() bool {
	switch s {
	case StatusPending, StatusDetecting, StatusProvisioning,
		StatusDeploying, StatusDeployed, StatusFailed, StatusTerminated:
		return true
	default:
		return false
	}
}

// String returns the string representation
func (s Status) String() string {
	return string(s)
}

// IsFinal checks if status is in a final state
func (s Status) IsFinal() bool {
	return s == StatusDeployed || s == StatusFailed || s == StatusTerminated
}

// IsTransitional checks if status is transitional
func (s Status) IsTransitional() bool {
	return s == StatusDetecting || s == StatusProvisioning || s == StatusDeploying
}
