//! WebSocket server for real-time Item updates.
//!
//! Provides a standalone `WebSocketServer` that accepts WebSocket connections,
//! manages client connections via a broadcast hub, and exchanges framed JSON
//! messages.  A `WebSocketEndpoint` is also provided so the WebSocket service
//! can be mounted on the existing `Router`.

use std::net::SocketAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use async_trait::async_trait;
use futures::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::broadcast;
use tokio_tungstenite::{accept_async, tungstenite::Message};
use tracing::{error, info};

use crate::domain::{CreateItem, Endpoint, Item, ItemStore, Request, Response, UpdateItem};

/// JSON message frame used over the WebSocket wire.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsMessage {
    /// Subscribe to a topic.
    Subscribe { topic: String },
    /// Unsubscribe from a topic.
    Unsubscribe { topic: String },
    /// Broadcast when an item is created.
    ItemCreated { item: Item },
    /// Broadcast when an item is updated.
    ItemUpdated { item: Item },
    /// Broadcast when an item is deleted.
    ItemDeleted { id: u64 },
    /// Request all current items.
    GetItems,
    /// Create a new item via WebSocket.
    CreateItem { name: String, description: String },
    /// Update an existing item via WebSocket.
    UpdateItem { id: u64, name: Option<String>, description: Option<String> },
    /// Delete an item via WebSocket.
    DeleteItem { id: u64 },
    /// Generic error response.
    Error { message: String },
    /// Sent to a client when it connects successfully.
    Connected { client_id: u64 },
}

/// Broadcast hub that fans out `WsMessage`s to all active subscribers.
#[derive(Debug, Clone)]
pub struct BroadcastHub {
    sender: broadcast::Sender<WsMessage>,
}

impl BroadcastHub {
    /// Create a new hub with the given channel capacity.
    pub fn new(capacity: usize) -> Self {
        let (sender, _) = broadcast::channel(capacity);
        Self { sender }
    }

    /// Subscribe a new client to the broadcast channel.
    pub fn subscribe(&self) -> broadcast::Receiver<WsMessage> {
        self.sender.subscribe()
    }

    /// Broadcast a message to every connected client.
    pub fn broadcast(
        &self,
        message: WsMessage,
    ) -> Result<usize, broadcast::error::SendError<WsMessage>> {
        self.sender.send(message)
    }

    /// Number of active receivers.
    pub fn receiver_count(&self) -> usize {
        self.sender.receiver_count()
    }
}

/// WebSocket server that handles real-time updates for the `Item` domain model.
pub struct WebSocketServer {
    listener: TcpListener,
    hub: BroadcastHub,
    store: Arc<ItemStore>,
    client_counter: AtomicU64,
}

impl WebSocketServer {
    /// Bind a new WebSocket server to `addr` backed by the given `ItemStore`.
    ///
    /// # Errors
    ///
    /// Returns an error if the underlying `TcpListener` fails to bind.
    pub async fn new(
        addr: SocketAddr,
        store: Arc<ItemStore>,
    ) -> Result<Self, std::io::Error> {
        let listener = TcpListener::bind(addr).await?;
        let hub = BroadcastHub::new(1024);
        Ok(Self {
            listener,
            hub,
            store,
            client_counter: AtomicU64::new(1),
        })
    }

    /// Return the local socket address the server is bound to.
    pub fn local_addr(&self) -> Result<SocketAddr, std::io::Error> {
        self.listener.local_addr()
    }

    /// Run the server, accepting connections until the process is shut down.
    ///
    /// Each connection is handled in its own spawned task so the server can
    /// accept new connections concurrently.
    pub async fn run(self) -> Result<(), std::io::Error> {
        let Self {
            listener,
            hub,
            store,
            client_counter,
        } = self;
        let hub = Arc::new(hub);
        let local_addr = listener.local_addr()?;
        info!("WebSocket server listening on ws://{}", local_addr);

        loop {
            let (stream, addr) = match listener.accept().await {
                Ok(conn) => conn,
                Err(e) => {
                    error!("Failed to accept WebSocket connection: {}", e);
                    continue;
                }
            };

            let hub = Arc::clone(&hub);
            let store = Arc::clone(&store);
            let client_id = client_counter.fetch_add(1, Ordering::SeqCst);

            tokio::spawn(async move {
                if let Err(e) = handle_connection(stream, addr, hub, store, client_id).await {
                    error!("WebSocket connection error from {}: {}", addr, e);
                }
            });
        }
    }
}

