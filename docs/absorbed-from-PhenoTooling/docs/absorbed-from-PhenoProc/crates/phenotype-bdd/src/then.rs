//! Then - Assertion phase for BDD tests

pub struct Then<T> {
    state: T,
}

impl<T> Then<T> {
    pub fn new(state: T) -> Self {
        Self { state }
    }

    pub fn state(&self) -> &T {
        &self.state
    }

    pub fn into_state(self) -> T {
        self.state
    }

    /// Assert a condition on the state
    pub fn assert<F>(self, f: F) -> Self
    where
        F: FnOnce(&T) -> bool,
    {
        assert!(f(&self.state), "Assertion failed");
        self
    }
}

impl<T> From<T> for Then<T> {
    fn from(state: T) -> Self {
        Self { state }
    }
}

impl<T> From<crate::When<T>> for Then<T> {
    fn from(when: crate::When<T>) -> Self {
        Self::new(when.into_state())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_stores_state() {
        let t: Then<i32> = Then::new(7);
        assert_eq!(t.state(), &7);
    }

    #[test]
    fn into_state_consumes_and_returns_owned() {
        let t: Then<String> = Then::new(String::from("hello"));
        let s: String = t.into_state();
        assert_eq!(s, "hello");
    }

    #[test]
    fn from_t_implements_into() {
        let t: Then<i32> = 42.into();
        assert_eq!(t.state(), &42);
    }

    #[test]
    fn from_when_moves_state() {
        let w: crate::When<i32> = crate::When::new(99);
        let t: Then<i32> = w.into();
        assert_eq!(t.state(), &99);
    }

    #[test]
    fn assert_passes_when_predicate_true() {
        let t: Then<i32> = Then::new(10);
        let after = t.assert(|n| *n == 10);
        // assert returns self, so we can chain.
        assert_eq!(after.state(), &10);
    }

    #[test]
    #[should_panic(expected = "Assertion failed")]
    fn assert_panics_when_predicate_false() {
        let t: Then<i32> = Then::new(10);
        t.assert(|n| *n == 99);
    }
}
