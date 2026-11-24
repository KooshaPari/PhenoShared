use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IpcEnvelope {
    pub command: String,
    pub request_id: String,
    pub payload: IpcPayload,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum IpcPayload {
    HealthCheck { timestamp_ms: u64 },
    ProjectLookup {
        repository: String,
        branch: String,
        include_metadata: bool,
    },
}

impl IpcEnvelope {
    pub fn sample_project_lookup() -> Self {
        Self {
            command: "project_lookup".to_string(),
            request_id: "bench-request-001".to_string(),
            payload: IpcPayload::ProjectLookup {
                repository: "kooshapari/BytePort".to_string(),
                branch: "main".to_string(),
                include_metadata: true,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::IpcEnvelope;

    #[test]
    fn ipc_envelope_json_round_trip() {
        let envelope = IpcEnvelope::sample_project_lookup();
        let json = serde_json::to_string(&envelope).expect("serialize IPC envelope");
        let decoded: IpcEnvelope =
            serde_json::from_str(&json).expect("deserialize IPC envelope");

        assert_eq!(decoded, envelope);
    }
}
