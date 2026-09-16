# ADR-012: API Design Principles

**Document ID:** BYTEPORT_ADR_012  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort provides client and server APIs for Rust applications. The API must be:
1. Ergonomic and easy to use correctly
2. Async-first for high performance
3. Type-safe with compile-time guarantees
4. Backward compatible across versions

## Decision

We adopt a **fluent builder pattern with async/await**:

### Client API

```rust
pub struct Client {
    config: ClientConfig,
    transport: Arc<dyn Transport>,
    encoder_registry: Arc<EncoderRegistry>,
    compression_registry: Arc<CompressionRegistry>,
    connection_pool: Arc<ConnectionPool>,
    schema_registry: Arc<SchemaRegistry>,
    metrics: Arc<BytePortMetrics>,
}

impl Client {
    pub async fn new(config: ClientConfig) -> Result<Self, ClientError> {
        let transport = create_transport(config.transport)?;
        
        Ok(Self {
            config,
            transport: Arc::new(transport),
            encoder_registry: Arc::new(EncoderRegistry::default()),
            compression_registry: Arc::new(CompressionRegistry::default()),
            connection_pool: Arc::new(ConnectionPool::new()),
            schema_registry: Arc::new(SchemaRegistry::new()),
            metrics: BytePortMetrics::new(),
        })
    }
    
    pub async fn request<T: Message, R: Message>(&self, message: T) -> Result<R, ClientError> {
        let start = Instant::now();
        let mut retries = 0;
        
        loop {
            match self.try_request::<T, R>(&message).await {
                Ok(response) => {
                    self.metrics.record_request(start.elapsed());
                    return Ok(response);
                }
                Err(e) if e.is_retryable() && retries < self.config.max_retries => {
                    retries += 1;
                    let delay = self.config.retry_backoff * 2u32.pow(retries - 1);
                    tokio::time::sleep(delay).await;
                }
                Err(e) => {
                    self.metrics.record_error("request_failed");
                    return Err(e);
                }
            }
        }
    }
    
    async fn try_request<T: Message, R: Message>(&self, message: &T) -> Result<R, ClientError> {
        // Get schema
        let schema = self.schema_registry.latest(T::schema_id())
            .ok_or(ClientError::SchemaNotFound(T::schema_id()))?;
        
        // Validate message
        message.validate(schema)?;
        
        // Encode
        let encoder = self.encoder_registry.get(self.config.default_encoder)
            .ok_or(ClientError::EncoderNotFound(self.config.default_encoder))?;
        let encoded = encoder.encode(message)?;
        
        // Compress (if enabled)
        let (payload, comp_id) = if let Some(comp_id) = self.config.compression {
            let compressor = self.compression_registry.get(comp_id)
                .ok_or(ClientError::CompressionNotFound(comp_id))?;
            let compressed = compressor.compress(&encoded)?;
            (compressed, comp_id)
        } else {
            (Bytes::from(encoded), CompressionId::None)
        };
        
        // Build frame
        let frame = FrameBuilder::new(T::schema_id())
            .encoder(self.config.default_encoder)
            .compression(comp_id)
            .request()
            .payload(payload)
            .build()?;
        
        // Send and receive
        let mut conn = self.connection_pool.get(
            &self.config.server_address,
            self.transport.as_ref(),
        ).await?;
        conn.send(&frame).await?;
        let response_frame = conn.receive().await?;
        
        // Parse response
        self.parse_response::<R>(response_frame).await
    }
}
```

### Server API

