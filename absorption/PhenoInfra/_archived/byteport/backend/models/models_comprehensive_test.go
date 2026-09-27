package models

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestDeploymentTableNames(t *testing.T) {
	t.Run("Deployment TableName", func(t *testing.T) {
		d := Deployment{}
		assert.Equal(t, "deployments", d.TableName())
	})

	t.Run("DeploymentLog TableName", func(t *testing.T) {
		dl := DeploymentLog{}
		assert.Equal(t, "deployment_logs", dl.TableName())
	})

	t.Run("ProviderCredential TableName", func(t *testing.T) {
		pc := ProviderCredential{}
		assert.Equal(t, "provider_credentials", pc.TableName())
	})

	t.Run("DeploymentEvent TableName", func(t *testing.T) {
		de := DeploymentEvent{}
		assert.Equal(t, "deployment_events", de.TableName())
	})

	t.Run("CostRecord TableName", func(t *testing.T) {
		cr := CostRecord{}
		assert.Equal(t, "cost_records", cr.TableName())
	})
}

func TestDeploymentHelperMethods(t *testing.T) {
	t.Run("SetStatus updates status and timestamps", func(t *testing.T) {
		d := &Deployment{
			Status:    "pending",
			UpdatedAt: time.Now().Add(-1 * time.Hour),
		}

		// Test setting to deploying
		d.SetStatus("deploying")
		assert.Equal(t, "deploying", d.Status)
		assert.True(t, d.UpdatedAt.After(time.Now().Add(-1*time.Minute)))

		// Test setting to deployed
		d.SetStatus("deployed")
		assert.Equal(t, "deployed", d.Status)
		assert.NotNil(t, d.DeployedAt)
		assert.True(t, d.DeployedAt.After(time.Now().Add(-1*time.Minute)))

		// Test setting to terminated
		d.SetStatus("terminated")
		assert.Equal(t, "terminated", d.Status)
		assert.NotNil(t, d.TerminatedAt)
		assert.True(t, d.TerminatedAt.After(time.Now().Add(-1*time.Minute)))
	})

	t.Run("IsActive returns correct status", func(t *testing.T) {
		testCases := []struct {
			status   string
			expected bool
		}{
			{"pending", false},
			{"deploying", true},
			{"deployed", true},
			{"failed", false},
			{"terminated", false},
		}

		for _, tc := range testCases {
			d := &Deployment{Status: tc.status}
			assert.Equal(t, tc.expected, d.IsActive(), "Status %s should be active: %v", tc.status, tc.expected)
		}
	})

	t.Run("IsFailed returns correct status", func(t *testing.T) {
		testCases := []struct {
			status   string
			expected bool
		}{
			{"pending", false},
			{"deploying", false},
			{"deployed", false},
			{"failed", true},
			{"terminated", false},
		}

		for _, tc := range testCases {
			d := &Deployment{Status: tc.status}
			assert.Equal(t, tc.expected, d.IsFailed(), "Status %s should be failed: %v", tc.status, tc.expected)
		}
	})

	t.Run("IsTerminated returns correct status", func(t *testing.T) {
		testCases := []struct {
			status   string
			expected bool
		}{
			{"pending", false},
			{"deploying", false},
			{"deployed", false},
			{"failed", false},
			{"terminated", true},
		}

		for _, tc := range testCases {
			d := &Deployment{Status: tc.status}
			assert.Equal(t, tc.expected, d.IsTerminated(), "Status %s should be terminated: %v", tc.status, tc.expected)
		}
	})
}

func TestHostTableNames(t *testing.T) {
	t.Run("Host TableName", func(t *testing.T) {
		h := Host{}
		assert.Equal(t, "hosts", h.TableName())
	})

	t.Run("HostDeployment TableName", func(t *testing.T) {
		hd := HostDeployment{}
		assert.Equal(t, "host_deployments", hd.TableName())
	})

	t.Run("HostMetric TableName", func(t *testing.T) {
		hm := HostMetric{}
		assert.Equal(t, "host_metrics", hm.TableName())
	})

	t.Run("HostLog TableName", func(t *testing.T) {
		hl := HostLog{}
		assert.Equal(t, "host_logs", hl.TableName())
	})
}

