use std::collections::HashMap;

use crate::builder::{HttpRequest, HttpResponse, ResponseBuilder};

#[derive(Debug, Clone)]
pub struct CorsConfig {
    pub allowed_origins: Vec<String>,
    pub allowed_methods: Vec<String>,
    pub allowed_headers: Vec<String>,
    pub allow_credentials: bool,
    pub max_age_seconds: Option<u64>,
}

impl CorsConfig {
    pub fn permissive() -> Self {
        Self {
            allowed_origins: vec!["*".to_owned()],
            allowed_methods: vec![
                "GET".to_owned(),
                "POST".to_owned(),
                "PUT".to_owned(),
                "PATCH".to_owned(),
                "DELETE".to_owned(),
                "OPTIONS".to_owned(),
            ],
            allowed_headers: vec![
                "authorization".to_owned(),
                "content-type".to_owned(),
                "x-request-id".to_owned(),
            ],
            allow_credentials: false,
            max_age_seconds: Some(600),
        }
    }

    pub fn origin_allowed(&self, origin: &str) -> bool {
        self.allowed_origins
            .iter()
            .any(|allowed| allowed == "*" || allowed == origin)
    }
}

impl Default for CorsConfig {
    fn default() -> Self {
        Self::permissive()
    }
}

#[derive(Debug, Clone)]
pub struct CorsLayer {
    config: CorsConfig,
}

impl CorsLayer {
    pub fn permissive() -> Self {
        Self::with_config(CorsConfig::permissive())
    }

    pub fn with_config(config: CorsConfig) -> Self {
        Self { config }
    }

    pub fn config(&self) -> &CorsConfig {
        &self.config
    }

    pub fn preflight(&self, request: &HttpRequest) -> HttpResponse {
        let origin = request
            .headers
            .get("Origin")
            .or_else(|| request.headers.get("origin"));
        let mut response = ResponseBuilder::no_content();
        if let Some(origin) = origin {
            self.apply_origin_headers(&mut response.headers, origin);
        }
        response.headers.insert(
            "Access-Control-Allow-Methods".to_owned(),
            self.config.allowed_methods.join(", "),
        );
        response.headers.insert(
            "Access-Control-Allow-Headers".to_owned(),
            self.config.allowed_headers.join(", "),
        );
        if let Some(max_age) = self.config.max_age_seconds {
            response
                .headers
                .insert("Access-Control-Max-Age".to_owned(), max_age.to_string());
        }
        response
    }

    pub fn decorate_response(&self, request: &HttpRequest, response: &mut HttpResponse) {
        if let Some(origin) = request
            .headers
            .get("Origin")
            .or_else(|| request.headers.get("origin"))
        {
            self.apply_origin_headers(&mut response.headers, origin);
        }
    }

    fn apply_origin_headers(&self, headers: &mut HashMap<String, String>, origin: &str) {
        if !self.config.origin_allowed(origin) {
            return;
        }
        let value = if self
            .config
            .allowed_origins
            .iter()
            .any(|allowed| allowed == "*")
            && !self.config.allow_credentials
        {
            "*"
        } else {
            origin
        };
        headers.insert("Access-Control-Allow-Origin".to_owned(), value.to_owned());
        if self.config.allow_credentials {
            headers.insert(
                "Access-Control-Allow-Credentials".to_owned(),
                "true".to_owned(),
            );
        }
    }
}
