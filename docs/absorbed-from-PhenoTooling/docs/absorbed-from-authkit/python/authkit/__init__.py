"""authkit — public API aggregator for the AuthKit Python SDK.

This package is the canonical re-export surface for the AuthKit Python SDK
that historically lived as three sibling sub-packages under
``AuthKit/python/``:

* ``pheno-auth``        — authentication core (managers, providers, MFA, JWT,
                          sessions, RBAC, SAML, SCIM, API keys, enterprise)
* ``pheno-credentials`` — secure credential broker (keyring, encrypted
                          storage, project-scoped + global credentials)
* ``pheno-security``    — security primitives (encryption, hashing, JWT
                          utilities, PII scanning, secret scanning)

All three are now also published (or are pending publication) as standalone
PyPI packages.  Importing from ``authkit`` re-exports their public APIs in
a single namespace, giving downstream applications a single, stable import
path that survives the per-package versioning churn.

The canonical substrate home for these packages is
``KooshaPari/phenotype-python-sdk`` (see the ``packages/auth-kit/``
directory).  This aggregator exists for backwards compatibility with code
that still imports from ``authkit.*``.

Quickstart
----------

    >>> from authkit import AuthManager, CredentialBroker, PIIScanner
    >>> mgr = AuthManager(...)
    >>> creds = CredentialBroker()
    >>> scanner = PIIScanner()

Stability
---------

``authkit`` follows the same deprecation policy as the underlying packages:
when a symbol is removed from ``pheno-auth`` / ``pheno-credentials`` /
``pheno-security``, its re-export here is kept behind a ``DeprecationWarning``
for one minor release before being removed.

See ``README.md`` for the full SDK surface and migration notes.
"""

from __future__ import annotations

from pheno_auth import (
    # Managers and registries
    AuthManager,
    AuthProvider,
    AuthProviderRegistry,
    AuthResult,
    AuthTokens,
    AuthenticationError,
    AuthorizationError,
    CachedToken,
    ConfigurationError,
    CredentialError,
    CredentialManager,
    Credentials,
    EncryptedTokenStorage,
    FileTokenManager,
    InMemorySessionStore,
    InteractiveCredentialManager,
    JWTHandler,
    MFAAdapter,
    MFAAdapterRegistry,
    MFAContext,
    MFAHandler,
    MFAMethod,
    MFARequiredError,
    MockBrowserAdapter,
    OAuthTokens,
    PlaywrightOAuthAdapter,
    ProviderError,
    ProviderRegistry,
    ProviderType,
    Role,
    RoleChecker,
    RBACError,
    RBACManager,
    RoleNotFoundError,
    SAMLError,
    SAMLConfig,
    SAMLHandler,
    SAMLResponseError,
    SAMLRequest,
    SAMLResponse,
    SamlSP,
    SCIMConflictError,
    SCIMError,
    SCIMFilterError,
    SCIMHandler,
    SCIMNotFoundError,
    SCIMService,
    SCIMStore,
    SCIMUser,
    SCIMGroup,
    SessionManager,
    SessionOAuthBroker,
    SessionStore,
    TokenCache,
    TokenError,
    TokenExpiredError,
    TokenManager,
    UserRole,
    create_auth_header,
    decode_jwt,
    decode_jwt_unverified,
    ensure_oauth_credentials,
    generate_totp_secret,
    has_permission,
    prompt_for_value,
    require_role,
    # MFA implementations
    EmailAdapter,
    EmailMFAAdapter,
    PushAdapter,
    PushNotificationAdapter,
    SMSAdapter,
    SMSMFAAdapter,
    TOTPAdapter,
    TOTPHandler,
    # Provider implementations
    Auth0Provider,
    AuthKitProvider,
    OAuth2GenericProvider,
    create_mfa_adapter,
    create_provider,
    get_mfa_registry,
    get_provider_registry,
    get_saml_attributes,
    register_mfa_adapter,
    register_provider,
)
from pheno_credentials import (
    AuditLogger,
    Credential,
    CredentialBroker,
    CredentialScope,
    CredentialStore,
    CredentialType,
    EncryptedFileStore,
    EncryptionService,
    EnvironmentManager,
    KeyringStore,
    ProjectManager,
    get_credential,
    get_credential_broker,
)
from pheno_security import (
    PIIScanner,
    ScanSummary,
    SecretFinding,
    SuppressionRules,
    create_jwt,
    decode_jwt as decode_jwt_unverified_security,
    decrypt,
    detect_pii,
    encrypt,
    generate_key,
    generate_token,
    hash_password,
    hash_string,
    redact_pii,
    scan_paths,
    verify_jwt,
    verify_password,
)

