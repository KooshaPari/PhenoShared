use crate::vcs::{Commit, Diff, Vcs};
use async_trait::async_trait;
use pheno_vcs_core::VcsError;

pub struct JjBackend;

#[async_trait]
impl Vcs for JjBackend {
    fn backend(&self) -> &str {
        "jj"
    }

    async fn log(&self, _n: usize) -> Result<Vec<Commit>, VcsError> {
        Ok(vec![])
    }

    async fn diff(&self, from: &str, to: &str) -> Result<Diff, VcsError> {
        Ok(Diff {
            from: from.into(),
            to: to.into(),
            patch: String::new(),
        })
    }

    async fn commit(&self, _msg: &str) -> Result<String, VcsError> {
        Ok("@".into())
    }
}
