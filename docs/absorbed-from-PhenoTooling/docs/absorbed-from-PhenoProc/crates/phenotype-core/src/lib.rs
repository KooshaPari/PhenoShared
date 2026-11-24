//! Phenotype core library

pub struct Core;

impl Core {
    pub fn new() -> Self {
        Self
    }
}

impl Default for Core {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_creates_core() {
        let _ = Core::new();
    }

    #[test]
    fn default_matches_new() {
        let a: Core = Core::default();
        let b = Core::new();
        // Both produce equivalent values; we can only assert by construction.
        let _ = (a, b);
    }
}
