//! Phenotype BID - Business Identifier utilities
//!
//! Provides typed identifiers and BID (Business ID) utilities.

#![cfg_attr(docsrs, feature(doc_auto_cfg))]

use std::fmt;
use std::str::FromStr;

use chrono::{DateTime, Utc};
use phenotype_content_hash::ContentHash;
use serde::{Deserialize, Serialize};

/// Business ID with type safety
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Bid<T> {
    value: String,
    _phantom: std::marker::PhantomData<T>,
}

impl<T> Bid<T> {
    pub fn new(value: impl Into<String>) -> Self {
        Self {
            value: value.into(),
            _phantom: std::marker::PhantomData,
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        // Validate BID format
        if s.len() >= 3
            && s.chars()
                .all(|c| c.is_alphanumeric() || c == '-' || c == '_')
        {
            Some(Self::new(s))
        } else {
            None
        }
    }

    pub fn as_str(&self) -> &str {
        &self.value
    }

    pub fn generate(prefix: &str) -> Self {
        let timestamp = Utc::now().timestamp_millis();
        let random = rand::random::<u16>();
        Self::new(format!("{}-{}-{}", prefix, timestamp, random))
    }
}

impl<T> fmt::Display for Bid<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.value)
    }
}

impl<T> FromStr for Bid<T> {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::parse(s).ok_or_else(|| "Invalid BID format".to_string())
    }
}

/// Typed business entity marker traits
pub mod entities {
    pub struct User;
    pub struct Organization;
    pub struct Project;
    pub struct Team;
    pub struct Resource;
    pub struct Policy;
    pub struct Role;
    pub struct Permission;
    pub struct Event;
    pub struct Task;
}

/// BID types
pub type UserId = Bid<entities::User>;
pub type OrgId = Bid<entities::Organization>;
pub type ProjectId = Bid<entities::Project>;
pub type TeamId = Bid<entities::Team>;
pub type ResourceId = Bid<entities::Resource>;
pub type PolicyId = Bid<entities::Policy>;
pub type RoleId = Bid<entities::Role>;
pub type PermissionId = Bid<entities::Permission>;
pub type EventId = Bid<entities::Event>;
pub type TaskId = Bid<entities::Task>;

/// Content-addressed BID
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentBid {
    pub hash: ContentHash,
    pub timestamp: DateTime<Utc>,
}

impl ContentBid {
    pub fn new(hash: ContentHash) -> Self {
        Self {
            hash,
            timestamp: Utc::now(),
        }
    }

    pub fn to_string(&self) -> String {
        format!("{}@{}", self.hash, self.timestamp)
    }
}

/// Namespace-qualified BID
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NamespacedBid {
    pub namespace: String,
    pub id: String,
}

impl NamespacedBid {
    pub fn new(namespace: impl Into<String>, id: impl Into<String>) -> Self {
        Self {
            namespace: namespace.into(),
            id: id.into(),
        }
    }

    pub fn to_string(&self) -> String {
        format!("{}:{}", self.namespace, self.id)
    }

    pub fn parse(s: &str) -> Option<Self> {
        let parts: Vec<&str> = s.splitn(2, ':').collect();
        if parts.len() == 2 {
            Some(Self::new(parts[0], parts[1]))
        } else {
            None
        }
    }
}

/// BID registry for tracking ID allocations
#[derive(Debug, Default)]
pub struct BidRegistry {
    allocated: std::collections::HashSet<String>,
}

impl BidRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn allocate(&mut self, bid: impl fmt::Display) -> bool {
        self.allocated.insert(bid.to_string())
    }

    pub fn is_allocated(&self, bid: &str) -> bool {
        self.allocated.contains(bid)
    }

    pub fn release(&mut self, bid: &str) -> bool {
        self.allocated.remove(bid)
    }
}

/// BID generator with collision detection
pub struct BidGenerator {
    registry: BidRegistry,
    prefix: String,
}

impl BidGenerator {
    pub fn new(prefix: impl Into<String>) -> Self {
        Self {
            registry: BidRegistry::new(),
            prefix: prefix.into(),
        }
    }

    pub fn generate<T>(&mut self) -> Bid<T> {
        loop {
            let bid = Bid::<T>::generate(&self.prefix);
            if self.registry.allocate(&bid) {
                return bid;
            }
        }
    }
}

use rand;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bid_parsing() {
        assert!(Bid::<entities::User>::parse("user-123").is_some());
        assert!(Bid::<entities::User>::parse("").is_none());
        assert!(Bid::<entities::User>::parse("ab").is_none());
    }

    #[test]
    fn test_namespaced_bid() {
        let bid = NamespacedBid::new("org", "123");
        assert_eq!(bid.to_string(), "org:123");
        assert_eq!(NamespacedBid::parse("org:123"), Some(bid));
    }
}
