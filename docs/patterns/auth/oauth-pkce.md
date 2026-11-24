# OAuth 2.0 with PKCE

## Overview

**OAuth 2.0** with **PKCE** (Proof Key for Code Exchange) is the modern standard for secure delegated authorization, especially for public clients (mobile apps, SPAs, CLI tools).

```
┌─────────────────────────────────────────────────────────────────┐
│                     OAuth 2.0 + PKCE FLOW                        │
│                                                                 │
│  ┌─────────────┐                                  ┌─────────────┐│
│  │   Client    │                                  │   Auth      ││
│  │  (Browser)  │                                  │  Server     ││
│  └──────┬──────┘                                  └──────┬─────┘│
│         │                                                 │      │
│         │  1. Generate PKCE params                        │      │
│         │     code_verifier = random(128 bytes)           │      │
│         │     code_challenge = SHA256(code_verifier)      │      │
│         │                                                 │      │
│         │  2. Authorization Request                       │      │
│         │ ──────GET /oauth/authorize?─────────────────────▶│      │
│         │        response_type=code                        │      │
│         │        client_id={client_id}                     │      │
│         │        redirect_uri={callback}                   │      │
│         │        code_challenge={hash}                     │      │
│         │        code_challenge_method=S256                │      │
│         │        scope=read write                          │      │
│         │        state={csrf_token}                        │      │
│         │                                                 │      │
│         │  3. User authenticates                          │      │
│         │     (login page, 2FA, consent)                  │      │
│         │                                                 │      │
│         │  4. Authorization Code                          │      │
│         │ ◀─────Redirect to {callback}?──────────────────│      │
│         │        code={auth_code}                          │      │
│         │        state={csrf_token}                        │      │
│         │                                                 │      │
│         │  5. Token Request                               │      │
│         │ ──────POST /oauth/token─────────────────────────▶│      │
│         │        grant_type=authorization_code             │      │
│         │        code={auth_code}                          │      │
│         │        redirect_uri={callback}                   │      │
│         │        client_id={client_id}                     │      │
│         │        code_verifier={original}   ◄─────────────┘      │
│         │                          (sent in body)                │
│         │                                                 │      │
│         │  6. Access Token + Refresh Token                │      │
│         │ ◀─────{access_token, refresh_token, expires_in}        │
│         │                                                 │      │
│         │  7. API Calls with Access Token                 │      │
│         │ ──────GET /api/resource─────────────────────────▶│      │
│         │        Authorization: Bearer {access_token}      │      │
│         │                                                 │      │
└─────────┴───────────────────────────────────────────────────┴──────┘
```

## Why PKCE?

### Without PKCE (Vulnerable)

```
Attack: Authorization Code Interception
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │────▶│ Browser │────▶│ Attacker│────▶│  App    │
│         │     │ (Malware)│     │  (Proxy) │     │         │
└─────────┘     └─────────┘     └────┬────┘     └─────────┘
                                     │
                                     │ Intercepts callback
                                     │ Gets: code=abc123
                                     │
                                     ▼
                              Attacker exchanges code
                              for access_token!
```

### With PKCE (Protected)

```
Attack: Authorization Code Interception (Fails)
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │────▶│ Browser │────▶│ Attacker│────▶│  App    │
│         │     │ (Malware)│     │  (Proxy) │     │ (has    │
└─────────┘     └─────────┘     └────┬────┘     │ verifier)
                                     │           └─────────┘
                                     │
                                     │ Gets: code=abc123
                                     │ Tries to exchange:
                                     │ POST /token
                                     │   code=abc123
                                     │ ❌ Missing code_verifier!
                                     │
                                     ▼
                              Server rejects:
                              "invalid_grant"
```

**PKCE prevents code interception attacks.** Required for public clients, recommended for all.

## Implementation

### PKCE Parameter Generation