__version__ = "0.2.0"

__all__ = [
    # pheno-auth
    "Auth0Provider",
    "AuthError",
    "AuthKitProvider",
    "AuthManager",
    "AuthProvider",
    "AuthProviderRegistry",
    "AuthResult",
    "AuthTokens",
    "AuthenticationError",
    "AuthorizationError",
    "CachedToken",
    "ConfigurationError",
    "CredentialError",
    "CredentialManager",
    "Credentials",
    "EmailAdapter",
    "EmailMFAAdapter",
    "EncryptedTokenStorage",
    "FileTokenManager",
    "InMemorySessionStore",
    "InteractiveCredentialManager",
    "JWTHandler",
    "MFAAdapter",
    "MFAAdapterRegistry",
    "MFAContext",
    "MFAHandler",
    "MFAMethod",
    "MFARequiredError",
    "MockBrowserAdapter",
    "OAuth2GenericProvider",
    "OAuthTokens",
    "PlaywrightOAuthAdapter",
    "ProviderError",
    "ProviderRegistry",
    "ProviderType",
    "PushAdapter",
    "PushNotificationAdapter",
    "RBACError",
    "RBACManager",
    "Role",
    "RoleChecker",
    "RoleNotFoundError",
    "ROLES",
    "ROLE_HIERARCHY",
    "ROLE_PERMISSIONS",
    "SAMLError",
    "SAMLConfig",
    "SAMLHandler",
    "SAMLRequest",
    "SAMLResponse",
    "SAMLResponseError",
    "SamlSP",
    "SCIMConflictError",
    "SCIMError",
    "SCIMFilterError",
    "SCIMGroup",
    "SCIMHandler",
    "SCIMNotFoundError",
    "SCIMService",
    "SCIMStore",
    "SCIMUser",
    "SMSAdapter",
    "SMSMFAAdapter",
    "SessionManager",
    "SessionOAuthBroker",
    "SessionStore",
    "TOTPAdapter",
    "TOTPHandler",
    "TokenCache",
    "TokenError",
    "TokenExpiredError",
    "TokenManager",
    "UserRole",
    "api_keys_router",
    "scim_router",
    "create_auth_header",
    "create_mfa_adapter",
    "create_provider",
    "decode_jwt",
    "decode_jwt_unverified",
    "ensure_oauth_credentials",
    "generate_totp_secret",
    "get_mfa_registry",
    "get_provider_registry",
    "get_saml_attributes",
    "has_permission",
    "prompt_for_value",
    "register_mfa_adapter",
    "register_provider",
    "require_role",
    # pheno-credentials
    "AuditLogger",
    "Credential",
    "CredentialBroker",
    "CredentialScope",
    "CredentialStore",
    "CredentialType",
    "EncryptedFileStore",
    "EncryptionService",
    "EnvironmentManager",
    "KeyringStore",
    "ProjectManager",
    "get_credential",
    "get_credential_broker",
    # pheno-security
    "PIIScanner",
    "ScanSummary",
    "SecretFinding",
    "SuppressionRules",
    "create_jwt",
    "decrypt",
    "detect_pii",
    "encrypt",
    "generate_key",
    "generate_token",
    "hash_password",
    "hash_string",
    "redact_pii",
    "scan_paths",
    "verify_jwt",
    "verify_password",
]
