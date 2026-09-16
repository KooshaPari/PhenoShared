package lib

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"log"
	"net/http"
	"nvms/models"
	"os"
	"strings"
	"time"

	"aidanwoods.dev/go-paseto"

	"github.com/zalando/go-keyring"
)

const (
	keyringUser       = "BytePortUser"
	serviceKeyService = "NVMService"
)

var (
	serviceKey paseto.V4SymmetricKey
)

func GetSymmetricKey() (string, error) {
	return keyring.Get(serviceKeyService, keyringUser)
}
func ensureKeyExists(service, user string) error {
	key := os.Getenv("SERVICE_KEY")
	if key == "" {
		return nil // Key already exists
	}

	// Generate and store a new key if not present
	newKey := GenerateSymmetricKey()
	err := os.Setenv("SERVICE_KEY", newKey)
	if err != nil {
		return err
	}
	return nil
}

func InitAuthSystem() error {
	err := ensureKeyExists(serviceKeyService, keyringUser)
	if err != nil {
		return fmt.Errorf("failed to initialize token key: %w", err)
	}

	// Initialize service key
	err = ensureKeyExists(serviceKeyService, keyringUser)
	if err != nil {
		return fmt.Errorf("failed to initialize secrets key: %w", err)
	}

	log.Println("Auth system initialized with separate keys for tokens and secrets.")
	return nil

}
func GenerateSymmetricKey() string {
	key := paseto.NewV4SymmetricKey()
	return key.ExportHex()
}

func GenerateNVMSToken(project models.Project) (string, error) {
	token := paseto.NewToken()
	token.SetAudience(serviceKeyService)
	token.SetExpiration(time.Now().Add(time.Minute * 10))
	token.SetSubject("deployment")
	token.SetIssuer("BytePort")
	token.SetIssuedAt(time.Now())
	token.SetNotBefore(time.Now())
	token.SetString("user-id", project.User.UUID)
	token.SetString("project-id", project.UUID)
	keyHex, err := GetSymmetricKey()
	if err != nil {
		log.Fatal(err)
	}
	key, err := paseto.V4SymmetricKeyFromHex(keyHex)
	if err != nil {
		return "", err
	}

	encryptedToken := token.V4Encrypt(key, nil)

	return encryptedToken, nil
}

