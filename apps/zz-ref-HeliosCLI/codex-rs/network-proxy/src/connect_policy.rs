use crate::policy::is_non_public_ip;
use crate::state::NetworkProxyState;
use rama_core::Layer;
use rama_core::Service;
use rama_dns::client::DnsConnectorLayer;
use rama_error::BoxError;
use rama_error::ErrorExt as _;
use rama_net::address::ProxyAddress;
use rama_net::client::EstablishedClientConnection;
use rama_tcp::TcpStream;
use rama_tcp::client::TcpStreamConnector;
use rama_tcp::client::service::TcpConnector;
use std::io;
use std::net::SocketAddr;
use std::sync::Arc;

#[derive(Clone)]
pub(crate) struct TargetCheckedTcpConnector {
    policy: TargetPolicy,
}

impl TargetCheckedTcpConnector {
    pub(crate) fn new(state: Arc<NetworkProxyState>) -> Self {
        Self {
            policy: TargetPolicy::State(state),
        }
    }

    pub(crate) fn from_allow_local_binding(allow_local_binding: bool) -> Self {
        Self {
            policy: TargetPolicy::Config {
                allow_local_binding,
            },
        }
    }
}

impl<Input> Service<Input> for TargetCheckedTcpConnector
where
    Input: Send
        + 'static
        + rama_core::extensions::ExtensionsRef
        + rama_net::AuthorityInputExt
        + rama_net::ProtocolInputExt
        + rama_net::TransportProtocolInputExt,
{
    type Output = EstablishedClientConnection<TcpStream, Input>;
    type Error = BoxError;

    async fn serve(&self, input: Input) -> Result<Self::Output, Self::Error> {
        // rama 0.3 removed domain-name resolution from `TcpConnector` itself:
        // the transport now only accepts an IP target and expects an upstream
        // connector layer to stamp a resolved `ConnectorTargetStream` into the
        // extensions. Without this layer every non-IP target fails with
        // "tcp connector target host is not an IP address".
        //
        // `DnsConnectorLayer::new()` uses the process-global resolver, which
        // defaults to the platform-native one (Windows DNS API on Windows).
        // The `hickory` feature is deliberately left off so no advisory-bearing
        // DNS client is linked in.
        //
        // When an upstream proxy is configured, the TCP connection is dialed to
        // the proxy, not to the request target, so the socket-level guard below
        // would otherwise classify the *proxy* address and reject the common
        // local-proxy setup (`HTTP_PROXY=http://127.0.0.1:...`) for every
        // operator that leaves `allow_local_binding` off, which is the default.
        // The exemption is safe because the two properties the guard defends
        // are still upheld elsewhere:
        //
        //  * target authorization happens before dialing, on the target host
        //    itself, in `network_policy::evaluate_host_policy` ->
        //    `NetworkProxyState::host_blocked`, which classifies local/private
        //    literals and rejects allowlisted hostnames that resolve to
        //    non-public IPs; and
        //  * the proxy address is operator configuration (`HTTP_PROXY`,
        //    `HTTPS_PROXY`, `ALL_PROXY`, or the managed `proxy_for_connect`
        //    path, itself gated on `allow_upstream_proxy`), never request data.
        //
        // `proxy_connector_exempts_socket_target_guard_for_configured_proxy`
        // pins this behavior: it is intentional, not an oversight.
        if input.extensions().get_ref::<ProxyAddress>().is_some() {
            return DnsConnectorLayer::new()
                .into_layer(TcpConnector::new())
                .serve(input)
                .await;
        }

        DnsConnectorLayer::new()
            .into_layer(
                TcpConnector::new().with_connector(TargetCheckedStreamConnector {
                    policy: self.policy.clone(),
                }),
            )
            .serve(input)
            .await
    }
}

#[derive(Clone)]
struct TargetCheckedStreamConnector {
    policy: TargetPolicy,
}