```rust
use sha2::{Sha256, Digest};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use rand::Rng;

pub struct PkcePair {
    pub code_verifier: String,
    pub code_challenge: String,
    pub method: String, // Always "S256"
}

impl PkcePair {
    /// Generate cryptographically secure PKCE parameters
    pub fn generate() -> Self {
        // Generate 128 bytes of randomness (256 hex chars = 128 bytes)
        let code_verifier = Self::generate_code_verifier();
        
        // Compute SHA256 hash
        let code_challenge = Self::compute_challenge(&code_verifier);
        
        Self {
            code_verifier,
            code_challenge,
            method: "S256".to_string(),
        }
    }
    
    fn generate_code_verifier() -> String {
        // RFC 7636: 43-128 characters of [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
        let bytes: Vec<u8> = (0..128)
            .map(|_| rand::thread_rng().gen::<u8>())
            .collect();
        
        URL_SAFE_NO_PAD.encode(&bytes)
    }
    
    fn compute_challenge(verifier: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(verifier.as_bytes());
        let hash = hasher.finalize();
        
        URL_SAFE_NO_PAD.encode(&hash)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn pkce_generation() {
        let pkce = PkcePair::generate();
        
        // Verifier should be 43-128 chars
        assert!(pkce.code_verifier.len() >= 43);
        assert!(pkce.code_verifier.len() <= 128);
        
        // Challenge should be 43 chars (base64 of 32-byte SHA256)
        assert_eq!(pkce.code_challenge.len(), 43);
        
        // Verify challenge computation
        let recomputed = PkcePair::compute_challenge(&pkce.code_verifier);
        assert_eq!(pkce.code_challenge, recomputed);
    }
}
```

### Authorization Endpoint

```rust
pub struct AuthorizationRequest {
    pub response_type: String,        // Must be "code"
    pub client_id: String,
    pub redirect_uri: Url,
    pub scope: Vec<String>,
    pub state: String,                // CSRF protection
    pub code_challenge: String,
    pub code_challenge_method: String, // Must be "S256"
}

impl AuthorizationRequest {
    pub fn validate(&self, client: &OAuthClient) -> Result<(), AuthError> {
        // Validate response_type
        if self.response_type != "code" {
            return Err(AuthError::unsupported_response_type());
        }
        
        // Validate client_id
        if self.client_id != client.id {
            return Err(AuthError::invalid_client());
        }
        
        // Validate redirect_uri
        if !client.redirect_uris.contains(&self.redirect_uri) {
            return Err(AuthError::invalid_redirect_uri());
        }
        
        // Validate code_challenge_method
        if self.code_challenge_method != "S256" {
            // RFC 7636: Servers MUST support S256
            // Optional: Support "plain" for legacy, but not recommended
            return Err(AuthError::invalid_request(
                "code_challenge_method must be S256"
            ));
        }
        
        // Validate code_challenge format
        if self.code_challenge.len() != 43 {
            return Err(AuthError::invalid_request(
                "Invalid code_challenge format"
            ));
        }
        
        // Validate scope
        for scope in &self.scope {
            if !client.allowed_scopes.contains(scope) {
                return Err(AuthError::invalid_scope(scope.clone()));
            }
        }
        
        // Validate state presence (not empty for CSRF protection)
        if self.state.is_empty() {
            return Err(AuthError::invalid_request(
                "state parameter required for CSRF protection"
            ));
        }
        
        Ok(())
    }
}
```

### Authorization Server Handler

```rust
pub struct AuthorizationServer {
    client_repo: Arc<dyn ClientRepository>,
    auth_code_repo: Arc<dyn AuthorizationCodeRepository>,
    session_manager: Arc<dyn SessionManager>,
}

impl AuthorizationServer {
    /// Step 1: Handle authorization request
    pub async fn authorize(
        &self,
        request: AuthorizationRequest,
        session: Session,
    ) -> Result<AuthorizationResponse, AuthError> {
        // Load client
        let client = self.client_repo
            .get_by_id(&request.client_id)
            .await?
            .ok_or(AuthError::invalid_client())?;
        
        // Validate request
        request.validate(&client)?;
        
        // Check user authentication
        if !session.is_authenticated() {
            // Redirect to login page with return URL
            return Ok(AuthorizationResponse::login_required(
                self.build_login_url(&request)
            ));
        }
        
        // Check consent (if first time for this client/scope)
        if !self.has_consent(&session.user_id, &client.id, &request.scope).await? {
            return Ok(AuthorizationResponse::consent_required(
                self.build_consent_url(&request)
            ));
        }
        
        // Generate authorization code
        let auth_code = AuthorizationCode {
            code: Self::generate_code(),
            client_id: client.id.clone(),
            user_id: session.user_id.clone(),
            redirect_uri: request.redirect_uri.clone(),
            scope: request.scope.clone(),
            code_challenge: request.code_challenge,
            code_challenge_method: request.code_challenge_method,
            expires_at: Utc::now() + Duration::minutes(10),
            used: false,
        };
        
        // Store code
        self.auth_code_repo.save(&auth_code).await?;
        
        // Return redirect with code
        let redirect_url = format!(
            "{}?code={}&state={}",
            request.redirect_uri,
            auth_code.code,
            request.state
        );
        
        Ok(AuthorizationResponse::redirect(redirect_url))
    }
    
    fn generate_code() -> String {
        // Cryptographically secure random code
        let bytes: Vec<u8> = (0..32)
            .map(|_| rand::thread_rng().gen::<u8>())
            .collect();
        URL_SAFE_NO_PAD.encode(&bytes)
    }
}
```

