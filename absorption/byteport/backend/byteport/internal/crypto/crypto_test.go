package crypto

import (
	"byteport/lib"
	"encoding/base64"
	"strings"
	"testing"
	"time"

	"aidanwoods.dev/go-paseto"
)

// TestPasetoTokenGenerateAndValidate verifies that a PASETO v4 local token
// can be created, encrypted, and decrypted with matching claims.
func TestPasetoTokenGenerateAndValidate(t *testing.T) {
	key := paseto.NewV4SymmetricKey()

	token := paseto.NewToken()
	token.SetAudience("test@example.com")
	token.SetExpiration(time.Now().Add(time.Hour))
	token.SetSubject("session")
	token.SetIssuer("BytePort")
	token.SetIssuedAt(time.Now())
	token.SetNotBefore(time.Now())
	token.SetString("user-id", "test-user-uuid-1234")

	encrypted := token.V4Encrypt(key, nil)
	if encrypted == "" {
		t.Fatal("V4Encrypt returned empty string")
	}

	// Decrypt and verify all claims
	parser := paseto.NewParser()
	decrypted, err := parser.ParseV4Local(key, encrypted, nil)
	if err != nil {
		t.Fatalf("ParseV4Local returned error: %v", err)
	}

	audience, err := decrypted.GetAudience()
	if err != nil {
		t.Fatalf("GetAudience returned error: %v", err)
	}
	if audience != "test@example.com" {
		t.Errorf("audience = %q, want %q", audience, "test@example.com")
	}

	subject, err := decrypted.GetSubject()
	if err != nil {
		t.Fatalf("GetSubject returned error: %v", err)
	}
	if subject != "session" {
		t.Errorf("subject = %q, want %q", subject, "session")
	}

	issuer, err := decrypted.GetIssuer()
	if err != nil {
		t.Fatalf("GetIssuer returned error: %v", err)
	}
	if issuer != "BytePort" {
		t.Errorf("issuer = %q, want %q", issuer, "BytePort")
	}

	userID, err := decrypted.GetString("user-id")
	if err != nil {
		t.Fatalf("GetString(user-id) returned error: %v", err)
	}
	if userID != "test-user-uuid-1234" {
		t.Errorf("user-id = %q, want %q", userID, "test-user-uuid-1234")
	}
}

// TestPasetoTokenDifferentKeysFails verifies that a token encrypted with one
// key cannot be decrypted with a different key.
func TestPasetoTokenDifferentKeysFails(t *testing.T) {
	keyA := paseto.NewV4SymmetricKey()
	keyB := paseto.NewV4SymmetricKey()

	token := paseto.NewToken()
	token.SetAudience("test@example.com")
	token.SetExpiration(time.Now().Add(time.Hour))
	token.SetString("user-id", "user-1")

	encrypted := token.V4Encrypt(keyA, nil)

	parser := paseto.NewParser()
	_, err := parser.ParseV4Local(keyB, encrypted, nil)
	if err == nil {
		t.Error("ParseV4Local should fail when using wrong decryption key")
	}
}

// TestPasetoTokenEmptyClaimsRoundTrip verifies that a token with no custom
// claims round-trips correctly.
func TestPasetoTokenEmptyClaimsRoundTrip(t *testing.T) {
	key := paseto.NewV4SymmetricKey()

	token := paseto.NewToken()
	token.SetExpiration(time.Now().Add(time.Hour))

	encrypted := token.V4Encrypt(key, nil)

	parser := paseto.NewParser()
	decrypted, err := parser.ParseV4Local(key, encrypted, nil)
	if err != nil {
		t.Fatalf("ParseV4Local returned error: %v", err)
	}

	// user-id should not exist
	_, err = decrypted.GetString("user-id")
	if err == nil {
		t.Error("GetString(user-id) should fail when claim is absent")
	}
}