impl TcpStreamConnector for TargetCheckedStreamConnector {
    type Error = BoxError;

    async fn connect(&self, addr: SocketAddr) -> Result<TcpStream, Self::Error> {
        if !self.policy.allow_local_binding().await? && is_non_public_ip(addr.ip()) {
            return Err(io::Error::new(
                io::ErrorKind::PermissionDenied,
                "network target rejected by policy",
            )
            .into());
        }

        tokio::net::TcpStream::connect(addr)
            .await
            .map(TcpStream::from)
            .map_err(Into::into)
    }
}

#[derive(Clone)]
enum TargetPolicy {
    Config { allow_local_binding: bool },
    State(Arc<NetworkProxyState>),
}

impl TargetPolicy {
    async fn allow_local_binding(&self) -> Result<bool, BoxError> {
        match self {
            Self::Config {
                allow_local_binding,
            } => Ok(*allow_local_binding),
            Self::State(state) => state
                .allow_local_binding()
                .await
                .map_err(|err| BoxError::from(err).context("read network proxy config")),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::NetworkProxySettings;
    use crate::state::network_proxy_state_for_policy;
    use rama_net::address::HostWithPort;
    use std::net::Ipv4Addr;
    use tokio::net::TcpListener;

    #[tokio::test(flavor = "current_thread")]
    async fn direct_connector_rejects_non_public_target_when_local_binding_disabled() {
        let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0))
            .await
            .expect("bind local listener");
        let target = listener.local_addr().expect("local addr");
        let connector = TargetCheckedTcpConnector::new(Arc::new(network_proxy_state_for_policy(
            NetworkProxySettings::default(),
        )));

        let request: rama_net::client::Request =
            rama_net::client::Request::new(HostWithPort::from(target));
        let err = Service::serve(&connector, request)
            .await
            .expect_err("local target should be rejected");

        assert!(
            format!("{err:?}").contains("network target rejected by policy"),
            "unexpected error: {err:?}"
        );
    }

    #[tokio::test(flavor = "current_thread")]
    async fn direct_connector_allows_non_public_target_when_local_binding_enabled() {
        let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0))
            .await
            .expect("bind local listener");
        let target = listener.local_addr().expect("local addr");
        let connector = TargetCheckedTcpConnector::new(Arc::new(network_proxy_state_for_policy(
            NetworkProxySettings {
                allow_local_binding: true,
                ..NetworkProxySettings::default()
            },
        )));

        let request: rama_net::client::Request =
            rama_net::client::Request::new(HostWithPort::from(target));
        let result = Service::serve(&connector, request).await;

        assert!(result.is_ok(), "local target should be allowed: {result:?}");
    }

    #[tokio::test(flavor = "current_thread")]
    async fn proxy_connector_exempts_socket_target_guard_for_configured_proxy() {
        // With an upstream proxy configured the dialed socket is the proxy, so
        // `TargetCheckedTcpConnector::serve` deliberately skips the
        // `allow_local_binding` guard for it; see the comment there. The target
        // itself is authorized earlier by
        // `network_policy::evaluate_host_policy`. Without the exemption this
        // call would be rejected as a non-public target even though
        // `allow_local_binding` is left at its default of `false`.
        let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0))
            .await
            .expect("bind local proxy listener");
        let proxy_addr = listener.local_addr().expect("proxy local addr");
        let connector = TargetCheckedTcpConnector::new(Arc::new(network_proxy_state_for_policy(
            NetworkProxySettings::default(),
        )));

        let proxy = ProxyAddress::try_from(format!("http://{proxy_addr}").as_str())
            .expect("proxy address should parse");
        let request: rama_net::client::Request =
            rama_net::client::Request::new(HostWithPort::from(proxy_addr));
        request.extensions.insert(proxy);

        let result = Service::serve(&connector, request).await;

        assert!(
            result.is_ok(),
            "loopback proxy should stay reachable without allow_local_binding: {result:?}"
        );
    }
}
