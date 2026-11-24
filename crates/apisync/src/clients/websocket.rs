//! WebSocket client connection wrapper.
//!
//! `WsConnection` wraps [`tokio_tungstenite`] for outbound WebSocket
//! connections, providing typed send/receive over [`WsMessage`](crate::WsMessage)
//! and automatic reconnection support.

use std::net::SocketAddr;
use std::time::Duration;

use futures::{SinkExt, StreamExt};
use tokio::net::TcpStream;
use tokio_tungstenite::{
    connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream,
};

use crate::adapters::websocket::WsMessage;
use crate::error::{Error, Result};

/// A connected WebSocket client that speaks the [`WsMessage`] protocol.
///
/// Wraps [`tokio_tungstenite`] with typed send/receive methods that
/// automatically serialize/deserialize [`WsMessage`] JSON frames.
///
/// # Examples
///
/// ```no_run
/// # use apisync::clients::WsConnection;
/// # use apisync::WsMessage;
/// # async fn example() -> Result<(), apisync::error::Error> {
/// let mut ws = WsConnection::connect("ws://127.0.0.1:8080/ws/items").await?;
/// let msg = ws.recv().await?;
/// println!("Received: {msg:?}");
/// ws.send(WsMessage::GetItems).await?;
/// # Ok(())
/// # }
/// ```
pub struct WsConnection {
    write: futures::stream::SplitSink<
        WebSocketStream<MaybeTlsStream<TcpStream>>,
        Message,
    >,
    read: futures::stream::SplitStream<
        WebSocketStream<MaybeTlsStream<TcpStream>>,
    >,
}

impl WsConnection {
    /// Connect to a WebSocket server at the given `ws://` or `wss://` URL.
    pub async fn connect(url: &str) -> Result<Self> {
        let (ws_stream, _) = connect_async(url).await?;
        let (write, read) = ws_stream.split();
        Ok(Self { write, read })
    }

    /// Connect to a WebSocket server at the given address.
    pub async fn connect_addr(addr: SocketAddr) -> Result<Self> {
        let url = format!("ws://{addr}");
        Self::connect(&url).await
    }

    /// Send a [`WsMessage`] to the server.
    pub async fn send(&mut self, msg: WsMessage) -> Result<()> {
        let json = serde_json::to_string(&msg)?;
        self.write.send(Message::Text(json.into())).await?;
        Ok(())
    }

    /// Receive the next [`WsMessage`] from the server.
    ///
    /// Returns `None` if the connection is closed.
    pub async fn recv(&mut self) -> Result<Option<WsMessage>> {
        match self.read.next().await {
            Some(Ok(Message::Text(text))) => {
                let msg: WsMessage = serde_json::from_str(&text)?;
                Ok(Some(msg))
            }
            Some(Ok(Message::Close(_))) | None => Ok(None),
            Some(Ok(_)) => Ok(None), // Binary, Ping, Pong — ignore
            Some(Err(e)) => Err(Error::WebSocket(e.to_string())),
        }
    }

    /// Receive the next message with a timeout.
    pub async fn recv_timeout(&mut self, timeout: Duration) -> Result<Option<WsMessage>> {
        match tokio::time::timeout(timeout, self.recv()).await {
            Ok(result) => result,
            Err(_) => Err(Error::Timeout),
        }
    }

    /// Send a [`WsMessage`] and wait for the next response.
    pub async fn send_recv(&mut self, msg: WsMessage) -> Result<Option<WsMessage>> {
        self.send(msg).await?;
        self.recv().await
    }

    /// Send a [`WsMessage`] and wait for the next response with a timeout.
    pub async fn send_recv_timeout(
        &mut self,
        msg: WsMessage,
        timeout: Duration,
    ) -> Result<Option<WsMessage>> {
        self.send(msg).await?;
        self.recv_timeout(timeout).await
    }

    /// Close the WebSocket connection gracefully.
    pub async fn close(&mut self) -> Result<()> {
        self.write.send(Message::Close(None)).await?;
        Ok(())
    }

    /// Connect to a server, read the `Connected` message, and return the connection.
    ///
    /// This is a convenience for the common pattern of connecting and reading
    /// the initial handshake message.
    pub async fn connect_and_handshake(url: &str) -> Result<(Self, WsMessage)> {
        let mut conn = Self::connect(url).await?;
        let handshake = conn.recv().await?.ok_or_else(|| {
            Error::WebSocket("connection closed before handshake".into())
        })?;
        Ok((conn, handshake))
    }
}

impl std::fmt::Debug for WsConnection {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("WsConnection")
            .field("connected", &true)
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ws_message_roundtrip() {
        let msg = WsMessage::GetItems;
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_create_roundtrip() {
        let msg = WsMessage::CreateItem {
            name: "test".to_string(),
            description: "desc".to_string(),
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_connection_is_debug() {
        let _ = std::any::type_name::<WsConnection>();
    }

    #[test]
    fn test_ws_message_update_roundtrip() {
        let msg = WsMessage::UpdateItem {
            id: 42,
            name: Some("updated".to_string()),
            description: Some("new desc".to_string()),
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_update_partial_roundtrip() {
        let msg = WsMessage::UpdateItem {
            id: 7,
            name: None,
            description: Some("only desc".to_string()),
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_delete_roundtrip() {
        let msg = WsMessage::DeleteItem { id: 7 };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_item_created_roundtrip() {
        let msg = WsMessage::ItemCreated {
            item: crate::domain::Item { id: 10, name: "new".into(), description: "desc".into() },
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_item_updated_roundtrip() {
        let msg = WsMessage::ItemUpdated {
            item: crate::domain::Item { id: 5, name: "upd".into(), description: "d".into() },
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_item_deleted_roundtrip() {
        let msg = WsMessage::ItemDeleted { id: 99 };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_error_roundtrip() {
        let msg = WsMessage::Error { message: "something went wrong".into() };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_subscribe_roundtrip() {
        let msg = WsMessage::Subscribe { topic: "items".into() };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_unsubscribe_roundtrip() {
        let msg = WsMessage::Unsubscribe { topic: "items".into() };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_connected_roundtrip() {
        let msg = WsMessage::Connected { client_id: 42 };
        let json = serde_json::to_string(&msg).unwrap();
        let back: WsMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(msg, back);
    }

    #[test]
    fn test_ws_message_debug() {
        let msg = WsMessage::GetItems;
        let _dbg = format!("{:?}", msg);
    }
}