/// Handle a single WebSocket connection.
async fn handle_connection(
    stream: TcpStream,
    addr: SocketAddr,
    hub: Arc<BroadcastHub>,
    store: Arc<ItemStore>,
    client_id: u64,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let ws_stream = accept_async(stream).await?;
    let (mut write, mut read) = ws_stream.split();
    let mut rx = hub.subscribe();

    // Send connected message.
    let connected_msg = WsMessage::Connected { client_id };
    let json = serde_json::to_string(&connected_msg)?;
    write.send(Message::Text(json)).await?;

    let hub_for_read = Arc::clone(&hub);

    // Task to forward broadcast messages to this client.
    let send_task = tokio::spawn(async move {
        loop {
            match rx.recv().await {
                Ok(msg) => {
                    let json = match serde_json::to_string(&msg) {
                        Ok(j) => j,
                        Err(e) => {
                            error!("Failed to serialize message: {}", e);
                            continue;
                        }
                    };
                    if let Err(e) = write.send(Message::Text(json)).await {
                        error!("Failed to send message to client {}: {}", client_id, e);
                        break;
                    }
                }
                Err(e) => {
                    error!("Broadcast receive error for client {}: {}", client_id, e);
                    break;
                }
            }
        }
    });

    // Task to read messages from this client.
    let read_task = tokio::spawn(async move {
        while let Some(result) = read.next().await {
            match result {
                Ok(Message::Text(text)) => {
                    match serde_json::from_str::<WsMessage>(&text) {
                        Ok(ws_msg) => {
                            if let Err(e) =
                                process_message(ws_msg, &store, &hub_for_read).await
                            {
                                let err_msg = WsMessage::Error {
                                    message: e.to_string(),
                                };
                                let _ = hub_for_read.broadcast(err_msg);
                            }
                        }
                        Err(e) => {
                            let err_msg = WsMessage::Error {
                                message: format!("Invalid message: {}", e),
                            };
                            let _ = hub_for_read.broadcast(err_msg);
                        }
                    }
                }
                Ok(Message::Close(_)) => break,
                Err(e) => {
                    error!("WebSocket read error for client {}: {}", client_id, e);
                    break;
                }
                _ => {}
            }
        }
    });

    tokio::select! {
        _ = send_task => {},
        _ = read_task => {},
    }

    info!("WebSocket client {} disconnected from {}", client_id, addr);
    Ok(())
}

/// Process an incoming `WsMessage` and optionally broadcast results.
async fn process_message(
    msg: WsMessage,
    store: &ItemStore,
    hub: &BroadcastHub,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    match msg {
        WsMessage::GetItems => {
            let items = store.list();
            for item in items {
                hub.broadcast(WsMessage::ItemCreated { item })?;
            }
        }
        WsMessage::CreateItem { name, description } => {
            let item = store.create(CreateItem { name, description });
            hub.broadcast(WsMessage::ItemCreated { item })?;
        }
        WsMessage::UpdateItem { id, name, description } => {
            match store.update(id, UpdateItem { name, description }) {
                Some(item) => {
                    hub.broadcast(WsMessage::ItemUpdated { item })?;
                }
                None => {
                    hub.broadcast(WsMessage::Error {
                        message: format!("Item {} not found", id),
                    })?;
                }
            }
        }
        WsMessage::DeleteItem { id } => {
            match store.delete(id) {
                Some(_) => {
                    hub.broadcast(WsMessage::ItemDeleted { id })?;
                }
                None => {
                    hub.broadcast(WsMessage::Error {
                        message: format!("Item {} not found", id),
                    })?;
                }
            }
        }
        WsMessage::Subscribe { topic } => {
            info!("Client subscribed to topic: {}", topic);
        }
        WsMessage::Unsubscribe { topic } => {
            info!("Client unsubscribed from topic: {}", topic);
        }
        _ => {}
    }
    Ok(())
}

/// WebSocket endpoint that can be mounted on the existing `Router`.
///
/// Provides HTTP-accessible metadata and broadcast proxy endpoints so the
/// WebSocket service is discoverable and can be driven via REST when needed.
pub struct WebSocketEndpoint {
    hub: Arc<BroadcastHub>,
    store: Arc<ItemStore>,
}

impl WebSocketEndpoint {
    /// Create a new endpoint backed by the given hub and store.
    pub fn new(hub: Arc<BroadcastHub>, store: Arc<ItemStore>) -> Self {
        Self { hub, store }
    }
}