### Token Endpoint

```rust
pub struct TokenRequest {
    pub grant_type: String,           // Must be "authorization_code"
    pub code: String,
    pub redirect_uri: Url,
    pub client_id: String,
    pub code_verifier: String,        // PKCE verification
}

pub struct TokenResponse {
    pub access_token: String,
    pub token_type: String,           // "Bearer"
    pub expires_in: u64,              // Seconds
    pub refresh_token: String,
    pub scope: Vec<String>,
}

impl AuthorizationServer {
    /// Step 2: Exchange code for tokens
    pub async fn token(
        &self,
        request: TokenRequest,
    ) -> Result<TokenResponse, AuthError> {
        // Validate grant_type
        if request.grant_type != "authorization_code" {
            return Err(AuthError::unsupported_grant_type());
        }
        
        // Load authorization code
        let auth_code = self.auth_code_repo
            .get_by_code(&request.code)
            .await?
            .ok_or(AuthError::invalid_grant())?;
        
        // Verify code hasn't been used (prevent replay attacks)
        if auth_code.used {
            // Security: Revoke all tokens issued with this code
            self.revoke_tokens_for_code(&auth_code.code).await?;
            return Err(AuthError::invalid_grant());
        }
        
        // Verify code hasn't expired
        if auth_code.expires_at < Utc::now() {
            return Err(AuthError::invalid_grant());
        }
        
        // Verify client_id matches
        if auth_code.client_id != request.client_id {
            return Err(AuthError::invalid_client());
        }
        
        // Verify redirect_uri matches authorization request
        if auth_code.redirect_uri != request.redirect_uri {
            return Err(AuthError::invalid_grant());
        }
        
        // PKCE VERIFICATION (Critical!)
        let computed_challenge = Self::compute_code_challenge(&request.code_verifier);
        if computed_challenge != auth_code.code_challenge {
            return Err(AuthError::invalid_grant());
        }
        
        // Mark code as used (prevent replay)
        self.auth_code_repo.mark_used(&auth_code.code).await?;
        
        // Generate tokens
        let access_token = self.generate_access_token(&auth_code).await?;
        let refresh_token = self.generate_refresh_token(&auth_code).await?;
        
        // Store tokens
        self.token_repo.save(&access_token).await?;
        self.token_repo.save(&refresh_token).await?;
        
        Ok(TokenResponse {
            access_token: access_token.token,
            token_type: "Bearer".to_string(),
            expires_in: access_token.expires_in_secs(),
            refresh_token: refresh_token.token,
            scope: auth_code.scope,
        })
    }
    
    fn compute_code_challenge(verifier: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(verifier.as_bytes());
        let hash = hasher.finalize();
        URL_SAFE_NO_PAD.encode(&hash)
    }
}
```

### Client Implementation

```rust
pub struct OAuthClient {
    client_id: String,
    redirect_uri: Url,
    auth_endpoint: Url,
    token_endpoint: Url,
    pkce: Option<PkcePair>,
    state: String,
}

impl OAuthClient {
    pub fn new(client_id: String, redirect_uri: Url) -> Self {
        Self {
            client_id,
            redirect_uri,
            auth_endpoint: Url::parse("https://auth.phenotype.dev/oauth/authorize").unwrap(),
            token_endpoint: Url::parse("https://auth.phenotype.dev/oauth/token").unwrap(),
            pkce: None,
            state: Self::generate_state(),
        }
    }
    
    /// Step 1: Build authorization URL
    pub fn build_auth_url(&mut self, scope: &[&str]) -> Url {
        // Generate PKCE params
        self.pkce = Some(PkcePair::generate());
        let pkce = self.pkce.as_ref().unwrap();
        
        let mut url = self.auth_endpoint.clone();
        url.query_pairs_mut()
            .append_pair("response_type", "code")
            .append_pair("client_id", &self.client_id)
            .append_pair("redirect_uri", self.redirect_uri.as_str())
            .append_pair("code_challenge", &pkce.code_challenge)
            .append_pair("code_challenge_method", "S256")
            .append_pair("state", &self.state);
        
        for s in scope {
            url.query_pairs_mut().append_pair("scope", s);
        }
        
        url
    }
    
    /// Step 2: Exchange code for token
    pub async fn exchange_code(&self, code: &str) -> Result<TokenResponse, ClientError> {
        let pkce = self.pkce.as_ref()
            .ok_or(ClientError::pkce_not_initialized())?;
        
        let client = reqwest::Client::new();
        let response = client
            .post(&self.token_endpoint.to_string())
            .form(&[
                ("grant_type", "authorization_code"),
                ("code", code),
                ("redirect_uri", self.redirect_uri.as_str()),
                ("client_id", &self.client_id),
                ("code_verifier", &pkce.code_verifier),
            ])
            .send()
            .await?;
        
        if !response.status().is_success() {
            let error: OAuthError = response.json().await?;
            return Err(ClientError::oauth_error(error));
        }
        
        let token_response: TokenResponse = response.json().await?;
        Ok(token_response)
    }
    
    fn generate_state() -> String {
        let bytes: Vec<u8> = (0..32)
            .map(|_| rand::thread_rng().gen::<u8>())
            .collect();
        URL_SAFE_NO_PAD.encode(&bytes)
    }
}
```