// TestAESEncryptionRoundtrip verifies that EncryptSecret followed by
// DecryptSecret returns the original plaintext.
func TestAESEncryptionRoundtrip(t *testing.T) {
	key, err := lib.GenerateEncryptionKey()
	if err != nil {
		t.Fatalf("GenerateEncryptionKey returned error: %v", err)
	}
	t.Setenv("ENCRYPTION_KEY", key)

	secrets := []string{
		"short",
		"AWS_SECRET_WITH_SPECIAL_CHARS_!@#$%^&*()",
		`{"json": "data", "nested": {"deep": true}}`,
		"",
		strings.Repeat("x", 512),
	}

	for _, secret := range secrets {
		encrypted, err := lib.EncryptSecret(secret)
		if err != nil {
			t.Errorf("EncryptSecret(%q) returned error: %v", truncate(secret, 30), err)
			continue
		}

		if encrypted == secret && secret != "" {
			t.Error("encrypted text should differ from plaintext")
		}

		// Verify the payload is valid base64 after the version prefix.
		payload := strings.TrimPrefix(encrypted, "v2:gcm:")
		if payload == encrypted {
			t.Error("EncryptSecret output is missing the GCM version prefix")
		}
		if _, b64Err := base64.StdEncoding.DecodeString(payload); b64Err != nil {
			t.Errorf("EncryptSecret produced invalid base64 payload: %v", b64Err)
			continue
		}

		decrypted, err := lib.DecryptSecret(encrypted)
		if err != nil {
			t.Errorf("DecryptSecret returned error: %v", err)
			continue
		}

		if decrypted != secret {
			t.Errorf("roundtrip mismatch for %q: got %q", truncate(secret, 30), truncate(decrypted, 30))
		}
	}
}

// TestAESDecryptionInvalidData verifies that DecryptSecret returns an error
// for various forms of invalid ciphertext.
func TestAESDecryptionInvalidData(t *testing.T) {
	key, err := lib.GenerateEncryptionKey()
	if err != nil {
		t.Fatalf("GenerateEncryptionKey returned error: %v", err)
	}
	t.Setenv("ENCRYPTION_KEY", key)

	tests := []struct {
		name       string
		ciphertext string
		wantErr    string // substring expected in error message
	}{
		{"invalid base64", "not-valid-base64!!!", ""},
		{"empty string", "", ""},
		{"ciphertext too short", base64.StdEncoding.EncodeToString([]byte("ab")), "too short"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := lib.DecryptSecret(tt.ciphertext)
			if err == nil {
				t.Error("DecryptSecret should return error for invalid ciphertext")
			}
			if tt.wantErr != "" && !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("error = %q, want to contain %q", err.Error(), tt.wantErr)
			}
		})
	}
}

// TestAESDecryptionTamperedCiphertext verifies that modifying ciphertext
// produces garbage (or an error) rather than the original plaintext.
func TestAESDecryptedTamperedCiphertext(t *testing.T) {
	key, err := lib.GenerateEncryptionKey()
	if err != nil {
		t.Fatalf("GenerateEncryptionKey returned error: %v", err)
	}
	t.Setenv("ENCRYPTION_KEY", key)

	original := "super-secret-value"
	encrypted, err := lib.EncryptSecret(original)
	if err != nil {
		t.Fatalf("EncryptSecret returned error: %v", err)
	}

	// Tamper with the ciphertext by flipping one character. The replacement must
	// actually differ from the byte already there, otherwise the "tampered" input
	// is identical to the original and the assertion below fails spuriously.
	tamperedBytes := []byte(encrypted)
	if len(tamperedBytes) <= 10 {
		t.Fatalf("ciphertext too short to tamper with: %d bytes", len(tamperedBytes))
	}
	replacement := byte('A')
	if tamperedBytes[10] == replacement {
		replacement = 'B'
	}
	tamperedBytes[10] = replacement
	tampered := string(tamperedBytes)

	decrypted, err := lib.DecryptSecret(tampered)
	if err != nil {
		// Error is acceptable — tampered data may fail base64 or decryption
		return
	}
	if decrypted == original {
		t.Error("tampered ciphertext should not decrypt to original plaintext")
	}
}

