//! Common validation types

/// Trait for types that can be validated
pub trait Validatable {
    /// Validation error type
    type Error;

    /// Validate the value
    fn validate(&self) -> Result<(), Self::Error>;
}

/// Range validation for numeric types
#[derive(Debug, Clone)]
pub struct Range<T> {
    min: Option<T>,
    max: Option<T>,
}

impl<T> Range<T> {
    pub fn new() -> Self {
        Self {
            min: None,
            max: None,
        }
    }

    pub fn with_min(mut self, min: T) -> Self {
        self.min = Some(min);
        self
    }

    pub fn with_max(mut self, max: T) -> Self {
        self.max = Some(max);
        self
    }

    /// Check if value is in range
    pub fn contains(&self, value: &T) -> bool
    where
        T: PartialOrd,
    {
        if let Some(min) = &self.min {
            if value < min {
                return false;
            }
        }
        if let Some(max) = &self.max {
            if value > max {
                return false;
            }
        }
        true
    }
}

impl<T> Default for Range<T> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn range_new_is_unbounded() {
        let r: Range<i32> = Range::new();
        assert!(r.contains(&-1_000_000));
        assert!(r.contains(&0));
        assert!(r.contains(&1_000_000));
    }

    #[test]
    fn range_default_matches_new() {
        let a: Range<i32> = Range::default();
        let b: Range<i32> = Range::new();
        assert!(a.contains(&0));
        assert!(b.contains(&0));
    }

    #[test]
    fn range_with_min_inclusive() {
        let r: Range<i32> = Range::new().with_min(0);
        assert!(!r.contains(&-1));
        assert!(r.contains(&0)); // min is inclusive
        assert!(r.contains(&100));
    }

    #[test]
    fn range_with_max_inclusive() {
        let r: Range<i32> = Range::new().with_max(10);
        assert!(r.contains(&-100));
        assert!(r.contains(&10)); // max is inclusive
        assert!(!r.contains(&11));
    }

    #[test]
    fn range_with_min_and_max() {
        let r: Range<i32> = Range::new().with_min(0).with_max(100);
        assert!(!r.contains(&-1));
        assert!(r.contains(&0));
        assert!(r.contains(&50));
        assert!(r.contains(&100));
        assert!(!r.contains(&101));
    }

    #[test]
    fn range_works_with_floats() {
        let r: Range<f64> = Range::new().with_min(0.0).with_max(1.0);
        assert!(r.contains(&0.0));
        assert!(r.contains(&0.5));
        assert!(r.contains(&1.0));
        assert!(!r.contains(&-0.1));
        assert!(!r.contains(&1.1));
    }

    #[test]
    fn range_can_be_reversed_via_setters() {
        // Setting min=10, max=5 produces an empty range — the API permits it.
        let r: Range<i32> = Range::new().with_min(10).with_max(5);
        assert!(!r.contains(&7));
    }

    struct CustomError(&'static str);
    struct Thing {
        value: i32,
    }

    impl Validatable for Thing {
        type Error = CustomError;
        fn validate(&self) -> Result<(), Self::Error> {
            if self.value >= 0 {
                Ok(())
            } else {
                Err(CustomError("negative"))
            }
        }
    }

    #[test]
    fn validatable_trait_can_be_implemented() {
        let ok = Thing { value: 5 };
        let bad = Thing { value: -1 };
        assert!(ok.validate().is_ok());
        assert!(bad.validate().is_err());
    }
}