## Token Refresh

```rust
pub async fn refresh_token(
    &self,
    refresh_token: &str,
) -> Result<TokenResponse, AuthError> {
    // Validate refresh token
    let token = self.token_repo
        .get_refresh_token(refresh_token)
        .await?
        .ok_or(AuthError::invalid_grant())?;
    
    if token.is_revoked() {
        return Err(AuthError::invalid_grant());
    }
    
    if token.is_expired() {
        return Err(AuthError::invalid_grant());
    }
    
    // Generate new access token
    let access_token = self.generate_access_token_from_refresh(&token).await?;
    
    // Optional: Rotate refresh token (security best practice)
    let new_refresh_token = self.generate_refresh_token_from_refresh(&token).await?;
    self.token_repo.revoke(&token.token).await?;
    self.token_repo.save(&new_refresh_token).await?;
    
    Ok(TokenResponse {
        access_token: access_token.token,
        token_type: "Bearer".to_string(),
        expires_in: access_token.expires_in_secs(),
        refresh_token: new_refresh_token.token,
        scope: token.scope,
    })
}
```

## Token Introspection

```rust
pub async fn introspect_token(&self, token: &str) -> Result<IntrospectionResponse, AuthError> {
    let access_token = self.token_repo
        .get_access_token(token)
        .await?;
    
    match access_token {
        Some(token) if !token.is_expired() && !token.is_revoked() => {
            Ok(IntrospectionResponse::active(
                token.user_id,
                token.client_id,
                token.scope,
                token.expires_at,
            ))
        }
        _ => Ok(IntrospectionResponse::inactive()),
    }
}
```

## Security Considerations

### CSRF Protection (State Parameter)

```rust
// Client: Store state in session before redirect
session.insert("oauth_state", state.clone())?;

// After redirect back
let returned_state = query.get("state");
let stored_state: String = session.get("oauth_state")?;

if returned_state != stored_state {
    return Err(AuthError::csrf_detected());
}
```

### Token Storage (Client-Side)

```rust
pub struct SecureTokenStorage;

impl SecureTokenStorage {
    /// Store tokens in secure, httpOnly cookies
    pub fn store_in_cookie(&self, response: &mut HttpResponse, tokens: &TokenResponse) {
        // Access token: short-lived, httpOnly, Secure, SameSite=Strict
        response.add_cookie(
            Cookie::build("access_token", &tokens.access_token)
                .http_only(true)
                .secure(true)
                .same_site(SameSite::Strict)
                .max_age(Duration::seconds(tokens.expires_in as i64))
                .path("/")
                .finish()
        ).unwrap();
        
        // Refresh token: long-lived, httpOnly, Secure, SameSite=Strict
        response.add_cookie(
            Cookie::build("refresh_token", &tokens.refresh_token)
                .http_only(true)
                .secure(true)
                .same_site(SameSite::Strict)
                .max_age(Duration::days(30))
                .path("/oauth/refresh")  // Limited path
                .finish()
        ).unwrap();
    }
    
    /// NEVER store tokens in:
    /// - localStorage (XSS vulnerable)
    /// - memory without encryption (swap risk)
    /// - logs (token exposure)
}
```

### Token Revocation

