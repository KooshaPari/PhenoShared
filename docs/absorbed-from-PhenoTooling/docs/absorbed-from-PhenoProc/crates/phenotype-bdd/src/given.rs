//! Given - Setup phase for BDD tests

pub struct Given<T> {
    state: T,
}

impl<T> Given<T> {
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

impl<T> From<T> for Given<T> {
    fn from(state: T) -> Self {
        Self { state }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_stores_state() {
        let g: Given<i32> = Given::new(7);
        assert_eq!(g.state(), &7);
    }

    #[test]
    fn into_state_consumes_and_returns_owned() {
        let g: Given<String> = Given::new(String::from("hello"));
        let s: String = g.into_state();
        assert_eq!(s, "hello");
    }

    #[test]
    fn from_t_implements_into() {
        let g: Given<i32> = 42.into();
        assert_eq!(g.state(), &42);
    }

    #[test]
    fn state_is_borrowed_reference() {
        let g: Given<Vec<u8>> = Given::new(vec![1, 2, 3]);
        assert_eq!(g.state(), &vec![1, 2, 3]);
        assert_eq!(g.state().len(), 3);
    }
}
