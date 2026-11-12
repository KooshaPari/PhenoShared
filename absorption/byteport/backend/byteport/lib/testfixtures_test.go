package lib

import (
	"encoding/base64"
	"fmt"
	"sync/atomic"
	"testing"

	"byteport/models"

	"github.com/glebarez/sqlite"
	"github.com/google/uuid"
	"github.com/zalando/go-keyring"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// libTestDBSeq hands every test its own in-memory database; sharing one DSN
// across tests makes them collide because the connection pool sees both.
var libTestDBSeq int64

// newLibTestDB swaps models.DB for a fresh in-memory SQLite holding every
// table the lib tests touch, and restores the previous handle on cleanup.
func newLibTestDB(t *testing.T) *gorm.DB {
	t.Helper()

	dsn := fmt.Sprintf("file:libtest%d?mode=memory&cache=shared", atomic.AddInt64(&libTestDBSeq, 1))
	db, err := gorm.Open(sqlite.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		t.Fatalf("open sqlite: %v", err)
	}
	if err := db.AutoMigrate(&models.User{}, &models.Project{}, &models.Instance{}, &models.GitSecret{}); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	prev := models.DB
	models.DB = db
	t.Cleanup(func() { models.DB = prev })
	return db
}

// resetMockKeyring installs a fresh in-memory keyring backend. zalando/go-keyring's
// mock backend is a package-global singleton, so tests must reset it to avoid
// bleed-through between the empty (must-create) and populated (must-reuse)
// paths that InitAuthSystem and the token helpers exercise.
func resetMockKeyring(t *testing.T) {
	t.Helper()
	keyring.MockInit()
	t.Cleanup(func() { keyring.MockInit() })
}

// testEncryptionKeyBytes returns a deterministic 32-byte (AES-256) key. It is
// built programmatically rather than written as a literal so that secret
// scanners do not flag the fixture as a committed credential.
func testEncryptionKeyBytes() []byte {
	k := make([]byte, 32)
	for i := range k {
		k[i] = byte(i)
	}
	return k
}

// seedEncryptionKey plants ENCRYPTION_KEY so DecryptSecret/EncryptSecret do
// not log.Fatal. The env var carries the base64-encoded 32-byte key.
func seedEncryptionKey(t *testing.T) {
	t.Helper()
	t.Setenv("ENCRYPTION_KEY", base64.StdEncoding.EncodeToString(testEncryptionKeyBytes()))
}

// mustEncrypt encrypts s with the seeded key and fails the test on error;
// small convenience so happy-path tests can seed encrypted fixtures.
func mustEncrypt(t *testing.T, s string) string {
	t.Helper()
	out, err := EncryptSecret(s)
	if err != nil {
		t.Fatalf("EncryptSecret(%q): %v", s, err)
	}
	return out
}

// seedUserWithToken prepares the keyring and auth system, then returns a fresh
// DB holding one persisted user plus a valid token for it. Every test that needs
// "an authenticated identity backed by a real row" starts here, so the setup
// lives in one place.
func seedUserWithToken(t *testing.T, email, name, password string) (*gorm.DB, models.User, string) {
	t.Helper()

	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	db := newLibTestDB(t)

	user := models.User{
		UUID:     uuid.NewString(),
		Email:    email,
		Name:     name,
		Password: password,
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	tok, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	return db, user, tok
}