// TestPasetoTokenExpirationDetection verifies that a token with an expiration
// time in the past is rejected when the NotExpired parser rule is applied.
func TestPasetoTokenExpirationDetection(t *testing.T) {
	key := paseto.NewV4SymmetricKey()

	// Create a token that expired 1 hour ago
	token := paseto.NewToken()
	token.SetAudience("test@example.com")
	token.SetExpiration(time.Now().Add(-time.Hour))
	token.SetSubject("session")
	token.SetIssuer("BytePort")
	token.SetIssuedAt(time.Now().Add(-2 * time.Hour))
	token.SetNotBefore(time.Now().Add(-2 * time.Hour))
	token.SetString("user-id", "expired-user-uuid")

	encrypted := token.V4Encrypt(key, nil)

	// Parse with expiration check enabled
	parser := paseto.NewParser()
	parser.AddRule(paseto.NotExpired())

	_, err := parser.ParseV4Local(key, encrypted, nil)
	if err == nil {
		t.Error("ParseV4Local with NotExpired rule should reject expired token")
	}
}

// TestPasetoTokenNotYetValid verifies that the NotExpired parser rule
// does NOT enforce the nbf (not-before) claim — only expiration is checked.
// This documents current go-paseto behavior.
func TestPasetoTokenNotYetValid(t *testing.T) {
	key := paseto.NewV4SymmetricKey()

	token := paseto.NewToken()
	token.SetExpiration(time.Now().Add(2 * time.Hour))
	token.SetNotBefore(time.Now().Add(time.Hour)) // valid starting 1 hour from now
	token.SetString("user-id", "future-user-uuid")

	encrypted := token.V4Encrypt(key, nil)

	parser := paseto.NewParser()
	parser.AddRule(paseto.NotExpired())

	_, err := parser.ParseV4Local(key, encrypted, nil)
	// NotExpired only checks exp, not nbf — so this succeeds.
	if err != nil {
		t.Errorf("ParseV4Local with NotExpired should NOT reject future-nbf token, got: %v", err)
	}
}

// TestGenerateEncryptionKeyUniqueness verifies that consecutive key
// generations produce different keys.
func TestGenerateEncryptionKeyUniqueness(t *testing.T) {
	key1, err := lib.GenerateEncryptionKey()
	if err != nil {
		t.Fatalf("GenerateEncryptionKey returned error: %v", err)
	}
	key2, err := lib.GenerateEncryptionKey()
	if err != nil {
		t.Fatalf("GenerateEncryptionKey returned error: %v", err)
	}
	if key1 == key2 {
		t.Error("GenerateEncryptionKey produced identical keys on consecutive calls")
	}

	// Both should be valid 32-byte base64 keys
	for _, k := range []string{key1, key2} {
		decoded, err := base64.StdEncoding.DecodeString(k)
		if err != nil {
			t.Errorf("key is not valid base64: %v", err)
		}
		if len(decoded) != 32 {
			t.Errorf("key length = %d, want 32", len(decoded))
		}
	}
}

// TestPasswordHashRoundtrip verifies that a password can be hashed and
// validated correctly using argon2id.
func TestPasswordHashRoundtrip(t *testing.T) {
	passwords := []string{"simple", "complex!@#$%^&*()", "", strings.Repeat("a", 1000)}

	for _, pw := range passwords {
		hash, err := lib.EncryptPass(pw)
		if err != nil {
			t.Errorf("EncryptPass(%q) returned error: %v", truncate(pw, 20), err)
			continue
		}
		if hash == "" {
			t.Errorf("EncryptPass(%q) returned empty string", truncate(pw, 20))
			continue
		}
		if !strings.HasPrefix(hash, "$argon2id$") {
			t.Errorf("hash does not have expected prefix: %s", truncate(hash, 40))
			continue
		}
		ok, err := lib.ValidatePass(pw, hash)
		if err != nil {
			t.Errorf("ValidatePass returned error for correct password %q: %v", truncate(pw, 20), err)
		} else if !ok {
			t.Errorf("ValidatePass returned false for correct password %q", truncate(pw, 20))
		}
		ok, err = lib.ValidatePass(pw+"wrong", hash)
		if err != nil {
			t.Errorf("ValidatePass returned error for incorrect password %q: %v", truncate(pw, 20), err)
		} else if ok {
			t.Errorf("ValidatePass returned true for incorrect password for %q", truncate(pw, 20))
		}
	}
}

// truncate shortens s to maxLen, appending "..." if truncated.
func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
