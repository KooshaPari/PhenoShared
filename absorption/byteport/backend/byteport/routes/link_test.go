package routes

import (
	"encoding/base64"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"byteport/lib"
	"byteport/models"

	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// legacyLinkBody is the POST /link payload the SvelteKit frontend shipped while
// the casing bug was live. It sends the credential as camelCase `apiKey`
// although models.AIProvider tags the field `api_key`, and keys the providers
// map `openAI` although the handler looks up `openai`. Go matched neither, so
// ValidateLink handed an EMPTY string to ValidateOpenAICredentials and every
// first-run setup failed with "Failed to validate OAI credentials"; the correct
// key was never persisted either.
const legacyLinkBody = `{
  "awsCreds": {
    "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
    "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  },
  "llmConfig": {
    "provider": "openAI",
    "providers": {
      "openAI": { "modal": "gpt-4o", "apiKey": "sk-legacy-camelcase-key" }
    }
  },
  "portfolio": {
    "rootEndpoint": "https://portfolio.example.com",
    "apiKey": "portfolio-key"
  }
}`

// canonicalLinkBody is the same payload written with the canonical spellings the
// backend emits (`api_key`, `openai`). Both spellings must resolve to the same
// credential, in both directions of the drift.
const canonicalLinkBody = `{
  "awsCreds": {
    "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
    "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  },
  "llmConfig": {
    "provider": "openai",
    "providers": {
      "openai": { "modal": "gpt-4o", "api_key": "sk-canonical-key" }
    }
  },
  "portfolio": {
    "rootEndpoint": "https://portfolio.example.com",
    "apiKey": "portfolio-key"
  }
}`

const testEncryptionKey = "0123456789abcdef0123456789abcdef" // 32 bytes, AES-256

// linkTestDBSeq hands every subtest its own in-memory database; sharing one DSN
// would make the second subtest collide with the first one's seeded user.
var linkTestDBSeq int64

// newLinkTestDB swaps models.DB for an in-memory SQLite database holding the
// users table and restores the previous value on cleanup.
func newLinkTestDB(t *testing.T) *gorm.DB {
	t.Helper()

	dsn := fmt.Sprintf("file:linktest%d?mode=memory&cache=shared", atomic.AddInt64(&linkTestDBSeq, 1))
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

// stubValidators replaces the three outbound credential validators with stubs
// and reports the API key ValidateLink passed to the OpenAI validator.
func stubValidators(t *testing.T) *string {
	t.Helper()

	gotOpenAIKey := new(string)
	prevAWS, prevOAI, prevPortfolio := lib.ValidateAWSCredentials, lib.ValidateOpenAICredentials, lib.ValidatePortfolioAPI
	t.Cleanup(func() {
		lib.ValidateAWSCredentials = prevAWS
		lib.ValidateOpenAICredentials = prevOAI
		lib.ValidatePortfolioAPI = prevPortfolio
	})

	lib.ValidateAWSCredentials = func(accessKey, secretKey string) error { return nil }
	lib.ValidateOpenAICredentials = func(apiToken string) error {
		*gotOpenAIKey = apiToken
		return nil
	}
	lib.ValidatePortfolioAPI = func(rootEndpoint, apiKey string) error { return nil }
	return gotOpenAIKey
}

// assertStoredOpenAIKey verifies the OpenAI credential was persisted
// encrypted under the canonical provider key and decrypts to want. Split out
// of TestValidateLinkCredentialsSurviveFieldCasing for cognitive simplicity.
func assertStoredOpenAIKey(t *testing.T, db *gorm.DB, uuid, want string) {
	t.Helper()
	var stored models.User
	if err := db.Where("uuid = ?", uuid).First(&stored).Error; err != nil {
		t.Fatalf("reload user: %v", err)
	}
	provider, ok := stored.LLMConfig.Providers["openai"]
	if !ok {
		t.Fatalf("stored providers = %v, want a canonical \"openai\" entry", stored.LLMConfig.Providers)
	}
	if provider.APIKey == "" {
		t.Fatal("stored api_key is empty: the credential was never persisted")
	}
	plain, err := lib.DecryptSecret(provider.APIKey)
	if err != nil {
		t.Fatalf("decrypt stored key: %v", err)
	}
	if plain != want {
		t.Fatalf("stored key decrypts to %q, want %q", plain, want)
	}
}

// TestValidateLinkCredentialsSurviveFieldCasing is the regression test for the
// api_key casing bug: the frontend sent `apiKey`/`openAI`, the backend expected
// `api_key`/`openai`, so the OpenAI credential silently validated as empty and
// was never stored.
//
// The outbound validators are stubbed (see lib.ValidateOpenAICredentials); a
// real run is covered by the server smoke check, not here.
func TestValidateLinkCredentialsSurviveFieldCasing(t *testing.T) {
	gin.SetMode(gin.TestMode)
	t.Setenv("ENCRYPTION_KEY", base64.StdEncoding.EncodeToString([]byte(testEncryptionKey)))

	cases := []struct {
		name string
		body string
		key  string
	}{
		{"legacy camelCase apiKey and openAI key", legacyLinkBody, "sk-legacy-camelcase-key"},
		{"canonical api_key and openai key", canonicalLinkBody, "sk-canonical-key"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			db := newLinkTestDB(t)
			gotKey := stubValidators(t)

			user := models.User{
				UUID:     "user-casing-1",
				Name:     "Casing",
				Email:    "casing@example.com",
				Password: "hash",
			}
			if err := db.Create(&user).Error; err != nil {
				t.Fatalf("seed user: %v", err)
			}

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest(http.MethodPost, "/link", strings.NewReader(tc.body))
			c.Request.Header.Set("Content-Type", "application/json")
			c.Set("user", user)

			ValidateLink(c)

			if w.Code != http.StatusOK {
				t.Fatalf("status = %d, want %d (body %s)", w.Code, http.StatusOK, w.Body.String())
			}
			if *gotKey != tc.key {
				t.Fatalf("ValidateOpenAICredentials received %q, want %q: the credential was dropped during decoding", *gotKey, tc.key)
			}

			// The credential must also be persisted (encrypted) under the
			// canonical provider key, which is what the old UI silently failed
			// to do.
			assertStoredOpenAIKey(t, db, user.UUID, tc.key)
		})
	}
}
