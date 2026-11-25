//! Plugin capability implementations: HTTP proxy, timer, filesystem.

pub mod http;

pub use http::{HttpCapability, HttpProxy, HttpRequest, HttpResponse};
