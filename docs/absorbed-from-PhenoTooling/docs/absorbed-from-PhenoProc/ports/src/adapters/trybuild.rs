use super::proc_driver::{Expansion, ProcDriver};
use async_trait::async_trait;
use std::path::Path;

pub struct TrybuildAdapter;

#[async_trait]
impl ProcDriver for TrybuildAdapter {
    fn backend(&self) -> &str {
        "trybuild"
    }
    async fn expand(
        &self,
        _path: &Path,
    ) -> Result<Expansion, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Expansion {
            file: "".into(),
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
