package routes

import (
	"errors"
	"fmt"

	"byteport/lib"
	"byteport/models"
)

// platformSecretField labels one of the four user-owned secret fields that
// the platform-secret helpers (decrypt/encrypt) operate on. The labels are
// the same strings that previously appeared in the per-field
// `respondInternalError` messages inside UpdateLink and ValidateLink, so
// moving the work into this file does not change the wire-visible response
// text for either handler.
type platformSecretField string

const (
	fieldAWSAccessKeyID     platformSecretField = "AWS Access Key ID"
	fieldAWSSecretAccessKey platformSecretField = "AWS Secret Access Key"
	fieldPortfolioURL       platformSecretField = "Portfolio Root Endpoint"
	fieldPortfolioAPIKey    platformSecretField = "Portfolio API Key"
)

// platformSecretError is returned by decryptUserPlatformSecrets and
// encryptUserPlatformSecrets when one of the four steps fails. Callers map
// it back to a 500 envelope via platformSecretErrorMessage; the public
// Error() string is already in the user-facing "Failed to <verb> <field>"
// shape so respondInternalError(c, err.Error()) produces the same JSON
// the handlers emitted before the refactor.
type platformSecretError struct {
	Field platformSecretField
	Op    string // "decrypt" or "encrypt"
	Err   error
}

func (e *platformSecretError) Error() string {
	return fmt.Sprintf("Failed to %s %s: %v", e.Op, e.Field, e.Err)
}

func (e *platformSecretError) Unwrap() error { return e.Err }

// platformSecretErrorMessage renders the response envelope title for a
// platformSecretError. It returns the user-facing message only (no wrapped
// error) so the JSON shape stays a single string under "error".
func platformSecretErrorMessage(err error) string {
	var pse *platformSecretError
	if errors.As(err, &pse) {
		return fmt.Sprintf("Failed to %s %s", pse.Op, pse.Field)
	}
	// Fallback for unexpected (non platformSecretError) errors so the handler
	// still has a sensible envelope title.
	return "Failed to process platform secrets"
}

// decryptUserPlatformSecrets decrypts the four user-owned platform-secret
// fields (AWS access + secret key, Portfolio URL + API key) and returns them
// in plaintext. UpdateLink previously ran this 4-stage DecryptSecret ladder
// inline with four `respondInternalError("Failed to decrypt <X>")` calls;
// ValidateLink ran the same ladder for the symmetric decrypt step. Both now
// share this helper so adding or removing a field only touches one file.
//
// The function does not touch the LLM/OpenAI credential — that has
// provider-specific lookup semantics (ProviderEntry vs ProviderKey with
// fallback) that differ between the two call sites, so it stays inline at
// each handler.
func decryptUserPlatformSecrets(user models.User) (models.AwsCreds, models.Portfolio, error) {
	var (
		aws       models.AwsCreds
		portfolio models.Portfolio
		err       error
	)
	if aws.AccessKeyID, err = lib.DecryptSecret(user.AwsCreds.AccessKeyID); err != nil {
		return aws, portfolio, &platformSecretError{Field: fieldAWSAccessKeyID, Op: "decrypt", Err: err}
	}
	if aws.SecretAccessKey, err = lib.DecryptSecret(user.AwsCreds.SecretAccessKey); err != nil {
		return aws, portfolio, &platformSecretError{Field: fieldAWSSecretAccessKey, Op: "decrypt", Err: err}
	}
	if portfolio.RootEndpoint, err = lib.DecryptSecret(user.Portfolio.RootEndpoint); err != nil {
		return aws, portfolio, &platformSecretError{Field: fieldPortfolioURL, Op: "decrypt", Err: err}
	}
	if portfolio.APIKey, err = lib.DecryptSecret(user.Portfolio.APIKey); err != nil {
		return aws, portfolio, &platformSecretError{Field: fieldPortfolioAPIKey, Op: "decrypt", Err: err}
	}
	return aws, portfolio, nil
}

// encryptUserPlatformSecrets is the encrypt-side counterpart used by
// ValidateLink after the plaintext credentials have been validated by
// lib.Validate{AWS,OpenAI,Portfolio}. Like its decrypt twin it collapses a
// 4-stage ladder that was previously inlined.
func encryptUserPlatformSecrets(aws models.AwsCreds, portfolio models.Portfolio) (models.AwsCreds, models.Portfolio, error) {
	var (
		encAWS       models.AwsCreds
		encPortfolio models.Portfolio
		err          error
	)
	if encAWS.AccessKeyID, err = lib.EncryptSecret(aws.AccessKeyID); err != nil {
		return encAWS, encPortfolio, &platformSecretError{Field: fieldAWSAccessKeyID, Op: "encrypt", Err: err}
	}
	if encAWS.SecretAccessKey, err = lib.EncryptSecret(aws.SecretAccessKey); err != nil {
		return encAWS, encPortfolio, &platformSecretError{Field: fieldAWSSecretAccessKey, Op: "encrypt", Err: err}
	}
	if encPortfolio.RootEndpoint, err = lib.EncryptSecret(portfolio.RootEndpoint); err != nil {
		return encAWS, encPortfolio, &platformSecretError{Field: fieldPortfolioURL, Op: "encrypt", Err: err}
	}
	if encPortfolio.APIKey, err = lib.EncryptSecret(portfolio.APIKey); err != nil {
		return encAWS, encPortfolio, &platformSecretError{Field: fieldPortfolioAPIKey, Op: "encrypt", Err: err}
	}
	return encAWS, encPortfolio, nil
}
