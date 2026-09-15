use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::future::Future;
use std::pin::Pin;

pub type DatasetFuture<T> = Pin<Box<dyn Future<Output = Result<T>> + Send + 'static>>;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Record {
    pub id: String,
    pub fields: serde_json::Value,
}

impl Record {
    pub fn new(id: impl Into<String>, fields: serde_json::Value) -> Self {
        Self {
            id: id.into(),
            fields,
        }
    }
}

pub trait Dataset: Send + Sync {
    fn records(&self) -> DatasetFuture<Vec<Record>>;
    fn schema(&self) -> DatasetFuture<serde_json::Value>;
}
