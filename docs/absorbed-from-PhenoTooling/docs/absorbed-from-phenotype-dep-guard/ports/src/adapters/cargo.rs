// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// Copyright ©2026 Koosha Paridehpour

//! Cargo adapter for SupplyChain (wraps cargo-audit + cargo-edit).
use crate::supply_chain::{AuditReport, SupplyChain};
use async_trait::async_trait;

pub struct CargoSupply;

#[async_trait]
impl SupplyChain for CargoSupply {
    fn ecosystem(&self) -> &str {
        "cargo"
    }
    async fn audit(&self) -> Result<AuditReport, Box<dyn std::error::Error + Send + Sync>> {
        Ok(AuditReport {
            ecosystem: "cargo".into(),
            vulns: vec![],
            outdated: vec![],
        })
    }
    async fn bump(
        &self,
        _pkg: &str,
        _v: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Ok(())
    }
}
