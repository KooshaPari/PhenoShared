// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// Copyright ©2026 Koosha Paridehpour

//! 5 smoke tests for the SupplyChain port.
use ports::adapters::cargo::CargoSupply;
use ports::adapters::npm::NpmSupply;
use ports::supply_chain::SupplyChain;

#[tokio::test]
async fn cargo_ecosystem() {
    assert_eq!(CargoSupply.ecosystem(), "cargo");
}

#[tokio::test]
async fn npm_ecosystem() {
    assert_eq!(NpmSupply.ecosystem(), "npm");
}

#[tokio::test]
async fn cargo_audit_ok() {
    let r = CargoSupply.audit().await.unwrap();
    assert!(r.vulns.is_empty());
}

#[tokio::test]
async fn npm_audit_ok() {
    let r = NpmSupply.audit().await.unwrap();
    assert!(r.outdated.is_empty());
}

#[tokio::test]
async fn trait_object_safe() {
    let _t: Box<dyn SupplyChain> = Box::new(CargoSupply);
}
