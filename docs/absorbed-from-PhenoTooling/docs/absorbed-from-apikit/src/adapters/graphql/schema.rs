//! GraphQL schema definitions exposing the Item domain model.

use std::sync::Arc;

use async_graphql::{
    futures_util::stream::{BoxStream, StreamExt},
    InputObject, Object, Schema, SimpleObject, Subscription, ID,
};

use crate::domain::{CreateItem, Item, ItemStore, UpdateItem};

/// GraphQL representation of an `Item`.
#[derive(SimpleObject, Clone)]
#[graphql(name = "Item")]
pub struct GraphItem {
    pub id: ID,
    pub name: String,
    pub description: String,
}

impl From<Item> for GraphItem {
    fn from(item: Item) -> Self {
        Self {
            id: ID(item.id.to_string()),
            name: item.name,
            description: item.description,
        }
    }
}

/// Input for creating a new item via GraphQL.
#[derive(InputObject)]
pub struct CreateGraphItem {
    pub name: String,
    pub description: String,
}

impl From<CreateGraphItem> for CreateItem {
    fn from(input: CreateGraphItem) -> Self {
        Self {
            name: input.name,
            description: input.description,
        }
    }
}

/// Input for updating an existing item via GraphQL.
#[derive(InputObject)]
pub struct UpdateGraphItem {
    pub name: Option<String>,
    pub description: Option<String>,
}

impl From<UpdateGraphItem> for UpdateItem {
    fn from(input: UpdateGraphItem) -> Self {
        Self {
            name: input.name,
            description: input.description,
        }
    }
}

/// Query root for the GraphQL schema.
pub struct QueryRoot {
    store: Arc<ItemStore>,
}

impl QueryRoot {
    pub fn new(store: Arc<ItemStore>) -> Self {
        Self { store }
    }
}

#[Object]
impl QueryRoot {
    /// Fetch a single item by id.
    async fn item(&self, id: ID) -> Option<GraphItem> {
        id.parse::<u64>()
            .ok()
            .and_then(|id| self.store.get(id))
            .map(Into::into)
    }

    /// List all items.
    async fn items(&self) -> Vec<GraphItem> {
        self.store.list().into_iter().map(Into::into).collect()
    }
}

/// Mutation root for the GraphQL schema.
pub struct MutationRoot {
    store: Arc<ItemStore>,
}

impl MutationRoot {
    pub fn new(store: Arc<ItemStore>) -> Self {
        Self { store }
    }
}

#[Object]
impl MutationRoot {
    /// Create a new item.
    async fn create_item(&self, input: CreateGraphItem) -> GraphItem {
        self.store.create(input.into()).into()
    }

    /// Update an existing item.
    async fn update_item(&self, id: ID, input: UpdateGraphItem) -> Option<GraphItem> {
        id.parse::<u64>()
            .ok()
            .and_then(|id| self.store.update(id, input.into()))
            .map(Into::into)
    }

    /// Delete an existing item.
    async fn delete_item(&self, id: ID) -> Option<GraphItem> {
        id.parse::<u64>()
            .ok()
            .and_then(|id| self.store.delete(id))
            .map(Into::into)
    }
}

/// Subscription root for the GraphQL schema.
pub struct SubscriptionRoot {
    store: Arc<ItemStore>,
}

impl SubscriptionRoot {
    pub fn new(store: Arc<ItemStore>) -> Self {
        Self { store }
    }
}

#[Subscription]
impl SubscriptionRoot {
    /// Stream the current list of items.
    async fn items_stream(&self) -> BoxStream<'static, Vec<GraphItem>> {
        let items: Vec<GraphItem> = self.store.list().into_iter().map(Into::into).collect();
        async_graphql::futures_util::stream::iter(items)
            .map(|item| vec![item])
            .boxed()
    }
}

/// The GraphQL schema type used by this adapter.
pub type GraphQLSchema = Schema<QueryRoot, MutationRoot, SubscriptionRoot>;

/// Build a new GraphQL schema backed by the supplied `ItemStore`.
pub fn build_schema(store: Arc<ItemStore>) -> GraphQLSchema {
    Schema::build(
        QueryRoot::new(store.clone()),
        MutationRoot::new(store.clone()),
        SubscriptionRoot::new(store.clone()),
    )
    .finish()
}

/// Execute a GraphQL query against the provided schema.
pub async fn execute_query(schema: &GraphQLSchema, query: &str) -> async_graphql::Response {
    schema.execute(query).await
}

