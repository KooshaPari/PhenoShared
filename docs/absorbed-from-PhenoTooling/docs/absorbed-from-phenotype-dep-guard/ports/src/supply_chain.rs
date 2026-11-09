// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// Copyright ©2026 Koosha Paridehpour

//! T64: phenotype-dep-guard hexagonal port — SupplyChain.
//!
//! 3 adapters: CargoSupply, NpmSupply, PipSupply.
use async_trait::async_trait;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vuln {
    pub id: String,
    pub severity: String,
    pub package: String,
    pub fix: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Outdated {
    pub package: String,
    pub current: String,
    pub latest: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditReport {
    pub ecosystem: String,
    pub vulns: Vec<Vuln>,
    pub outdated: Vec<Outdated>,
}

#[async_trait]
pub trait SupplyChain: Send + Sync {
    fn ecosystem(&self) -> &str;
    async fn audit(&self) -> Result<AuditReport, Box<dyn std::error::Error + Send + Sync>>;
    async fn bump(
        &self,
        pkg: &str,
        version: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
}
