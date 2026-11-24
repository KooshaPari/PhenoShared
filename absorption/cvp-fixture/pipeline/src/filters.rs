//! Filter implementations and the [`Filter`] trait used by [`crate::Pipeline`].
//!
//! Each filter in this module operates on a `Vec<Item>` and produces a new
//! `Vec<Item>`. Filters are stateless and `Send + Sync` so they can be shared
//! across threads and composed in arbitrary order.

use crate::Item;
use std::collections::HashSet;

/// A transformation that takes a stream of [`Item`]s and returns a new stream.
///
/// Implementors must be safe to share across threads (`Send + Sync`) so they
/// can be applied concurrently by a [`crate::Pipeline`].
///
/// Filters are pure with respect to their input — `apply` should not mutate
/// any of the items it receives, only produce new ones.
pub trait Filter: Send + Sync {
    /// Apply this filter to a list of items, producing a (possibly different)
    /// list of items.
    fn apply(&self, items: Vec<Item>) -> Vec<Item>;

    /// Short, human-readable name for this filter. Used in logs and
    /// diagnostics; should be stable across versions.
    fn name(&self) -> &str;
}

/// Keep only items for which the supplied predicate returns `true`.
///
/// Items are visited in order and all that satisfy the predicate are emitted
/// in their original order.
pub struct PredicateFilter {
    predicate: Box<dyn Fn(&Item) -> bool + Send + Sync>,
}

impl PredicateFilter {
    /// Construct a new [`PredicateFilter`] from a predicate closure.
    ///
    /// The closure receives a reference to each item and must return `true`
    /// to keep the item or `false` to drop it.
    pub fn new(predicate: impl Fn(&Item) -> bool + Send + Sync + 'static) -> Self {
        Self {
            predicate: Box::new(predicate),
        }
    }
}

impl Filter for PredicateFilter {
    fn apply(&self, items: Vec<Item>) -> Vec<Item> {
        items.into_iter().filter(|i| (self.predicate)(i)).collect()
    }

    fn name(&self) -> &str {
        "predicate"
    }
}

/// Transform each item using the provided function.
///
/// The mapping function takes ownership of each [`Item`] and returns a
/// (possibly different) [`Item`]. Use this to enrich, normalize, or reshape
/// items as they pass through the pipeline.
pub struct MapFilter {
    func: Box<dyn Fn(Item) -> Item + Send + Sync>,
}

impl MapFilter {
    /// Construct a new [`MapFilter`] from a mapping closure.
    pub fn new(func: impl Fn(Item) -> Item + Send + Sync + 'static) -> Self {
        Self {
            func: Box::new(func),
        }
    }
}

impl Filter for MapFilter {
    fn apply(&self, items: Vec<Item>) -> Vec<Item> {
        items.into_iter().map(|i| (self.func)(i)).collect()
    }

    fn name(&self) -> &str {
        "map"
    }
}

/// Keep only the first `count` items, dropping the rest.
///
/// Mirrors the semantics of [`std::iter::Iterator::take`]: items beyond the
/// requested count are never produced.
pub struct TakeFilter {
    count: usize,
}

impl TakeFilter {
    /// Construct a new [`TakeFilter`] that keeps at most `count` items.
    pub fn new(count: usize) -> Self {
        Self { count }
    }
}

impl Filter for TakeFilter {
    fn apply(&self, items: Vec<Item>) -> Vec<Item> {
        items.into_iter().take(self.count).collect()
    }

    fn name(&self) -> &str {
        "take"
    }
}

/// Drop the first `count` items, keeping the remainder.
///
/// Mirrors the semantics of [`std::iter::Iterator::skip`]: the first `count`
/// items are discarded and the rest are emitted in their original order.
pub struct SkipFilter {
    count: usize,
}

impl SkipFilter {
    /// Construct a new [`SkipFilter`] that discards the first `count` items.
    pub fn new(count: usize) -> Self {
        Self { count }
    }
}

impl Filter for SkipFilter {
    fn apply(&self, items: Vec<Item>) -> Vec<Item> {
        items.into_iter().skip(self.count).collect()
    }

    fn name(&self) -> &str {
        "skip"
    }
}

/// Keep only items that carry a specific tag.
///
/// An item is kept if `item.tags` contains the configured tag string.
pub struct TagFilter {
    tag: String,
}

impl TagFilter {
    /// Construct a new [`TagFilter`] that keeps items tagged with `tag`.
    pub fn new(tag: impl Into<String>) -> Self {
        Self { tag: tag.into() }
    }
}

