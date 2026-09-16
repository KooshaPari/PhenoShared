package testhelpers

import (
	"net/url"
	"testing"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// TestDB wraps a GORM test database and optional backing container metadata.
type TestDB struct {
	DB        *gorm.DB
	Container any
}

// SetupSQLiteTestDB creates an isolated in-memory SQLite database for unit tests.
func SetupSQLiteTestDB(t *testing.T) *TestDB {
	t.Helper()

	dbName := url.QueryEscape(t.Name())
	db, err := gorm.Open(sqlite.Open("file:"+dbName+"?mode=memory&cache=shared"), &gorm.Config{})
	if err != nil {
		t.Fatalf("failed to open sqlite test database: %v", err)
	}

	t.Cleanup(func() {
		sqlDB, err := db.DB()
		if err == nil {
			_ = sqlDB.Close()
		}
	})

	return &TestDB{DB: db}
}

// SetupTestDB is the integration-test entrypoint. It currently uses SQLite so
// repository tests can run without a Docker/Postgres dependency.
func SetupTestDB(t *testing.T) *TestDB {
	t.Helper()
	return SetupSQLiteTestDB(t)
}

// MigrateModels applies the supplied GORM models to the test database.
func (db *TestDB) MigrateModels(models ...any) error {
	return db.DB.AutoMigrate(models...)
}
