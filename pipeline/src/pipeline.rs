//! The [`Pipeline`] type: composable item-stream transformations.

use crate::filters::Filter;
use crate::item::Item;

/// A pipeline that processes items through a chain of [`Filter`]s.
///
/// A pipeline owns its items and passes them through filters in turn via
/// [`Pipeline::apply`]. Each filter receives the output of the previous one,
/// so the pipeline behaves like a left-fold over the list of filters.
///
/// Filters are applied by reference, allowing the same filter to be reused
/// across multiple pipelines.
pub struct Pipeline {
    items: Vec<Item>,
}

impl Pipeline {
    /// Build a new pipeline that starts with `items` as its input stream.
    pub fn new(items: Vec<Item>) -> Self {
        Self { items }
    }

    /// Run `filter` over the current items and return a new [`Pipeline`]
    /// containing the filtered result. The receiver is consumed so the
    /// filters read in a fluent, left-to-right style.
    pub fn apply<F: Filter>(self, filter: &F) -> Pipeline {
        Pipeline {
            items: filter.apply(self.items),
        }
    }

    /// Consume the pipeline and return the underlying `Vec<Item>`.
    pub fn into_items(self) -> Vec<Item> {
        self.items
    }

    /// Number of items currently held by the pipeline.
    pub fn len(&self) -> usize {
        self.items.len()
    }

    /// `true` when the pipeline holds no items.
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::filters::{MapFilter, PredicateFilter, TakeFilter};

    fn items() -> Vec<Item> {
        vec![
            Item::new("a", "alpha"),
            Item::new("b", "beta"),
            Item::new("c", "gamma"),
            Item::new("d", "delta"),
        ]
    }

    #[test]
    fn test_pipeline_len() {
        let p = Pipeline::new(items());
        assert_eq!(p.len(), 4);
        assert!(!p.is_empty());
    }

    #[test]
    fn test_pipeline_empty() {
        let p = Pipeline::new(vec![]);
        assert!(p.is_empty());
    }

    #[test]
    fn test_pipeline_single_filter() {
        let result = Pipeline::new(items())
            .apply(&TakeFilter::new(2))
            .into_items();
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].key, "a");
        assert_eq!(result[1].key, "b");
    }

    #[test]
    fn test_pipeline_chained_filters() {
        let result = Pipeline::new(items())
            .apply(&PredicateFilter::new(|i| i.key != "a"))
            .apply(&TakeFilter::new(2))
            .into_items();
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].key, "b");
        assert_eq!(result[1].key, "c");
    }

    #[test]
    fn test_pipeline_map_then_filter() {
        let result = Pipeline::new(items())
            .apply(&MapFilter::new(|mut i| {
                i.tags.push(i.key.clone());
                i
            }))
            .apply(&crate::filters::TagFilter::new("b"))
            .into_items();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].key, "b");
    }
}