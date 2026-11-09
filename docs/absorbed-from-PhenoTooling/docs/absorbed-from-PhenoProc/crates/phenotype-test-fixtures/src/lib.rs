//! Test fixtures for Phenotype

/// Fixture trait
pub trait Fixture<T>: Clone {
    /// Create a fixture
    fn create() -> T;
}

/// Test data fixture
#[derive(Debug, Clone)]
pub struct TestData;

impl Fixture<TestData> for TestData {
    fn create() -> TestData {
        TestData
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_data_fixture_create() {
        let _ = <TestData as Fixture<TestData>>::create();
    }

    #[test]
    fn test_data_is_clone_and_debug() {
        let a = TestData;
        let b = a.clone();
        let dbg = format!("{:?}", b);
        assert!(dbg.contains("TestData"));
    }
}