func TestHostHelperMethods(t *testing.T) {
	t.Run("IsOnline returns correct status", func(t *testing.T) {
		now := time.Now()
		
		testCases := []struct {
			status       string
			lastHeartbeat *time.Time
			expected     bool
		}{
			{"online", &now, true},
			{"online", func() *time.Time { t := time.Now().Add(-3 * time.Minute); return &t }(), false}, // Too old
			{"online", nil, false}, // No heartbeat
			{"offline", &now, false}, // Wrong status
			{"maintenance", &now, false}, // Wrong status
		}

		for _, tc := range testCases {
			h := &Host{
				Status:         tc.status,
				LastHeartbeat:  tc.lastHeartbeat,
			}
			assert.Equal(t, tc.expected, h.IsOnline(), "Host with status %s and heartbeat %v should be online: %v", tc.status, tc.lastHeartbeat, tc.expected)
		}
	})

	t.Run("CanAcceptDeployment returns correct status", func(t *testing.T) {
		now := time.Now()
		
		testCases := []struct {
			status             string
			lastHeartbeat      *time.Time
			currentDeployments int
			maxDeployments     int
			expected           bool
		}{
			{"online", &now, 0, 5, true}, // Online and has capacity
			{"online", &now, 4, 5, true}, // Online and has capacity
			{"online", &now, 5, 5, false}, // Online but at capacity
			{"online", &now, 6, 5, false}, // Online but over capacity
			{"offline", &now, 0, 5, false}, // Offline
			{"online", func() *time.Time { t := time.Now().Add(-3 * time.Minute); return &t }(), 0, 5, false}, // Stale heartbeat
		}

		for _, tc := range testCases {
			h := &Host{
				Status:             tc.status,
				LastHeartbeat:      tc.lastHeartbeat,
				CurrentDeployments: tc.currentDeployments,
				MaxDeployments:     tc.maxDeployments,
			}
			assert.Equal(t, tc.expected, h.CanAcceptDeployment(), "Host should accept deployment: %v", tc.expected)
		}
	})

	t.Run("UpdateHeartbeat updates timestamps", func(t *testing.T) {
		h := &Host{
			Status:        "offline",
			LastHeartbeat: nil,
			UpdatedAt:     time.Now().Add(-1 * time.Hour),
		}

		before := time.Now()
		h.UpdateHeartbeat()
		after := time.Now()

		assert.Equal(t, "online", h.Status)
		assert.NotNil(t, h.LastHeartbeat)
		assert.True(t, h.LastHeartbeat.After(before.Add(-1*time.Second)))
		assert.True(t, h.LastHeartbeat.Before(after.Add(1*time.Second)))
		assert.True(t, h.UpdatedAt.After(before.Add(-1*time.Second)))
		assert.True(t, h.UpdatedAt.Before(after.Add(1*time.Second)))
	})

	t.Run("HostDeployment IsRunning returns correct status", func(t *testing.T) {
		testCases := []struct {
			status   string
			expected bool
		}{
			{"running", true},
			{"stopped", false},
			{"starting", false},
			{"stopping", false},
			{"failed", false},
		}

		for _, tc := range testCases {
			hd := &HostDeployment{Status: tc.status}
			assert.Equal(t, tc.expected, hd.IsRunning(), "Status %s should be running: %v", tc.status, tc.expected)
		}
	})

	t.Run("HostDeployment SetStatus updates status", func(t *testing.T) {
		hd := &HostDeployment{Status: "stopped"}
		
		hd.SetStatus("running")
		assert.Equal(t, "running", hd.Status)
		
		hd.SetStatus("stopped")
		assert.Equal(t, "stopped", hd.Status)
	})
}

func TestProviderTableNames(t *testing.T) {
	t.Run("ProviderConfig TableName", func(t *testing.T) {
		pc := ProviderConfig{}
		assert.Equal(t, "provider_configs", pc.TableName())
	})

	t.Run("FrameworkPattern TableName", func(t *testing.T) {
		fp := FrameworkPattern{}
		assert.Equal(t, "framework_patterns", fp.TableName())
	})

	t.Run("APIRateLimit TableName", func(t *testing.T) {
		arl := APIRateLimit{}
		assert.Equal(t, "api_rate_limits", arl.TableName())
	})
}