func ValidateServiceToken(encryptedToken string) (bool, *paseto.Token, error) {

	keyHex, err := GetSymmetricKey()
	if err != nil {
		return false, nil, err
	}

	key, err := paseto.V4SymmetricKeyFromHex(keyHex)
	if err != nil {
		return false, nil, err
	}

	parser := paseto.NewParser()
	parser.AddRule(paseto.ForAudience(serviceKeyService))
	parser.AddRule(paseto.NotExpired())

	token, err := parser.ParseV4Local(key, encryptedToken, nil)
	if err != nil {
		return false, nil, err
	}

	return true, token, nil
}
func AuthMiddleware(w http.ResponseWriter, r *http.Request) error {
	// Get key from environment/config during initialization
	keyHex := os.Getenv("SERVICE_KEY")
	if keyHex == "" {
		http.Error(w, "Server configuration error", http.StatusInternalServerError)
		return fmt.Errorf("failed to get service key")
	}

	key, err := paseto.V4SymmetricKeyFromHex(keyHex)
	if err != nil {
		http.Error(w, "Server configuration error", http.StatusInternalServerError)
		return err // Don't panic, return error response instead
	}
	serviceKey = key

	// Validate PASETO token
	authHeader, err := r.Cookie("Authorization")
	if err != nil {
		http.Error(w, "Unauthorized - No auth cookie found", http.StatusUnauthorized)
		return http.ErrBodyNotAllowed
	}

	authToken := authHeader.Value
	if authToken == "" {
		http.Error(w, "Unauthorized - Empty auth token", http.StatusUnauthorized)
		return err
	}

	tokenString := strings.TrimPrefix(authToken, "Bearer ")
	parser := paseto.NewParser()

	token, err := parser.ParseV4Local(serviceKey, tokenString, nil)
	if err != nil {
		http.Error(w, "Unauthorized - Invalid token "+err.Error(), http.StatusUnauthorized)
		return err
	}

	// Extract claims with error checking
	projectID, err := token.GetString("project-id")
	if err != nil {
		http.Error(w, "Invalid token claims", http.StatusBadRequest)
		return err
	}

	userID, err := token.GetString("user-id")
	if err != nil {
		http.Error(w, "Invalid token claims", http.StatusBadRequest)
		return err
	}

	fmt.Printf("Successfully authenticated user %s for project %s\n", userID, projectID)
	w.WriteHeader(http.StatusOK)
	return nil
}
func EncryptSecret(secret string) (string, error) {
	key, err := GetDecodedEncryptionKey()
	if err != nil {
		log.Fatal(err)
	}
	// Validate the key length
	if len(key) != 16 && len(key) != 24 && len(key) != 32 {
		return "", fmt.Errorf("invalid key length: must be 16, 24, or 32 bytes")
	}

	// Create a new AES cipher block
	block, err := aes.NewCipher([]byte(key))
	if err != nil {
		return "", fmt.Errorf("failed to create cipher: %v", err)
	}

	// Generate a random IV
	iv := make([]byte, aes.BlockSize)
	if _, err := rand.Read(iv); err != nil {
		return "", fmt.Errorf("failed to generate IV: %v", err)
	}

	// Encrypt the secret using CFB
	cipherText := make([]byte, len(secret))
	stream := cipher.NewCFBEncrypter(block, iv)
	stream.XORKeyStream(cipherText, []byte(secret))

	// Prepend the IV to the ciphertext and encode
	finalCipherText := append(iv, cipherText...)
	return base64.StdEncoding.EncodeToString(finalCipherText), nil
}

func DecryptSecret(cipherText string) (string, error) {
	// Validate the key length
	key, err := GetDecodedEncryptionKey()
	if err != nil {
		log.Fatal(err)
	}
	if len(key) != 16 && len(key) != 24 && len(key) != 32 {
		return "", fmt.Errorf("invalid key length: must be 16, 24, or 32 bytes")
	}

	// Decode the base64-encoded ciphertext
	data, err := base64.StdEncoding.DecodeString(cipherText)
	if err != nil {
		return "", fmt.Errorf("failed to decode base64: %v", err)
	}

	// Separate the IV and the actual ciphertext
	if len(data) < aes.BlockSize {
		return "", fmt.Errorf("ciphertext too short")
	}
	iv := data[:aes.BlockSize]
	cipherTextData := data[aes.BlockSize:]

	// Create a new AES cipher block
	block, err := aes.NewCipher([]byte(key))
	if err != nil {
		return "", fmt.Errorf("failed to create cipher: %v", err)
	}

	// Decrypt the ciphertext using CFB
	plainText := make([]byte, len(cipherTextData))
	stream := cipher.NewCFBDecrypter(block, iv)
	stream.XORKeyStream(plainText, cipherTextData)

	return string(plainText), nil
}
func GetDecodedEncryptionKey() ([]byte, error) {
	encryptionKey := os.Getenv("ENCRYPTION_KEY")
	if encryptionKey == "" {
		return nil, fmt.Errorf("encryption key is not set")
	}

	// Trim whitespace from the environment variable
	trimmedKey := strings.TrimSpace(encryptionKey)

	// Decode the Base64 key
	decodedKey, err := base64.StdEncoding.DecodeString(trimmedKey)
	if err != nil {
		return nil, fmt.Errorf("failed to decode encryption key: %v", err)
	}

	// Validate key length (AES requires 16, 24, or 32 bytes)
	keyLength := len(decodedKey)
	if keyLength != 16 && keyLength != 24 && keyLength != 32 {
		return nil, fmt.Errorf("invalid key length: %d bytes (must be 16, 24, or 32)", keyLength)
	}

	return decodedKey, nil
}
