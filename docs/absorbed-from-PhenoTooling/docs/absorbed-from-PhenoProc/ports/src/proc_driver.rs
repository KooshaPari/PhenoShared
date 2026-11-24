//! T78: PhenoProc hexagonal port — ProcDriver.
//!
//! 3 adapters: CargoExpandAdapter, TrybuildAdapter, NightlyAdapter.
use async_trait::async_trait;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Expansion {
    pub file: String,
    pub original: String,
    pub expanded: String,
}

#[async_trait]
pub trait ProcDriver: Send + Sync {
    fn backend(&self) -> &str;
    async fn expand(
        &self,
        path: &Path,
    ) -> Result<Expansion, Box<dyn std::error::Error + Send + Sync>>;
    async fn trybuild(
        &self,
        path: &Path,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
}