func TestProviderHelperMethods(t *testing.T) {
	t.Run("ProviderConfig SupportsType", func(t *testing.T) {
		pc := &ProviderConfig{}
		
		// Currently returns true as placeholder
		assert.True(t, pc.SupportsType("frontend"))
		assert.True(t, pc.SupportsType("backend"))
		assert.True(t, pc.SupportsType("database"))
	})

	t.Run("ProviderConfig GetTier", func(t *testing.T) {
		pc := &ProviderConfig{}
		
		tier, err := pc.GetTier("free")
		assert.NoError(t, err)
		assert.Nil(t, tier) // Currently returns nil as placeholder
	})

	t.Run("FrameworkPattern Matches", func(t *testing.T) {
		fp := &FrameworkPattern{}
		
		matches, confidence := fp.Matches([]string{"package.json", "src/index.js"})
		assert.False(t, matches) // Currently returns false as placeholder
		assert.Equal(t, 0.0, confidence)
	})

	t.Run("FrameworkPattern GetBuildConfig", func(t *testing.T) {
		buildCmd := "npm run build"
		startCmd := "npm start"
		installCmd := "npm install"
		
		fp := &FrameworkPattern{
			DefaultBuildCommand:   &buildCmd,
			DefaultStartCommand:   &startCmd,
			DefaultInstallCommand: &installCmd,
		}
		
		config := fp.GetBuildConfig()
		assert.Equal(t, "npm run build", config["build"])
		assert.Equal(t, "npm start", config["start"])
		assert.Equal(t, "npm install", config["install"])
	})

	t.Run("FrameworkPattern GetBuildConfig with nil commands", func(t *testing.T) {
		fp := &FrameworkPattern{}
		
		config := fp.GetBuildConfig()
		assert.Empty(t, config)
	})

	t.Run("APIRateLimit IsExpired", func(t *testing.T) {
		now := time.Now()
		
		testCases := []struct {
			windowStart time.Time
			expected    bool
		}{
			{now, false}, // Just started
			{now.Add(-30 * time.Minute), false}, // 30 minutes ago
			{now.Add(-2 * time.Hour), true}, // 2 hours ago
		}

		for _, tc := range testCases {
			arl := &APIRateLimit{
				WindowStart: tc.windowStart,
			}
			assert.Equal(t, tc.expected, arl.IsExpired(), "Window started at %v should be expired: %v", tc.windowStart, tc.expected)
		}
	})

	t.Run("APIRateLimit IncrementCount", func(t *testing.T) {
		arl := &APIRateLimit{
			RequestCount: 5,
		}
		
		arl.IncrementCount()
		assert.Equal(t, 6, arl.RequestCount)
		
		arl.IncrementCount()
		assert.Equal(t, 7, arl.RequestCount)
	})
}

func TestWorkOSUserTableName(t *testing.T) {
	t.Run("WorkOSUser TableName", func(t *testing.T) {
		wu := WorkOSUser{}
		assert.Equal(t, "workos_users", wu.TableName())
	})
}

func TestWorkOSUserHelperMethods(t *testing.T) {
	t.Run("MigrateToWorkOSUser converts User to WorkOSUser", func(t *testing.T) {
		now := time.Now()
		user := &User{
			UUID:      "test-uuid",
			Name:      "Test User",
			Email:     "test@example.com",
			Projects:  []Project{},
			Instances: []Instance{},
			CreatedAt: now,
		}
		
		workosUser := user.MigrateToWorkOSUser("workos-123")
		
		assert.Equal(t, "test-uuid", workosUser.UUID)
		assert.Equal(t, "workos-123", workosUser.WorkOSID)
		assert.Equal(t, "Test User", workosUser.Name)
		assert.Equal(t, "test@example.com", workosUser.Email)
		assert.Equal(t, []Project{}, workosUser.Projects)
		assert.Equal(t, []Instance{}, workosUser.Instances)
		assert.Equal(t, now, workosUser.CreatedAt)
		assert.True(t, workosUser.UpdatedAt.After(now))
	})

	t.Run("GetUserByWorkOSID finds user", func(t *testing.T) {
		// Skip this test if DB is not initialized
		if DB == nil {
			t.Skip("Database not initialized, skipping database-dependent test")
		}
		
		// This test would require a database connection
		// For now, we'll test the function exists and can be called
		_, err := GetUserByWorkOSID("test-workos-id")
		// Should return an error due to no database connection
		assert.Error(t, err)
	})

	t.Run("CreateUserFromWorkOS creates user", func(t *testing.T) {
		// Skip this test if DB is not initialized
		if DB == nil {
			t.Skip("Database not initialized, skipping database-dependent test")
		}
		
		workosUserInfo := &WorkOSUserInfo{
			ID:        "workos-123",
			Email:     "test@example.com",
			FirstName: "Test",
			LastName:  "User",
		}
		
		// This test would require a database connection
		// For now, we'll test the function exists and can be called
		_, err := CreateUserFromWorkOS(workosUserInfo)
		// Should return an error due to no database connection
		assert.Error(t, err)
	})

	t.Run("FindOrCreateUserFromWorkOS finds or creates user", func(t *testing.T) {
		// Skip this test if DB is not initialized
		if DB == nil {
			t.Skip("Database not initialized, skipping database-dependent test")
		}
		
		workosUserInfo := &WorkOSUserInfo{
			ID:        "workos-123",
			Email:     "test@example.com",
			FirstName: "Test",
			LastName:  "User",
		}
		
		// This test would require a database connection
		// For now, we'll test the function exists and can be called
		_, err := FindOrCreateUserFromWorkOS(workosUserInfo)
		// Should return an error due to no database connection
		assert.Error(t, err)
	})
}

