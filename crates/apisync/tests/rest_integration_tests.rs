//! REST adapter integration tests
//!
//! These tests start a real HTTP server, send HTTP requests via reqwest,
//! and verify responses for all CRUD operations on the `Item` domain model.

use std::net::SocketAddr;
use std::sync::Arc;

use apisync::adapters::rest::HyperServer;
use apisync::domain::{CreateItem, Item, UpdateItem};
use apisync::endpoints::ItemCrudEndpoint;

/// Start a `HyperServer` on a random available port and return the bound
/// address so tests can connect to it.
async fn setup_server() -> SocketAddr {
    let endpoint = Arc::new(ItemCrudEndpoint::new());
    let server = HyperServer::new("127.0.0.1:0".parse().unwrap(), endpoint)
        .await
        .expect("failed to bind server");
    let addr = server.local_addr().unwrap();
    tokio::spawn(async move {
        let _ = server.run().await;
    });
    addr
}

#[tokio::test]
async fn test_list_items_empty() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    let response = client.get(format!("http://{addr}/items")).send().await.unwrap();

    assert_eq!(response.status(), 200);
    let items: Vec<Item> = response.json().await.unwrap();
    assert!(items.is_empty());
}

#[tokio::test]
async fn test_create_item() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    let response = client
        .post(format!("http://{addr}/items"))
        .json(&CreateItem { name: "Test Item".to_string(), description: "A test item".to_string() })
        .send()
        .await
        .unwrap();

    assert_eq!(response.status(), 201);
    let item: Item = response.json().await.unwrap();
    assert_eq!(item.id, 1);
    assert_eq!(item.name, "Test Item");
    assert_eq!(item.description, "A test item");
}

#[tokio::test]
async fn test_get_item() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    // Create an item first
    let create_response = client
        .post(format!("http://{addr}/items"))
        .json(&CreateItem {
            name: "Get Me".to_string(),
            description: "An item to retrieve".to_string(),
        })
        .send()
        .await
        .unwrap();
    assert_eq!(create_response.status(), 201);
    let created: Item = create_response.json().await.unwrap();

    // Retrieve the item
    let response = client.get(format!("http://{addr}/items/{}", created.id)).send().await.unwrap();

    assert_eq!(response.status(), 200);
    let item: Item = response.json().await.unwrap();
    assert_eq!(item, created);
}

#[tokio::test]
async fn test_get_item_not_found() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    let response = client.get(format!("http://{addr}/items/999")).send().await.unwrap();

    assert_eq!(response.status(), 404);
}

#[tokio::test]
async fn test_update_item() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    // Create an item first
    let create_response = client
        .post(format!("http://{addr}/items"))
        .json(&CreateItem {
            name: "Old Name".to_string(),
            description: "Old description".to_string(),
        })
        .send()
        .await
        .unwrap();
    let created: Item = create_response.json().await.unwrap();

    // Update the item
    let response = client
        .put(format!("http://{addr}/items/{}", created.id))
        .json(&UpdateItem {
            name: Some("New Name".to_string()),
            description: Some("New description".to_string()),
        })
        .send()
        .await
        .unwrap();

    assert_eq!(response.status(), 200);
    let item: Item = response.json().await.unwrap();
    assert_eq!(item.id, created.id);
    assert_eq!(item.name, "New Name");
    assert_eq!(item.description, "New description");
}

#[tokio::test]
async fn test_update_item_not_found() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    let response = client
        .put(format!("http://{addr}/items/999"))
        .json(&UpdateItem { name: Some("New Name".to_string()), description: None })
        .send()
        .await
        .unwrap();

    assert_eq!(response.status(), 404);
}

#[tokio::test]
async fn test_delete_item() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    // Create an item first
    let create_response = client
        .post(format!("http://{addr}/items"))
        .json(&CreateItem {
            name: "Delete Me".to_string(),
            description: "An item to delete".to_string(),
        })
        .send()
        .await
        .unwrap();
    let created: Item = create_response.json().await.unwrap();

    // Delete the item
    let response =
        client.delete(format!("http://{addr}/items/{}", created.id)).send().await.unwrap();

    assert_eq!(response.status(), 200);

    // Verify the item is gone
    let get_response =
        client.get(format!("http://{addr}/items/{}", created.id)).send().await.unwrap();
    assert_eq!(get_response.status(), 404);
}

#[tokio::test]
async fn test_delete_item_not_found() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    let response = client.delete(format!("http://{addr}/items/999")).send().await.unwrap();

    assert_eq!(response.status(), 404);
}

#[tokio::test]
async fn test_list_items_with_data() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    // Create multiple items
    for i in 1..=3 {
        let response = client
            .post(format!("http://{addr}/items"))
            .json(&CreateItem {
                name: format!("Item {i}"),
                description: format!("Description {i}"),
            })
            .send()
            .await
            .unwrap();
        assert_eq!(response.status(), 201);
    }

    // List all items
    let response = client.get(format!("http://{addr}/items")).send().await.unwrap();

    assert_eq!(response.status(), 200);
    let items: Vec<Item> = response.json().await.unwrap();
    assert_eq!(items.len(), 3);
    assert_eq!(items[0].name, "Item 1");
    assert_eq!(items[1].name, "Item 2");
    assert_eq!(items[2].name, "Item 3");
}

#[tokio::test]
async fn test_create_item_invalid_body() {
    let addr = setup_server().await;
    let client = reqwest::Client::new();

    let response = client
        .post(format!("http://{addr}/items"))
        .body("not-json")
        .header("Content-Type", "application/json")
        .send()
        .await
        .unwrap();

    assert_eq!(response.status(), 400);
}
