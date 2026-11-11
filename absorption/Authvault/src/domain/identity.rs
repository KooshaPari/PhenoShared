use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Unique user identifier
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct UserId(pub String);

impl UserId {
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }
}

impl Default for UserId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for UserId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl UserId {
    /// Construct a `UserId` from an existing string value.
    pub fn from_string(s: impl Into<String>) -> Self {
        Self(s.into())
    }
}

/// User entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: UserId,
    pub email: String,
    pub active: bool,
    pub email_verified: bool,
    pub roles: Vec<Role>,
    pub password_hash: Option<String>,
    pub attributes: HashMap<String, serde_json::Value>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub last_login: Option<DateTime<Utc>>,
}

impl User {
    pub fn new(email: impl Into<String>) -> Self {
        let now = Utc::now();
        Self {
            id: UserId::new(),
            email: email.into(),
            active: true,
            email_verified: false,
            roles: Vec::new(),
            password_hash: None,
            attributes: HashMap::new(),
            created_at: now,
            updated_at: now,
            last_login: None,
        }
    }

    pub fn with_password_hash(mut self, hash: impl Into<String>) -> Self {
        self.password_hash = Some(hash.into());
        self
    }

    pub fn with_role(mut self, role: Role) -> Self {
        self.roles.push(role);
        self
    }

    pub fn with_attribute(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.attributes.insert(key.into(), value);
        self
    }

    pub fn has_role(&self, role_name: &str) -> bool {
        self.roles.iter().any(|r| r.name == role_name || r.implies(role_name))
    }

    pub fn has_permission(&self, permission: &str) -> bool {
        self.roles.iter().any(|r| r.has_permission(permission))
    }

    /// Mark the email as verified and update `updated_at`.
    pub fn verify(&mut self) {
        self.email_verified = true;
        self.updated_at = Utc::now();
    }

    /// Deactivate the account.
    pub fn deactivate(&mut self) {
        self.active = false;
        self.updated_at = Utc::now();
    }

    /// Record a login timestamp.
    pub fn record_login(&mut self) {
        let now = Utc::now();
        self.last_login = Some(now);
        self.updated_at = now;
    }
}

/// Role definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Role {
    pub name: String,
    /// Parent role names (supports multiple inheritance).
    pub parents: Vec<String>,
    pub permissions: Vec<Permission>,
}

impl Role {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into(), parents: Vec::new(), permissions: Vec::new() }
    }

    pub fn with_parent(mut self, parent: impl Into<String>) -> Self {
        self.parents.push(parent.into());
        self
    }

    pub fn with_permission(mut self, permission: Permission) -> Self {
        self.permissions.push(permission);
        self
    }

    pub fn implies(&self, role: &str) -> bool {
        self.parents.iter().any(|p| p == role)
    }

    pub fn has_permission(&self, permission: &str) -> bool {
        self.permissions.iter().any(|p| p.matches(permission))
    }
}

/// Pre-built standard roles.
pub mod roles {
    use super::{Permission, Role};

    /// Admin role with full access.
    pub fn admin() -> Role {
        Role::new("admin").with_permission(Permission::new("*", vec!["*".to_string()]))
    }

    /// Regular user role with self-service access.
    pub fn user() -> Role {
        Role::new("user").with_permission(Permission::new(
            "self:profile",
            vec!["read".to_string(), "write".to_string()],
        ))
    }

    /// Guest role with public read access.
    pub fn guest() -> Role {
        Role::new("guest").with_permission(Permission::new("public", vec!["read".to_string()]))
    }
}

/// Permission pattern
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Permission {
    pub resource: String,
    pub actions: Vec<String>,
}

impl Permission {
    pub fn new(resource: impl Into<String>, actions: Vec<String>) -> Self {
        Self { resource: resource.into(), actions }
    }

    pub fn matches(&self, resource_action: &str) -> bool {
        // Split on the LAST `:` so that resource paths like `"self:profile:read"`
        // are interpreted as resource=`"self:profile"`, action=`"read"`.
        let Some(sep) = resource_action.rfind(':') else {
            return false;
        };
        let resource = &resource_action[..sep];
        let action = &resource_action[sep + 1..];
        self.matches_resource_action(resource, action)
    }

    pub fn matches_resource_action(&self, resource: &str, action: &str) -> bool {
        self.matches_resource(resource) && self.matches_action(action)
    }

    fn matches_action(&self, action: &str) -> bool {
        self.actions.iter().any(|a| a == "*" || a == action)
    }

    pub fn matches_resource(&self, resource: &str) -> bool {
        if self.resource == "*" {
            return true;
        }
        if self.resource.ends_with(":*") {
            // Strip the trailing `*` to keep the colon, then require the resource to
            // start with `"prefix:"` so that `"users:*"` does NOT match bare `"users"`.
            let prefix = &self.resource[..self.resource.len() - 1];
            resource.starts_with(prefix)
        } else {
            self.resource == resource
        }
    }
}

/// Predefined roles (compatibility alias – prefer the `roles` module).
pub struct Roles;

impl Roles {
    pub fn admin() -> Role {
        roles::admin()
    }

    pub fn user() -> Role {
        roles::user()
    }

    pub fn guest() -> Role {
        roles::guest()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_creation() {
        let user = User::new("test@example.com");
        assert_eq!(user.email, "test@example.com");
        assert!(user.active);
        assert!(!user.email_verified);
    }

    #[test]
    fn test_role_hierarchy() {
        let admin = Role::new("admin").with_parent("moderator");
        let moderator = Role::new("moderator").with_parent("user");

        assert!(admin.implies("moderator"));
        assert!(moderator.implies("user"));
        assert!(!admin.implies("user"));
    }

    #[test]
    fn test_permission_matching() {
        let perm = Permission::new("users:*", vec!["read".to_string(), "write".to_string()]);

        assert!(perm.matches_resource_action("users:123", "read"));
        assert!(perm.matches_resource_action("users:123", "write"));
        assert!(!perm.matches_resource_action("users:123", "delete"));
        assert!(!perm.matches_resource_action("posts:123", "read"));
    }

    #[test]
    // Traces to: FR-AUTHVAULT-150
    fn test_user_has_role_direct_match() {
        let user = User::new("test@example.com").with_role(Role::new("admin"));
        assert!(user.has_role("admin"));
        assert!(!user.has_role("user"));
    }

    #[test]
    // Traces to: FR-AUTHVAULT-151
    fn test_user_has_role_via_hierarchy() {
        let user = User::new("test@example.com").with_role(Role::new("admin").with_parent("user"));
        assert!(user.has_role("admin"));
        assert!(user.has_role("user"));
        assert!(!user.has_role("guest"));
    }

    /// FR-AUTHVAULT-152: `matches_resource` correctly handles exact and wildcard prefix matching.
    #[test]
    fn test_permission_matches_resource_exact_and_wildcard() {
        let exact = Permission::new("users:123", vec!["read".to_string()]);
        assert!(exact.matches_resource("users:123"));
        assert!(!exact.matches_resource("users:456"));
        assert!(!exact.matches_resource("posts:123"));

        let wildcard = Permission::new("users:*", vec!["read".to_string()]);
        assert!(wildcard.matches_resource("users:123"));
        assert!(wildcard.matches_resource("users:456"));
        assert!(!wildcard.matches_resource("posts:123"));
        assert!(!wildcard.matches_resource("users")); // prefix must include the colon separator
    }
}