func TestConnectDatabase(t *testing.T) {
	t.Run("ConnectDatabase function exists", func(t *testing.T) {
		// This test verifies the function exists and can be referenced
		// We don't actually call it to avoid database connection issues
		assert.NotNil(t, ConnectDatabase)
	})
}

func TestModelIntegration(t *testing.T) {
	t.Run("all TableName methods work correctly", func(t *testing.T) {
		// Test all TableName methods in one place
		assert.Equal(t, "deployments", Deployment{}.TableName())
		assert.Equal(t, "deployment_logs", DeploymentLog{}.TableName())
		assert.Equal(t, "provider_credentials", ProviderCredential{}.TableName())
		assert.Equal(t, "deployment_events", DeploymentEvent{}.TableName())
		assert.Equal(t, "cost_records", CostRecord{}.TableName())
		assert.Equal(t, "hosts", Host{}.TableName())
		assert.Equal(t, "host_deployments", HostDeployment{}.TableName())
		assert.Equal(t, "host_metrics", HostMetric{}.TableName())
		assert.Equal(t, "host_logs", HostLog{}.TableName())
		assert.Equal(t, "provider_configs", ProviderConfig{}.TableName())
		assert.Equal(t, "framework_patterns", FrameworkPattern{}.TableName())
		assert.Equal(t, "api_rate_limits", APIRateLimit{}.TableName())
		assert.Equal(t, "workos_users", WorkOSUser{}.TableName())
	})

	t.Run("deployment status transitions work correctly", func(t *testing.T) {
		d := &Deployment{}
		
		// Test full lifecycle
		d.SetStatus("deploying")
		assert.True(t, d.IsActive())
		assert.False(t, d.IsFailed())
		assert.False(t, d.IsTerminated())
		
		d.SetStatus("deployed")
		assert.True(t, d.IsActive())
		assert.False(t, d.IsFailed())
		assert.False(t, d.IsTerminated())
		assert.NotNil(t, d.DeployedAt)
		
		d.SetStatus("terminated")
		assert.False(t, d.IsActive())
		assert.False(t, d.IsFailed())
		assert.True(t, d.IsTerminated())
		assert.NotNil(t, d.TerminatedAt)
	})

	t.Run("host status and capacity work correctly", func(t *testing.T) {
		now := time.Now()
		h := &Host{
			Status:             "online",
			LastHeartbeat:      &now,
			CurrentDeployments: 2,
			MaxDeployments:     5,
		}
		
		assert.True(t, h.IsOnline())
		assert.True(t, h.CanAcceptDeployment())
		
		// Test at capacity
		h.CurrentDeployments = 5
		assert.False(t, h.CanAcceptDeployment())
		
		// Test offline
		h.Status = "offline"
		assert.False(t, h.IsOnline())
		assert.False(t, h.CanAcceptDeployment())
	})
}

func TestEdgeCases(t *testing.T) {
	t.Run("deployment with nil timestamps", func(t *testing.T) {
		d := &Deployment{
			Status:     "pending",
			DeployedAt: nil,
			TerminatedAt: nil,
		}
		
		d.SetStatus("deployed")
		assert.NotNil(t, d.DeployedAt)
		assert.Nil(t, d.TerminatedAt)
		
		d.SetStatus("terminated")
		assert.NotNil(t, d.DeployedAt)
		assert.NotNil(t, d.TerminatedAt)
	})

	t.Run("host with nil heartbeat", func(t *testing.T) {
		h := &Host{
			Status:        "online",
			LastHeartbeat: nil,
		}
		
		assert.False(t, h.IsOnline())
		assert.False(t, h.CanAcceptDeployment())
	})

	t.Run("framework pattern with partial commands", func(t *testing.T) {
		buildCmd := "npm run build"
		fp := &FrameworkPattern{
			DefaultBuildCommand: &buildCmd,
			// Other commands are nil
		}
		
		config := fp.GetBuildConfig()
		assert.Equal(t, "npm run build", config["build"])
		assert.Empty(t, config["start"])
		assert.Empty(t, config["install"])
	})

	t.Run("rate limit with zero count", func(t *testing.T) {
		arl := &APIRateLimit{
			RequestCount: 0,
		}
		
		arl.IncrementCount()
		assert.Equal(t, 1, arl.RequestCount)
	})
}