//! Test fixtures

/// Test fixture trait
pub trait Fixturable {
    fn name(&self) -> &str;
}

/// Test fixture
pub struct Fixture {
    pub name: String,
}

impl Fixturable for Fixture {
    fn name(&self) -> &str {
        &self.name
    }
}

impl Fixture {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fixture_implements_fixturable() {
        let f = Fixture::new("my-test");
        assert_eq!(f.name(), "my-test");
    }

    #[test]
    fn test_fixturable_trait_bound() {
        fn assert_fixturable<T: Fixturable>(_t: &T) {}
        let f = Fixture::new("bound-check");
        assert_fixturable(&f);
    }
}