```rust
pub async fn revoke_token(&self, token: &str, token_type_hint: Option<String>) {
    // Try access token first
    if let Some(access) = self.token_repo.get_access_token(token).await? {
        self.token_repo.revoke_access(&access.token).await?;
        
        // Also revoke associated refresh token
        if let Some(refresh) = self.token_repo.get_refresh_by_access(&access.id).await? {
            self.token_repo.revoke_refresh(&refresh.token).await?;
        }
        
        return Ok(());
    }
    
    // Try refresh token
    if let Some(refresh) = self.token_repo.get_refresh_token(token).await? {
        self.token_repo.revoke_refresh(&refresh.token).await?;
        
        // Also revoke all access tokens issued with this refresh
        self.token_repo.revoke_access_by_refresh(&refresh.id).await?;
    }
    
    Ok(())
}
```

## Error Handling

```rust
#[derive(Debug, Serialize)]
#[serde(tag = "error")]
pub enum OAuthError {
    #[serde(rename = "invalid_request")]
    InvalidRequest { error_description: String },
    
    #[serde(rename = "invalid_client")]
    InvalidClient,
    
    #[serde(rename = "invalid_grant")]
    InvalidGrant,
    
    #[serde(rename = "unauthorized_client")]
    UnauthorizedClient,
    
    #[serde(rename = "unsupported_grant_type")]
    UnsupportedGrantType,
    
    #[serde(rename = "invalid_scope")]
    InvalidScope { scope: String },
    
    #[serde(rename = "server_error")]
    ServerError,
}

impl OAuthError {
    pub fn http_status(&self) -> StatusCode {
        match self {
            Self::InvalidRequest { .. } => StatusCode::BAD_REQUEST,
            Self::InvalidClient => StatusCode::UNAUTHORIZED,
            Self::InvalidGrant => StatusCode::BAD_REQUEST,
            Self::UnauthorizedClient => StatusCode::BAD_REQUEST,
            Self::UnsupportedGrantType => StatusCode::BAD_REQUEST,
            Self::InvalidScope { .. } => StatusCode::BAD_REQUEST,
            Self::ServerError => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}
```

## Testing

```rust
#[tokio::test]
async fn authorization_flow_with_pkce() {
    let server = TestAuthorizationServer::new().await;
    let client = OAuthClient::new(
        "test-client".to_string(),
        Url::parse("http://localhost/callback").unwrap(),
    );
    
    // Step 1: Get authorization URL
    let auth_url = client.build_auth_url(&["read", "write"]);
    
    // Step 2: Simulate user authorization
    let auth_response = server
        .authorize(AuthorizationRequest {
            response_type: "code".to_string(),
            client_id: "test-client".to_string(),
            redirect_uri: Url::parse("http://localhost/callback").unwrap(),
            scope: vec!["read".to_string(), "write".to_string()],
            state: "test-state".to_string(),
            code_challenge: extract_challenge(&auth_url),
            code_challenge_method: "S256".to_string(),
        },
        authenticated_session(),
        )
        .await
        .unwrap();
    
    // Extract code from redirect
    let code = extract_code(&auth_response);
    
    // Step 3: Exchange code for token
    let token_response = server
        .token(TokenRequest {
            grant_type: "authorization_code".to_string(),
            code,
            redirect_uri: Url::parse("http://localhost/callback").unwrap(),
            client_id: "test-client".to_string(),
            code_verifier: extract_verifier(&client),
        })
        .await
        .unwrap();
    
    assert!(!token_response.access_token.is_empty());
    assert!(!token_response.refresh_token.is_empty());
    assert_eq!(token_response.token_type, "Bearer");
}

#[tokio::test]
async fn pkce_verification_fails_with_wrong_verifier() {
    let server = TestAuthorizationServer::new().await;
    
    // Create code with PKCE params
    let pkce = PkcePair::generate();
    let code = server.create_auth_code(&pkce).await;
    
    // Try to exchange with wrong verifier
    let result = server.token(TokenRequest {
        grant_type: "authorization_code".to_string(),
        code,
        redirect_uri: Url::parse("http://localhost/callback").unwrap(),
        client_id: "test-client".to_string(),
        code_verifier: "wrong-verifier".to_string(),
    }).await;
    
    assert!(matches!(result, Err(AuthError::InvalidGrant)));
}
```

## References

- [RFC 6749 - OAuth 2.0](https://tools.ietf.org/html/rfc6749)
- [RFC 7636 - PKCE](https://tools.ietf.org/html/rfc7636)
- [OAuth 2.0 Security Best Current Practice](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)
- [OAuth 2.0 for Browser-Based Apps](https://tools.ietf.org/html/draft-ietf-oauth-browser-based-apps)
