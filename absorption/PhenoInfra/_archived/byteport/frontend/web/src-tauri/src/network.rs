use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[cfg(test)]
use mockall::automock;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ObjectMetadata {
    pub key: String,
    pub size: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ObjectSummary {
    pub key: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NetworkError {
    message: String,
}

impl NetworkError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl Display for NetworkError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.message)
    }
}

impl Error for NetworkError {}

#[cfg_attr(test, automock)]
pub trait NetworkClient {
    fn upload_chunk(&self, key: &str, bytes: &[u8]) -> Result<(), NetworkError>;
    fn fetch_metadata(&self, key: &str) -> Result<ObjectMetadata, NetworkError>;
    fn delete_object(&self, key: &str) -> Result<(), NetworkError>;
    fn list_objects(&self, prefix: &str) -> Result<Vec<ObjectSummary>, NetworkError>;
}

pub fn upload_chunk_command<C: NetworkClient>(
    client: &C,
    key: &str,
    bytes: Vec<u8>,
) -> Result<(), String> {
    client
        .upload_chunk(key, &bytes)
        .map_err(|error| error.to_string())
}

pub fn fetch_metadata_command<C: NetworkClient>(
    client: &C,
    key: &str,
) -> Result<ObjectMetadata, String> {
    client
        .fetch_metadata(key)
        .map_err(|error| error.to_string())
}

pub fn delete_object_command<C: NetworkClient>(client: &C, key: &str) -> Result<(), String> {
    client.delete_object(key).map_err(|error| error.to_string())
}

pub fn list_objects_command<C: NetworkClient>(
    client: &C,
    prefix: &str,
) -> Result<Vec<ObjectSummary>, String> {
    client
        .list_objects(prefix)
        .map_err(|error| error.to_string())
}