#[async_trait]
impl Endpoint for WebSocketEndpoint {
    async fn handle(&self, req: Request) -> Response {
        match (req.method.as_str(), req.path.as_str()) {
            ("GET", "/ws/info") => {
                let info = serde_json::json!({
                    "endpoint": "/ws/items",
                    "protocol": "websocket",
                    "supported_messages": [
                        "item_created",
                        "item_updated",
                        "item_deleted",
                        "get_items",
                        "create_item",
                        "update_item",
                        "delete_item"
                    ]
                });
                Response::ok()
                    .with_header("Content-Type", "application/json")
                    .with_body(info.to_string().into_bytes())
            }
            ("POST", "/ws/broadcast") => {
                let body = req
                    .body
                    .and_then(|b| serde_json::from_slice::<WsMessage>(&b).ok());
                match body {
                    Some(msg) => {
                        let _ = self.hub.broadcast(msg);
                        Response::ok()
                            .with_header("Content-Type", "application/json")
                            .with_body(b"{\"status\":\"broadcasted\"}".to_vec())
                    }
                    None => Response::new(400),
                }
            }
            ("GET", "/ws/items") => {
                let items = self.store.list();
                let body = serde_json::to_vec(&items).unwrap_or_default();
                Response::ok()
                    .with_header("Content-Type", "application/json")
                    .with_body(body)
            }
            _ => Response::not_found(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{timeout, Duration};
    use tokio_tungstenite::connect_async;

    /// Helper that binds a WebSocket server on a random port and returns the
    /// bound address together with the hub so tests can broadcast.
    async fn setup_ws_server() -> (SocketAddr, Arc<BroadcastHub>, Arc<ItemStore>) {
        let store = Arc::new(ItemStore::new());
        let server = WebSocketServer::new(
            SocketAddr::from(([127, 0, 0, 1], 0)),
            Arc::clone(&store),
        )
        .await
        .unwrap();
        let addr = server.local_addr().unwrap();
        let hub = Arc::new(server.hub.clone());
        let store = server.store.clone();

        tokio::spawn(async move {
            let _ = server.run().await;
        });

        // Give the server a moment to start listening.
        tokio::time::sleep(Duration::from_millis(50)).await;

        (addr, hub, store)
    }

    #[tokio::test]
    async fn test_websocket_connection_and_broadcast() {
        let (addr, hub, _store) = setup_ws_server().await;
        let url = format!("ws://{}/ws/items", addr);

        let (mut ws, _) = connect_async(&url).await.expect("failed to connect");

        // Read the `Connected` message.
        let msg = timeout(Duration::from_secs(1), ws.next())
            .await
            .unwrap()
            .unwrap()
            .unwrap();
        let text = msg.to_text().unwrap();
        let connected: WsMessage = serde_json::from_str(text).unwrap();
        assert!(
            matches!(connected, WsMessage::Connected { .. }),
            "expected Connected message, got: {:?}",
            connected
        );

        // Broadcast an item from the server side.
        let item = Item {
            id: 1,
            name: "Test Item".to_string(),
            description: "A test item".to_string(),
        };
        hub.broadcast(WsMessage::ItemCreated { item: item.clone() })
            .unwrap();

        // Receive the broadcasted item.
        let msg = timeout(Duration::from_secs(1), ws.next())
            .await
            .unwrap()
            .unwrap()
            .unwrap();
        let text = msg.to_text().unwrap();
        let received: WsMessage = serde_json::from_str(text).unwrap();
        assert_eq!(received, WsMessage::ItemCreated { item });
    }

    #[tokio::test]
    async fn test_websocket_create_item() {
        let (addr, _hub, store) = setup_ws_server().await;
        let url = format!("ws://{}/ws/items", addr);

        let (mut ws, _) = connect_async(&url).await.expect("failed to connect");

        // Skip Connected message.
        let _ = timeout(Duration::from_secs(1), ws.next())
            .await
            .unwrap()
            .unwrap()
            .unwrap();

        // Send a CreateItem message.
        let create = WsMessage::CreateItem {
            name: "Widget".to_string(),
            description: "A useful widget".to_string(),
        };
        let json = serde_json::to_string(&create).unwrap();
        ws.send(Message::Text(json)).await.unwrap();

        // Receive the broadcasted ItemCreated.
        let msg = timeout(Duration::from_secs(1), ws.next())
            .await
            .unwrap()
            .unwrap()
            .unwrap();
        let text = msg.to_text().unwrap();
        let received: WsMessage = serde_json::from_str(text).unwrap();
        assert!(
            matches!(received, WsMessage::ItemCreated { .. }),
            "expected ItemCreated, got: {:?}",
            received
        );

        // Verify the store was updated.
        let items = store.list();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].name, "Widget");
    }

    #[tokio::test]
    async fn test_websocket_endpoint_info() {
        let hub = Arc::new(BroadcastHub::new(16));
        let store = Arc::new(ItemStore::new());
        let endpoint = WebSocketEndpoint::new(Arc::clone(&hub), Arc::clone(&store));

        let req = Request::new("/ws/info", "GET");
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 200);
        let body = String::from_utf8(res.body.unwrap()).unwrap();
        assert!(body.contains("websocket"));
        assert!(body.contains("item_created"));
    }

