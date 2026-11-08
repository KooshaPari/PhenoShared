use super::proc_driver::{Expansion, ProcDriver};
use async_trait::async_trait;
use std::path::Path;

pub struct CargoExpandAdapter;

#[async_trait]
impl ProcDriver for CargoExpandAdapter {
    fn backend(&self) -> &str {
        "cargo-expand"
    }
    async fn expand(
        &self,
        path: &Path,
    ) -> Result<Expansion, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Expansion {
            file: path.display().to_string(),
            original: "".into(),
            expanded: "".into(),
        })
    }
    async fn trybuild(
        &self,
        _path: &Path,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Ok(())
    }
}
