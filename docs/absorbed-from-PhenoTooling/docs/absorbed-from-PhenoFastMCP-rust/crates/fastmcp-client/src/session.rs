//! Client session state.

use fastmcp_protocol::{ClientCapabilities, ClientInfo, ServerCapabilities, ServerInfo};

/// Client-side session state.
#[derive(Debug)]
pub struct ClientSession {
    /// Client info sent during initialization.
    client_info: ClientInfo,
    /// Client capabilities sent during initialization.
    client_capabilities: ClientCapabilities,
    /// Server info received during initialization.
    server_info: ServerInfo,
    /// Server capabilities received during initialization.
    server_capabilities: ServerCapabilities,
    /// Negotiated protocol version.
    protocol_version: String,
}

impl ClientSession {
    /// Creates a new client session after successful initialization.
    #[must_use]
    pub fn new(
        client_info: ClientInfo,
        client_capabilities: ClientCapabilities,
        server_info: ServerInfo,
        server_capabilities: ServerCapabilities,
        protocol_version: String,
    ) -> Self {
        Self {
            client_info,
            client_capabilities,
            server_info,
            server_capabilities,
            protocol_version,
        }
    }

    /// Returns the client info.
    #[must_use]
    pub fn client_info(&self) -> &ClientInfo {
        &self.client_info
    }

    /// Returns the client capabilities.
    #[must_use]
    pub fn client_capabilities(&self) -> &ClientCapabilities {
        &self.client_capabilities
    }

    /// Returns the server info.
    #[must_use]
    pub fn server_info(&self) -> &ServerInfo {
        &self.server_info
    }

    /// Returns the server capabilities.
    #[must_use]
    pub fn server_capabilities(&self) -> &ServerCapabilities {
        &self.server_capabilities
    }

    /// Returns the negotiated protocol version.
    #[must_use]
    pub fn protocol_version(&self) -> &str {
        &self.protocol_version
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use fastmcp_protocol::{PromptsCapability, ResourcesCapability, ToolsCapability};

    fn test_session() -> ClientSession {
        ClientSession::new(
            ClientInfo {
                name: "test-client".to_string(),
                version: "1.0.0".to_string(),
            },
            ClientCapabilities::default(),
            ServerInfo {
                name: "test-server".to_string(),
                version: "2.0.0".to_string(),
            },
            ServerCapabilities {
                tools: Some(ToolsCapability { list_changed: true }),
                resources: Some(ResourcesCapability {
                    subscribe: true,
                    list_changed: false,
                }),
                prompts: Some(PromptsCapability {
                    list_changed: false,
                }),
                logging: None,
                tasks: None,
            },
            "2024-11-05".to_string(),
        )
    }

    #[test]
    fn session_client_info() {
        let session = test_session();
        assert_eq!(session.client_info().name, "test-client");
        assert_eq!(session.client_info().version, "1.0.0");
    }

    #[test]
    fn session_client_capabilities() {
        let session = test_session();
        let caps = session.client_capabilities();
        assert!(caps.sampling.is_none());
        assert!(caps.elicitation.is_none());
        assert!(caps.roots.is_none());
    }

    #[test]
    fn session_server_info() {
        let session = test_session();
        assert_eq!(session.server_info().name, "test-server");
        assert_eq!(session.server_info().version, "2.0.0");
    }

    #[test]
    fn session_server_capabilities() {
        let session = test_session();
        let caps = session.server_capabilities();
        assert!(caps.tools.is_some());
        assert!(caps.tools.as_ref().unwrap().list_changed);
        assert!(caps.resources.is_some());
        assert!(caps.resources.as_ref().unwrap().subscribe);
        assert!(!caps.resources.as_ref().unwrap().list_changed);
        assert!(caps.prompts.is_some());
        assert!(caps.logging.is_none());
        assert!(caps.tasks.is_none());
    }

    #[test]
    fn session_protocol_version() {
        let session = test_session();
        assert_eq!(session.protocol_version(), "2024-11-05");
    }

    #[test]
    fn session_with_sampling_capabilities() {
        let session = ClientSession::new(
            ClientInfo {
                name: "sampler".to_string(),
                version: "0.1.0".to_string(),
            },
            ClientCapabilities {
                sampling: Some(fastmcp_protocol::SamplingCapability {}),
                elicitation: None,
                roots: None,
            },
            ServerInfo {
                name: "srv".to_string(),
                version: "1.0.0".to_string(),
            },
            ServerCapabilities::default(),
            "2024-11-05".to_string(),
        );
        assert!(session.client_capabilities().sampling.is_some());
    }

    #[test]
    fn session_with_empty_server_capabilities() {
        let session = ClientSession::new(
            ClientInfo {
                name: "c".to_string(),
                version: "0.1.0".to_string(),
            },
            ClientCapabilities::default(),
            ServerInfo {
                name: "s".to_string(),
                version: "0.1.0".to_string(),
            },
            ServerCapabilities::default(),
            String::new(),
        );
        assert!(session.server_capabilities().tools.is_none());
        assert!(session.server_capabilities().resources.is_none());
        assert!(session.server_capabilities().prompts.is_none());
        assert!(session.server_capabilities().logging.is_none());
        assert!(session.server_capabilities().tasks.is_none());
        assert!(session.protocol_version().is_empty());
    }
}
