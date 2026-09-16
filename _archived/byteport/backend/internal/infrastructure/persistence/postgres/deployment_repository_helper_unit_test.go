//go:build !integration

package postgres

import (
	"testing"

	"github.com/byteport/api/testhelpers"
)

// setupTestDB returns an in-memory SQLite-backed test database for fast unit tests.
func setupTestDB(t *testing.T) *testhelpers.TestDB {
	return testhelpers.SetupSQLiteTestDB(t)
}
