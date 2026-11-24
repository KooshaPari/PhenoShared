//! When - Action phase for BDD tests

pub struct When<T> {
    state: T,
}

impl<T> When<T> {
    pub fn new(state: T) -> Self {
        Self { state }
    }

    pub fn state(&self) -> &T {
        &self.state
    }

    pub fn into_state(self) -> T {
        self.state
    }
}

impl<T> From<T> for When<T> {
    fn from(state: T) -> Self {
        Self { state }
    }
}

impl<T> From<crate::Given<T>> for When<T> {
    fn from(given: crate::Given<T>) -> Self {
        Self::new(given.into_state())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_stores_state() {
        let w: When<i32> = When::new(7);
        assert_eq!(w.state(), &7);
    }

    #[test]
    fn into_state_consumes_and_returns_owned() {
        let w: When<String> = When::new(String::from("hello"));
        let s: String = w.into_state();
        assert_eq!(s, "hello");
    }

    #[test]
    fn from_t_implements_into() {
        let w: When<i32> = 42.into();
        assert_eq!(w.state(), &42);
    }

    #[test]
    fn from_given_moves_state() {
        let g: crate::Given<i32> = crate::Given::new(100);
        let w: When<i32> = g.into();
        assert_eq!(w.state(), &100);
    }
}
