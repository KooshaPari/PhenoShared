//! HTTP client core library

pub struct HttpClient;

impl HttpClient {
    pub fn new() -> Self {
        Self
    }
}

impl Default for HttpClient {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_creates_http_client() {
        let _ = HttpClient::new();
    }

    #[test]
    fn default_matches_new() {
        let a: HttpClient = HttpClient::default();
        let b = HttpClient::new();
        let _ = (a, b);
    }
}
