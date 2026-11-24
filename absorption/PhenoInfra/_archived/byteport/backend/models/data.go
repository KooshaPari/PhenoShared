package models

import (
	"fmt"
	"log"
	"os"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

func ConnectDatabase() {
	// Get database URL from environment variable
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		// Default for local development - use same PostgreSQL as Zen MCP server
		dsn = "host=localhost user=zen password=zen dbname=zen_mcp port=5432 sslmode=disable"
		log.Println("DATABASE_URL not set, using Zen PostgreSQL connection")
	}

	// Configure GORM logger
	logLevel := logger.Info
	if os.Getenv("GIN_MODE") == "release" {
		logLevel = logger.Warn
	}

	// Open database connection with PostgreSQL driver
	database, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logLevel),
		NowFunc: func() time.Time {
			return time.Now().UTC()
		},
		// Disable foreign key constraints for SQLite compatibility during migration
		// Re-enable in production
		DisableForeignKeyConstraintWhenMigrating: false,
	})

	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Configure connection pool
	sqlDB, err := database.DB()
	if err != nil {
		log.Fatalf("Failed to get database instance: %v", err)
	}

	// Set connection pool settings
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)

	// Verify connection
	if err := sqlDB.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}

	fmt.Println("Successfully connected to PostgreSQL database")

	// AutoMigrate models in the correct order
	// Note: For production, use migration files instead
	err = database.AutoMigrate(
		&User{},
		&Repository{},
		&Project{},
		&Instance{},
		&AWSResource{},
		&Deployment{},
		&Host{},
	)
	if err != nil {
		log.Fatalf("Failed to auto-migrate database: %v", err)
	}

	fmt.Println("Database migration completed successfully")

	DB = database
}