/// Execute a GraphQL mutation against the provided schema.
pub async fn execute_mutation(
    schema: &GraphQLSchema,
    mutation: &str,
) -> async_graphql::Response {
    schema.execute(mutation).await
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_schema() -> GraphQLSchema {
        let store = Arc::new(ItemStore::new());
        build_schema(store)
    }

    #[tokio::test]
    async fn test_query_items_empty() {
        let schema = setup_schema();
        let res = execute_query(&schema, "{ items { id name description } }").await;
        assert!(res.is_ok());
        let json = serde_json::to_value(&res).unwrap();
        let items = json["data"]["items"].as_array().unwrap();
        assert!(items.is_empty());
    }

    #[tokio::test]
    async fn test_mutation_create_item() {
        let schema = setup_schema();
        let mutation = r#"mutation { createItem(input: { name: "Test", description: "Desc" }) { id name description } }"#;
        let res = execute_mutation(&schema, mutation).await;
        assert!(res.is_ok());
        let json = serde_json::to_value(&res).unwrap();
        let item = &json["data"]["createItem"];
        assert_eq!(item["name"], "Test");
        assert_eq!(item["description"], "Desc");
    }

    #[tokio::test]
    async fn test_query_item_by_id() {
        let schema = setup_schema();
        let mutation = r#"mutation { createItem(input: { name: "Find Me", description: "Desc" }) { id name description } }"#;
        let res = execute_mutation(&schema, mutation).await;
        let json = serde_json::to_value(&res).unwrap();
        let id = json["data"]["createItem"]["id"].as_str().unwrap();

        let query = format!("{{ item(id: \"{}\") {{ id name description }} }}", id);
        let res = execute_query(&schema, &query).await;
        assert!(res.is_ok());
        let json = serde_json::to_value(&res).unwrap();
        let item = &json["data"]["item"];
        assert_eq!(item["name"], "Find Me");
    }

    #[tokio::test]
    async fn test_query_item_not_found() {
        let schema = setup_schema();
        let res = execute_query(&schema, "{ item(id: \"999\") { id name description } }").await;
        assert!(res.is_ok());
        let json = serde_json::to_value(&res).unwrap();
        assert!(json["data"]["item"].is_null());
    }

    #[tokio::test]
    async fn test_mutation_update_item() {
        let schema = setup_schema();
        let mutation = r#"mutation { createItem(input: { name: "Old", description: "Old Desc" }) { id name description } }"#;
        let res = execute_mutation(&schema, mutation).await;
        let json = serde_json::to_value(&res).unwrap();
        let id = json["data"]["createItem"]["id"].as_str().unwrap();

        let update = format!(
            r#"mutation {{ updateItem(id: "{}", input: {{ name: "New" }}) {{ id name description }} }}"#,
            id
        );
        let res = execute_mutation(&schema, &update).await;
        assert!(res.is_ok());
        let json = serde_json::to_value(&res).unwrap();
        let item = &json["data"]["updateItem"];
        assert_eq!(item["name"], "New");
        assert_eq!(item["description"], "Old Desc");
    }

    #[tokio::test]
    async fn test_mutation_delete_item() {
        let schema = setup_schema();
        let mutation = r#"mutation { createItem(input: { name: "Delete Me", description: "Desc" }) { id name description } }"#;
        let res = execute_mutation(&schema, mutation).await;
        let json = serde_json::to_value(&res).unwrap();
        let id = json["data"]["createItem"]["id"].as_str().unwrap();

        let delete = format!(r#"mutation {{ deleteItem(id: "{}") {{ id name description }} }}"#, id);
        let res = execute_mutation(&schema, &delete).await;
        assert!(res.is_ok());
        let json = serde_json::to_value(&res).unwrap();
        let item = &json["data"]["deleteItem"];
        assert_eq!(item["name"], "Delete Me");

        let query = format!("{{ item(id: \"{}\") {{ id name description }} }}", id);
        let res = execute_query(&schema, &query).await;
        let json = serde_json::to_value(&res).unwrap();
        assert!(json["data"]["item"].is_null());
    }

    #[tokio::test]
    async fn test_subscription_items_stream() {
        let schema = setup_schema();
        let request = async_graphql::Request::new("subscription { itemsStream { id name description } }");
        let mut stream = schema.execute_stream(request);
        let mut count = 0;
        while let Some(response) = stream.next().await {
            assert!(response.is_ok());
            count += 1;
        }
        assert_eq!(count, 0); // Empty store yields empty stream
    }
}

