//go:build integration

package postgres

import (
	"testing"

	"github.com/byteport/api/testhelpers"
)

// setupTestDB provides a Postgres-backed test database for integration testing.
func setupTestDB(t *testing.T) *testhelpers.TestDB {
	return testhelpers.SetupTestDB(t)
}
