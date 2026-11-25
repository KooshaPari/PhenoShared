use serde::{Deserialize, Serialize};
use std::fmt;

/// A single data item flowing through the pipeline.
///
/// Every item carries a stable `key`, a payload `value`, and an optional set
/// of `tags` that other filters (such as [`crate::filters::TagFilter`]) can
/// inspect. Items implement `Clone`, `PartialEq`, `Eq`, and `Hash` so they
/// can be freely stored in collections and deduplicated by key.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Item {
    pub key: String,
    pub value: String,
    pub tags: Vec<String>,
}

impl Item {
    /// Construct a new [`Item`] with the given key and value and no tags.
    pub fn new(key: impl Into<String>, value: impl Into<String>) -> Self {
        Self {
            key: key.into(),
            value: value.into(),
            tags: Vec::new(),
        }
    }

    /// Attach `tags` to this item, replacing any previous tags, and return
    /// the modified item for builder-style chaining.
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }
}

impl fmt::Display for Item {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[{}] {}", self.key, self.value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_item_creation() {
        let item = Item::new("k1", "hello");
        assert_eq!(item.key, "k1");
        assert_eq!(item.value, "hello");
        assert!(item.tags.is_empty());
    }

    #[test]
    fn test_item_with_tags() {
        let item = Item::new("k1", "hello").with_tags(vec!["a".into(), "b".into()]);
        assert_eq!(item.tags, vec!["a", "b"]);
    }

    #[test]
    fn test_item_display() {
        let item = Item::new("k1", "hello");
        assert_eq!(format!("{item}"), "[k1] hello");
    }
}