```rust
pub struct Server {
    config: ServerConfig,
    transport: Arc<dyn Transport>,
    handler_registry: HandlerRegistry,
    schema_registry: Arc<SchemaRegistry>,
    encoder_registry: Arc<EncoderRegistry>,
    compression_registry: Arc<CompressionRegistry>,
    metrics: Arc<BytePortMetrics>,
}

impl Server {
    pub async fn new(config: ServerConfig) -> Result<Self, ServerError> {
        let transport = create_transport(config.transport)?;
        
        Ok(Self {
            config,
            transport: Arc::new(transport),
            handler_registry: HandlerRegistry::new(),
            schema_registry: Arc::new(SchemaRegistry::new()),
            encoder_registry: Arc::new(EncoderRegistry::default()),
            compression_registry: Arc::new(CompressionRegistry::default()),
            metrics: BytePortMetrics::new(),
        })
    }
    
    pub fn register_handler<T: Message, R: Message>(
        &mut self,
        handler: impl MessageHandler<T, R> + 'static,
    ) {
        self.handler_registry.register(T::schema_id(), Box::new(handler));
    }
    
    pub async fn run(self) -> Result<(), ServerError> {
        let listener = self.transport.listen(&self.config.listen_address).await?;
        tracing::info!("Server listening on {}", self.config.listen_address);
        
        loop {
            let conn = listener.accept().await?;
            let server = self.clone();
            tokio::spawn(async move {
                if let Err(e) = server.handle_connection(conn).await {
                    tracing::error!(error = %e, "Connection error");
                }
            });
        }
    }
    
    async fn handle_connection(&self, mut conn: Connection) -> Result<(), ServerError> {
        let mut parser = FrameParser::new();
        
        loop {
            let data = conn.receive().await?;
            let frame = match parser.parse(data)? {
                Some(frame) => frame,
                None => continue,
            };
            
            let start = Instant::now();
            let response = self.process_frame(frame).await?;
            conn.send(&response).await?;
            self.metrics.record_request(start.elapsed());
        }
    }
    
    async fn process_frame(&self, frame: Frame) -> Result<Bytes, ServerError> {
        let handler = self.handler_registry.get(frame.header.schema_id)
            .ok_or(ServerError::NoHandler(frame.header.schema_id))?;
        
        // Decompress if needed
        let payload = if frame.header.flags.contains(FrameFlags::COMPRESSED) {
            let compressor = self.compression_registry.get(frame.header.compression_id)
                .ok_or(ServerError::CompressionNotFound(frame.header.compression_id))?;
            compressor.decompress(&frame.payload)?
        } else {
            frame.payload
        };
        
        // Decode
        let encoder = self.encoder_registry.get(frame.header.encoder_id)
            .ok_or(ServerError::EncoderNotFound(frame.header.encoder_id))?;
        let schema = self.schema_registry.latest(frame.header.schema_id)
            .ok_or(ServerError::SchemaNotFound(frame.header.schema_id))?;
        let message = encoder.decode(payload, schema)?;
        
        // Process
        let response = handler.handle(message).await?;
        
        // Encode response
        let response_payload = encoder.encode(response.as_ref())?;
        
        // Build response frame
        FrameBuilder::new(response.schema_id())
            .encoder(frame.header.encoder_id)
            .compression(frame.header.compression_id)
            .response()
            .payload(response_payload)
            .build()
            .map_err(ServerError::Frame)
    }
}
```

### Message Handler Trait

```rust
#[async_trait]
pub trait MessageHandler<T: Message, R: Message>: Send + Sync {
    async fn handle(&self, message: T) -> Result<R, HandlerError>;
}

// Example usage
pub struct UserEventHandler {
    db: Database,
}

#[async_trait]
impl MessageHandler<UserEvent, AckResponse> for UserEventHandler {
    async fn handle(&self, message: UserEvent) -> Result<AckResponse, HandlerError> {
        self.db.insert_event(&message).await
            .map_err(HandlerError::Database)?;
        
        Ok(AckResponse {
            status: AckStatus::Ok,
            message_id: message.id,
            timestamp: SystemTime::now(),
        })
    }
}
```

## Consequences

**Positive:**
- Fluent API is intuitive and self-documenting
- Async/await matches Rust idioms
- Generic message types provide type safety
- Clear separation between client and server

**Negative:**
- Builder pattern adds verbosity
- Async trait objects have complexity
- Error handling across async boundaries

---

*End of ADR-012*
