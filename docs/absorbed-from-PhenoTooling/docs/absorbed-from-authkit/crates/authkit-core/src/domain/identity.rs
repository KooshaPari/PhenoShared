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

/// User entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: UserId,
    pub email: String,
    pub active: bool,
    pub email_verified: bool,
    pub roles: Vec<Role>,
}

impl User {
    pub fn new(email: impl Into<String>) -> Self {
        Self {
            id: UserId::new(),
            email: email.into(),
            active: true,
            email_verified: false,
            roles: Vec::new(),
        }
    }

    pub fn with_role(mut self, role: Role) -> Self {
        self.roles.push(role);
        self
    }

    pub fn has_role(&self, role_name: &str) -> bool {
        self.roles.iter().any(|r| r.name == role_name || r.implies(role_name))
    }
}

/// Role definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Role {
    pub name: String,
    pub parent: Option<String>,
    pub permissions: Vec<Permission>,
}

impl Role {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            parent: None,
            permissions: Vec::new(),
        }
    }

    pub fn with_parent(mut self, parent: impl Into<String>) -> Self {
        self.parent = Some(parent.into());
        self
    }

    pub fn with_permission(mut self, permission: Permission) -> Self {
        self.permissions.push(permission);
        self
    }

    pub fn implies(&self, role: &str) -> bool {
        self.parent.as_ref().map_or(false, |p| p == role)
    }

    pub fn has_permission(&self, permission: &str) -> bool {
        self.permissions.iter().any(|p| p.matches(permission))
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
        Self {
            resource: resource.into(),
            actions,
        }
    }

    pub fn matches(&self, resource_action: &str) -> bool {
        let parts: Vec<&str> = resource_action.split(':').collect();
        if parts.len() != 2 {
            return false;
        }

        self.matches_resource_action(parts[0], parts[1])
    }

    pub fn matches_resource_action(&self, resource: &str, action: &str) -> bool {
        self.matches_resource(resource) && self.actions.contains(&action.to_string())
    }

    pub fn matches_resource(&self, resource: &str) -> bool {
        if self.resource.ends_with(":*") {
            let prefix = &self.resource[..self.resource.len() - 2];
            resource.starts_with(prefix)
        } else {
            self.resource == resource
        }
    }
}

/// Predefined roles
pub struct Roles;

impl Roles {
    pub fn admin() -> Role {
        Role::new("admin").with_permission(Permission::new("*", vec!["*".to_string()]))
    }

    pub fn user() -> Role {
        Role::new("user").with_permission(Permission::new("users:*", vec!["read".to_string(), "write".to_string()]))
    }

    pub fn guest() -> Role {
        Role::new("guest").with_permission(Permission::new("public:*", vec!["read".to_string()]))
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
    // Traces to: FR-AUTHKIT-150
    fn test_user_has_role_direct_match() {
        let user = User::new("test@example.com").with_role(Role::new("admin"));
        assert!(user.has_role("admin"));
        assert!(!user.has_role("user"));
    }

    #[test]
    // Traces to: FR-AUTHKIT-151
    fn test_user_has_role_via_hierarchy() {
        let user = User::new("test@example.com").with_role(Role::new("admin").with_parent("user"));
        assert!(user.has_role("admin"));
        assert!(user.has_role("user"));
        assert!(!user.has_role("guest"));
    }

    /// FR-AUTHKIT-152: `matches_resource` correctly handles exact and wildcard prefix matching.
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
