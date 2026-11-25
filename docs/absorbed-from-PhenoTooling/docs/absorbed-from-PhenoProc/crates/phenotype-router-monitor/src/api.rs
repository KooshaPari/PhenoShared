use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiVersion {
    pub version: String,
    pub build_date: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiInfo {
    pub service: String,
    pub version: ApiVersion,
    pub endpoints: Vec<String>,
}

impl ApiInfo {
    pub fn new(service: String, version: String) -> Self {
        Self {
            service,
            version: ApiVersion {
                version,
                build_date: chrono::Utc::now().to_rfc3339(),
            },
            endpoints: vec![
                "/api/v1/routers/{id}/metrics".into(),
                "/api/v1/routers/metrics".into(),
                "/api/v1/routers/{id}/status".into(),
                "/api/v1/health".into(),
            ],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api_info_creation() {
        let info = ApiInfo::new("router-monitor".into(), "1.0.0".into());
        assert_eq!(info.service, "router-monitor");
        assert_eq!(info.endpoints.len(), 4);
    }

    #[test]
    fn test_api_info_endpoints() {
        let info = ApiInfo::new("svc".into(), "v1".into());
        assert!(info.endpoints.iter().any(|e| e.contains("metrics")));
        assert!(info.endpoints.iter().any(|e| e.contains("status")));
        assert!(info.endpoints.iter().any(|e| e.contains("health")));
    }

    #[test]
    fn test_api_info_build_date_set() {
        let info = ApiInfo::new("svc".into(), "v1".into());
        // build_date should be a non-empty RFC3339 string
        assert!(!info.version.build_date.is_empty());
        // Should contain 'T' separating date and time.
        assert!(info.version.build_date.contains('T'));
    }

    #[test]
    fn test_api_version_serde_roundtrip() {
        let v = ApiVersion {
            version: "1.0.0".into(),
            build_date: "2026-01-01T00:00:00+00:00".into(),
        };
        let j = serde_json::to_string(&v).unwrap();
        let v2: ApiVersion = serde_json::from_str(&j).unwrap();
        assert_eq!(v2.version, "1.0.0");
    }

    #[test]
    fn test_api_info_serde_roundtrip() {
        let info = ApiInfo::new("svc".into(), "1.0.0".into());
        let j = serde_json::to_string(&info).unwrap();
        let info2: ApiInfo = serde_json::from_str(&j).unwrap();
        assert_eq!(info2.service, "svc");
        assert_eq!(info2.version.version, "1.0.0");
        assert_eq!(info2.endpoints.len(), info.endpoints.len());
    }
}
