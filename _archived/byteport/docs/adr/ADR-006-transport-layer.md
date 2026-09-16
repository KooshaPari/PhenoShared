# ADR-006: Transport Layer Architecture

**Document ID:** BYTEPORT_ADR_006  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort must support diverse networking requirements across different deployment scenarios:
- Local IPC (Unix domain sockets)
- Datacenter communication (TCP)
- Low-latency applications (QUIC)
- Edge/IoT deployments (UDP)
- Web clients (WebSocket)

We need a unified transport abstraction that enables runtime selection and consistent API across transport types.

## Decision

We adopt a **trait-based transport abstraction with pluggable implementations**:

```rust
#[async_trait]
pub trait Transport: Send + Sync + 'static {
    fn id(&self) -> TransportId;
    
    async fn connect(&self, addr: &SocketAddr) -> Result<Connection, TransportError>;
    async fn listen(&self, addr: &SocketAddr) -> Result<Listener, TransportError>;
    
    fn address_families(&self) -> &[AddressFamily];
    fn capabilities(&self) -> TransportCapabilities;
}

#[derive(Debug, Clone, Copy)]
pub struct TransportCapabilities {
    pub multiplexing: bool,
    pub flow_control: bool,
    pub ordered_delivery: bool,
    pub reliable_delivery: bool,
    pub congestion_control: bool,
}

pub enum AddressFamily {
    Ipv4,
    Ipv6,
    Unix,
}

pub struct Connection {
    reader: Box<dyn AsyncRead + Send + Unpin>,
    writer: Box<dyn AsyncWrite + Send + Unpin>,
    local_addr: SocketAddr,
    peer_addr: SocketAddr,
}

pub struct Listener {
    inner: Box<dyn AsyncAccept + Send + Unpin>,
    local_addr: SocketAddr,
}
```

## Supported Transports

| Transport | Latency | Throughput | Multiplexing | Reliability | Use Case |
|-----------|---------|------------|--------------|-------------|----------|
| TCP | ~45μs | 10 Gbps | No | Yes | General |
| QUIC | ~65μs | 10 Gbps | Yes | Yes | Low-latency |
| UDP | ~15μs | 20 Gbps | No | No | Real-time |
| Unix Socket | ~5μs | 50 Gbps | No | Yes | IPC |
| WebSocket | ~120μs | 5 Gbps | Via TLS | Yes | Web clients |

## TCP Implementation

```rust
pub struct TcpTransport {
    config: TcpConfig,
}

pub struct TcpConfig {
    pub nodelay: bool,
    pub keepalive: Option<Duration>,
    pub send_buffer_size: Option<usize>,
    pub recv_buffer_size: Option<usize>,
    pub connect_timeout: Duration,
}

#[async_trait]
impl Transport for TcpTransport {
    fn id(&self) -> TransportId { TransportId::Tcp }
    
    async fn connect(&self, addr: &SocketAddr) -> Result<Connection, TransportError> {
        let socket = tokio::time::timeout(
            self.config.connect_timeout,
            tokio::net::TcpStream::connect(addr),
        ).await.map_err(|_| TransportError::ConnectTimeout)??;
        
        socket.set_nodelay(self.config.nodelay)?;
        
        if let Some(keepalive) = self.config.keepalive {
            socket.set_keepalive(Some(keepalive))?;
        }
        
        if let Some(size) = self.config.send_buffer_size {
            socket.set_send_buffer_size(size)?;
        }
        
        if let Some(size) = self.config.recv_buffer_size {
            socket.set_recv_buffer_size(size)?;
        }
        
        let local_addr = socket.local_addr()?;
        let peer_addr = socket.peer_addr()?;
        let (reader, writer) = socket.into_split();
        
        Ok(Connection::new(
            Box::new(reader),
            Box::new(writer),
            local_addr,
            peer_addr,
        ))
    }
    
    async fn listen(&self, addr: &SocketAddr) -> Result<Listener, TransportError> {
        let listener = tokio::net::TcpListener::bind(addr).await?;
        Ok(Listener::new(listener, *addr))
    }
    
    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            multiplexing: false,
            flow_control: true,
            ordered_delivery: true,
            reliable_delivery: true,
            congestion_control: true,
        }
    }
}
```

## QUIC Implementation

```rust
pub struct QuicTransport {
    endpoint: quinn::Endpoint,
    config: QuicConfig,
}

pub struct QuicConfig {
    pub max_concurrent_bidi_streams: u64,
    pub max_concurrent_uni_streams: u64,
    pub stream_receive_window: u64,
    pub receive_window: u64,
    pub send_window: u64,
    pub max_idle_timeout: Duration,
    pub keep_alive_interval: Duration,
}

#[async_trait]
impl Transport for QuicTransport {
    fn id(&self) -> TransportId { TransportId::Quic }
    
    async fn connect(&self, addr: &SocketAddr) -> Result<Connection, TransportError> {
        let connection = self.endpoint
            .connect(*addr, "byteport.local")?
            .await
            .map_err(TransportError::Quic)?;
        
        let (reader, writer) = connection.accept_bidirectional().await?;
        
        Ok(Connection::new(
            Box::new(reader),
            Box::new(writer),
            connection.local_addr()?,
            connection.peer_addr()?,
        ))
    }
    
    async fn listen(&self, addr: &SocketAddr) -> Result<Listener, TransportError> {
        let listener = self.endpoint.bind(addr).await?;
        Ok(Listener::new(listener, *addr))
    }
    
    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            multiplexing: true,
            flow_control: true,
            ordered_delivery: true,
            reliable_delivery: true,
            congestion_control: true,
        }
    }
}
```

## Connection Pooling

```rust
pub struct ConnectionPool {
    inner: RwLock<HashMap<SocketAddr, Vec<PooledConnection>>>,
    config: ConnectionPoolConfig,
}

struct PooledConnection {
    connection: Connection,
    created_at: Instant,
    last_used: Instant,
    use_count: u64,
}

impl ConnectionPool {
    pub async fn get(&self, addr: &SocketAddr, transport: &dyn Transport) 
        -> Result<Connection, TransportError> 
    {
        // Try to acquire existing connection
        let mut pool = self.inner.write().await;
        if let Some(conns) = pool.get_mut(addr) {
            while let Some(pooled) = conns.pop() {
                if pooled.is_expired(&self.config) {
                    continue;
                }
                if self.health_check(&pooled.connection).await {
                    return Ok(pooled.into_connection());
                }
            }
        }
        
        // Create new connection
        let conn = transport.connect(addr).await?;
        Ok(conn)
    }
    
    pub async fn release(&self, addr: SocketAddr, conn: Connection) {
        let mut pool = self.inner.write().await;
        let conns = pool.entry(addr).or_default();
        
        if conns.len() < self.config.max_connections_per_host {
            conns.push(PooledConnection::new(conn));
        }
    }
}
```

## Consequences

**Positive:**
- Single API across all transport types
- Runtime transport selection
- Connection pooling for efficiency
- Consistent error handling

**Negative:**
- Trait object indirection overhead
- Connection pooling complexity
- QUIC support requires additional dependencies

---

*End of ADR-006*
