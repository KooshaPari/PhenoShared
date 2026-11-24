/// Extension trait adding `.context()` to `Result` types for richer messages.
pub trait ErrorContext<T, E> {
    /// Wrap the error with additional context.
    fn context(self, msg: impl Into<String>) -> Result<T, String>;
}

impl<T, E: std::fmt::Display> ErrorContext<T, E> for Result<T, E> {
    fn context(self, msg: impl Into<String>) -> Result<T, String> {
        self.map_err(|e| format!("{}: {e}", msg.into()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn context_helper() {
        let result: Result<(), &str> = Err("boom");
        let ctx = result.context("loading config");
        assert_eq!(ctx.unwrap_err(), "loading config: boom");
    }
}
