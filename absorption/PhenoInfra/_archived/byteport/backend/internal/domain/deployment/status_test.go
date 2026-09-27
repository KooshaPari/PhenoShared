package deployment

import "testing"

func TestStatus_IsValid(t *testing.T) {
	tests := []struct {
		name   string
		status Status
		want   bool
	}{
		{"pending valid", StatusPending, true},
		{"detecting valid", StatusDetecting, true},
		{"provisioning valid", StatusProvisioning, true},
		{"deploying valid", StatusDeploying, true},
		{"deployed valid", StatusDeployed, true},
		{"failed valid", StatusFailed, true},
		{"terminated valid", StatusTerminated, true},
		{"invalid empty", Status(""), false},
		{"invalid unknown", Status("unknown"), false},
		{"invalid typo", Status("pendding"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.status.IsValid(); got != tt.want {
				t.Errorf("Status.IsValid() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestStatus_IsFinal(t *testing.T) {
	tests := []struct {
		name   string
		status Status
		want   bool
	}{
		{"pending not final", StatusPending, false},
		{"detecting not final", StatusDetecting, false},
		{"provisioning not final", StatusProvisioning, false},
		{"deploying not final", StatusDeploying, false},
		{"deployed final", StatusDeployed, true},
		{"failed final", StatusFailed, true},
		{"terminated final", StatusTerminated, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.status.IsFinal(); got != tt.want {
				t.Errorf("Status.IsFinal() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestStatus_IsTransitional(t *testing.T) {
	tests := []struct {
		name   string
		status Status
		want   bool
	}{
		{"pending transitional", StatusPending, false}, // pending is initial, not transitional
		{"detecting transitional", StatusDetecting, true},
		{"provisioning transitional", StatusProvisioning, true},
		{"deploying transitional", StatusDeploying, true},
		{"deployed not transitional", StatusDeployed, false},
		{"failed not transitional", StatusFailed, false},
		{"terminated not transitional", StatusTerminated, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.status.IsTransitional(); got != tt.want {
				t.Errorf("Status.IsTransitional() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestStatus_String(t *testing.T) {
	tests := []struct {
		name   string
		status Status
		want   string
	}{
		{"pending", StatusPending, "pending"},
		{"detecting", StatusDetecting, "detecting"},
		{"provisioning", StatusProvisioning, "provisioning"},
		{"deploying", StatusDeploying, "deploying"},
		{"deployed", StatusDeployed, "deployed"},
		{"failed", StatusFailed, "failed"},
		{"terminated", StatusTerminated, "terminated"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.status.String(); got != tt.want {
				t.Errorf("Status.String() = %v, want %v", got, tt.want)
			}
		})
	}
}
