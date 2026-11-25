use thiserror::Error;

#[derive(Error, Debug)]
pub enum MonitorServiceError {
    #[error("Router not found: {0}")]
    RouterNotFound(String),
    #[error("Connection failed: {0}")]
    ConnectionFailed(String),
    #[error("Timeout: {0}")]
    Timeout(String),
}

pub type MonitorServiceResult<T> = Result<T, MonitorServiceError>;

pub struct RouterMonitorService {
    pub name: String,
    pub version: String,
}

impl RouterMonitorService {
    pub fn new(name: String, version: String) -> Self {
        Self { name, version }
    }

    pub fn service_name(&self) -> &str {
        &self.name
    }

    pub fn service_version(&self) -> &str {
        &self.version
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_service_creation() {
        let service = RouterMonitorService::new("router-monitor".into(), "1.0.0".into());
        assert_eq!(service.service_name(), "router-monitor");
        assert_eq!(service.service_version(), "1.0.0");
    }

    #[test]
    fn test_service_name_and_version_accessors() {
        let service = RouterMonitorService::new("svc".into(), "2.5.1".into());
        assert_eq!(service.service_name(), "svc");
        assert_eq!(service.service_version(), "2.5.1");
    }

    #[test]
    fn test_service_name_returns_reference() {
        let service = RouterMonitorService::new("hello".into(), "v1".into());
        // The accessor returns a borrow; ensure it lives correctly.
        let name: &str = service.service_name();
        assert_eq!(name, "hello");
    }

    #[test]
    fn test_monitor_service_error_display() {
        let nf = MonitorServiceError::RouterNotFound("r1".into());
        assert!(format!("{}", nf).contains("r1"));
        assert!(format!("{}", nf).contains("not found"));

        let conn = MonitorServiceError::ConnectionFailed("refused".into());
        assert!(format!("{}", conn).contains("refused"));
        assert!(format!("{}", conn).contains("Connection failed"));

        let timeout = MonitorServiceError::Timeout("30s".into());
        assert!(format!("{}", timeout).contains("30s"));
        assert!(format!("{}", timeout).contains("Timeout"));
    }
}