impl Filter for TagFilter {
    fn apply(&self, items: Vec<Item>) -> Vec<Item> {
        items
            .into_iter()
            .filter(|i| i.tags.contains(&self.tag))
            .collect()
    }

    fn name(&self) -> &str {
        "tag"
    }
}

/// Remove items that share a key with an earlier item.
///
/// When two or more items have the same [`Item::key`], the first occurrence
/// is kept and subsequent ones are dropped. Items are visited in input order
/// and the first-seen key wins, which makes the filter deterministic.
pub struct DeduplicateFilter;

impl DeduplicateFilter {
    /// Construct a new [`DeduplicateFilter`].
    pub fn new() -> Self {
        Self
    }
}

impl Default for DeduplicateFilter {
    fn default() -> Self {
        Self::new()
    }
}

impl Filter for DeduplicateFilter {
    fn apply(&self, items: Vec<Item>) -> Vec<Item> {
        let mut seen = HashSet::new();
        items
            .into_iter()
            .filter(|i| seen.insert(i.key.clone()))
            .collect()
    }

    fn name(&self) -> &str {
        "deduplicate"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn item(key: &str, value: &str) -> Item {
        Item::new(key, value)
    }

    #[test]
    fn test_predicate_filter() {
        let items = vec![item("a", "1"), item("b", "2"), item("c", "3")];
        let filter = PredicateFilter::new(|i| i.key != "b");
        let result = filter.apply(items);
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].key, "a");
        assert_eq!(result[1].key, "c");
    }

    #[test]
    fn test_map_filter() {
        let items = vec![item("a", "hello"), item("b", "world")];
        let filter = MapFilter::new(|mut i| {
            i.value = i.value.to_uppercase();
            i
        });
        let result = filter.apply(items);
        assert_eq!(result[0].value, "HELLO");
        assert_eq!(result[1].value, "WORLD");
    }

    #[test]
    fn test_take_filter() {
        let items = vec![item("a", "1"), item("b", "2"), item("c", "3")];
        let filter = TakeFilter::new(2);
        let result = filter.apply(items);
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].key, "a");
        assert_eq!(result[1].key, "b");
    }

    #[test]
    fn test_take_filter_more_than_input() {
        let items = vec![item("a", "1"), item("b", "2")];
        let filter = TakeFilter::new(10);
        let result = filter.apply(items);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_take_filter_zero() {
        let items = vec![item("a", "1"), item("b", "2")];
        let filter = TakeFilter::new(0);
        let result = filter.apply(items);
        assert!(result.is_empty());
    }

    #[test]
    fn test_skip_filter() {
        let items = vec![item("a", "1"), item("b", "2"), item("c", "3")];
        let filter = SkipFilter::new(1);
        let result = filter.apply(items);
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].key, "b");
    }

    #[test]
    fn test_tag_filter() {
        let items = vec![
            item("a", "1").with_tags(vec!["keep".into()]),
            item("b", "2"),
            item("c", "3").with_tags(vec!["keep".into()]),
        ];
        let filter = TagFilter::new("keep");
        let result = filter.apply(items);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_deduplicate_filter() {
        let items = vec![item("a", "1"), item("a", "2"), item("b", "3")];
        let filter = DeduplicateFilter::new();
        let result = filter.apply(items);
        assert_eq!(result.len(), 2);
        // First occurrence of key "a" must be the one kept.
        assert_eq!(result[0].key, "a");
        assert_eq!(result[0].value, "1");
        assert_eq!(result[1].key, "b");
    }

    #[test]
    fn test_deduplicate_filter_all_unique() {
        let items = vec![item("a", "1"), item("b", "2"), item("c", "3")];
        let filter = DeduplicateFilter::new();
        let result = filter.apply(items);
        assert_eq!(result.len(), 3);
    }

    #[test]
    fn test_deduplicate_filter_all_duplicates() {
        let items = vec![item("a", "1"), item("a", "2"), item("a", "3")];
        let filter = DeduplicateFilter::new();
        let result = filter.apply(items);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].value, "1");
    }

    #[test]
    fn test_deduplicate_filter_default() {
        // Use the unit-struct form here to keep the `Default` impl exercised
        // without tripping the `default_constructed_unit_structs` lint.
        let items = vec![item("a", "1"), item("a", "2")];
        let filter: DeduplicateFilter = Default::default();
        let result = filter.apply(items);
        assert_eq!(result.len(), 1);
    }
}