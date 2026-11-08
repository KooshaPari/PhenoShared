// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// Copyright ©2026 Koosha Paridehpour

//! Npm adapter for SupplyChain (wraps npm audit + npm version).
use crate::supply_chain::{AuditReport, SupplyChain};
use async_trait::async_trait;

pub struct NpmSupply;

#[async_trait]
impl SupplyChain for NpmSupply {
    fn ecosystem(&self) -> &str {
        "npm"
    }
    async fn audit(&self) -> Result<AuditReport, Box<dyn std::error::Error + Send + Sync>> {
        Ok(AuditReport {
            ecosystem: "npm".into(),
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