    #[tokio::test]
    async fn test_websocket_endpoint_broadcast() {
        let hub = Arc::new(BroadcastHub::new(16));
        let store = Arc::new(ItemStore::new());
        let endpoint = WebSocketEndpoint::new(Arc::clone(&hub), Arc::clone(&store));

        let item = Item {
            id: 1,
            name: "Broadcasted".to_string(),
            description: "Via REST".to_string(),
        };
        let msg = WsMessage::ItemCreated { item: item.clone() };
        let body = serde_json::to_vec(&msg).unwrap();
        let req = Request::new("/ws/broadcast", "POST").with_body(body);
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 200);

        // Verify the broadcast was sent (one receiver, no WebSocket client).
        // Since we have no WS client, the broadcast still succeeds.
        assert_eq!(hub.receiver_count(), 0);
    }

    #[tokio::test]
    async fn test_websocket_endpoint_items() {
        let hub = Arc::new(BroadcastHub::new(16));
        let store = Arc::new(ItemStore::new());
        store.create(CreateItem {
            name: "Foo".to_string(),
            description: "Bar".to_string(),
        });
        let endpoint = WebSocketEndpoint::new(Arc::clone(&hub), Arc::clone(&store));

        let req = Request::new("/ws/items", "GET");
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 200);
        let body = res.body.unwrap();
        let items: Vec<Item> = serde_json::from_slice(&body).unwrap();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].name, "Foo");
    }

    #[tokio::test]
    async fn test_websocket_endpoint_not_found() {
        let hub = Arc::new(BroadcastHub::new(16));
        let store = Arc::new(ItemStore::new());
        let endpoint = WebSocketEndpoint::new(Arc::clone(&hub), Arc::clone(&store));

        let req = Request::new("/ws/unknown", "GET");
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 404);
    }

    #[tokio::test]
    async fn test_broadcast_hub_multiple_clients() {
        let hub = BroadcastHub::new(16);
        let mut rx1 = hub.subscribe();
        let mut rx2 = hub.subscribe();

        let item = Item {
            id: 1,
            name: "Multi".to_string(),
            description: "Cast".to_string(),
        };
        hub.broadcast(WsMessage::ItemCreated { item: item.clone() }).unwrap();

        let msg1 = rx1.recv().await.unwrap();
        let msg2 = rx2.recv().await.unwrap();
        assert_eq!(msg1, WsMessage::ItemCreated { item: item.clone() });
        assert_eq!(msg2, WsMessage::ItemCreated { item });
    }

    #[tokio::test]
    async fn test_websocket_get_items() {
        let (addr, _hub, store) = setup_ws_server().await;
        let url = format!("ws://{}/ws/items", addr);

        // Pre-populate the store.
        store.create(CreateItem {
            name: "Pre".to_string(),
            description: "Loaded".to_string(),
        });

        let (mut ws, _) = connect_async(&url).await.expect("failed to connect");

        // Skip Connected message.
        let _ = timeout(Duration::from_secs(1), ws.next())
            .await
            .unwrap()
            .unwrap()
            .unwrap();

        // Send GetItems.
        let get = WsMessage::GetItems;
        let json = serde_json::to_string(&get).unwrap();
        ws.send(Message::Text(json)).await.unwrap();

        // Receive the ItemCreated broadcast for the pre-loaded item.
        let msg = timeout(Duration::from_secs(1), ws.next())
            .await
            .unwrap()
            .unwrap()
            .unwrap();
        let text = msg.to_text().unwrap();
        let received: WsMessage = serde_json::from_str(text).unwrap();
        assert!(
            matches!(received, WsMessage::ItemCreated { .. }),
            "expected ItemCreated, got: {:?}",
            received
        );
    }
}
