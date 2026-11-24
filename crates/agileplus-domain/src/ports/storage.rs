//! Storage port -- persistence abstraction for all domain entities.
//!
//! Traceability: FR-STORE-* / WP05-T025

use crate::domain::audit::AuditEntry;
use crate::domain::cycle::{Cycle, CycleFeature, CycleState, CycleWithFeatures};
use crate::domain::feature::Feature;
use crate::domain::governance::{Evidence, GovernanceContract, PolicyRule};
use crate::domain::metric::Metric;
use crate::domain::module::{Module, ModuleFeatureTag, ModuleWithFeatures};
use crate::domain::project::Project;
use crate::domain::state_machine::FeatureState;
use crate::domain::sync_mapping::SyncMapping;
use crate::domain::work_package::{WorkPackage, WpDependency, WpState};
use crate::error::DomainError;

/// Port for persistent storage operations.
///
/// Implementations provide CRUD access to all domain entities.
/// The SQLite adapter (WP06) is the primary implementation.
#[async_trait::async_trait]
pub trait StoragePort: Send + Sync {
    // -- Feature CRUD --

    /// Create a new feature, returning its assigned ID.
    async fn create_feature(&self, feature: &Feature) -> Result<i64, DomainError>;

    async fn get_feature_by_slug(&self, slug: &str) -> Result<Option<Feature>, DomainError>;

    async fn get_feature_by_id(&self, id: i64) -> Result<Option<Feature>, DomainError>;

    async fn update_feature_state(&self, id: i64, state: FeatureState) -> Result<(), DomainError>;

    async fn list_features_by_state(
        &self,
        state: FeatureState,
    ) -> Result<Vec<Feature>, DomainError>;

    async fn list_all_features(&self) -> Result<Vec<Feature>, DomainError>;

    async fn create_work_package(&self, wp: &WorkPackage) -> Result<i64, DomainError>;

    async fn get_work_package(&self, id: i64) -> Result<Option<WorkPackage>, DomainError>;

    async fn update_wp_state(&self, id: i64, state: WpState) -> Result<(), DomainError>;

    async fn list_wps_by_feature(&self, feature_id: i64) -> Result<Vec<WorkPackage>, DomainError>;

    async fn add_wp_dependency(&self, dep: &WpDependency) -> Result<(), DomainError>;

    async fn get_wp_dependencies(&self, wp_id: i64) -> Result<Vec<WpDependency>, DomainError>;

    async fn get_ready_wps(&self, feature_id: i64) -> Result<Vec<WorkPackage>, DomainError>;

    async fn append_audit_entry(&self, entry: &AuditEntry) -> Result<i64, DomainError>;

    async fn get_audit_trail(&self, feature_id: i64) -> Result<Vec<AuditEntry>, DomainError>;

    async fn get_latest_audit_entry(
        &self,
        feature_id: i64,
    ) -> Result<Option<AuditEntry>, DomainError>;

    async fn create_evidence(&self, evidence: &Evidence) -> Result<i64, DomainError>;

    async fn get_evidence_by_wp(&self, wp_id: i64) -> Result<Vec<Evidence>, DomainError>;

    async fn get_evidence_by_fr(&self, fr_id: &str) -> Result<Vec<Evidence>, DomainError>;

    async fn create_policy_rule(&self, rule: &PolicyRule) -> Result<i64, DomainError>;

    async fn list_active_policies(&self) -> Result<Vec<PolicyRule>, DomainError>;

    async fn record_metric(&self, metric: &Metric) -> Result<i64, DomainError>;

    async fn get_metrics_by_feature(&self, feature_id: i64) -> Result<Vec<Metric>, DomainError>;

    async fn create_governance_contract(
        &self,
        contract: &GovernanceContract,
    ) -> Result<i64, DomainError>;

    async fn get_governance_contract(
        &self,
        feature_id: i64,
        version: i32,
    ) -> Result<Option<GovernanceContract>, DomainError>;

    async fn get_latest_governance_contract(
        &self,
        feature_id: i64,
    ) -> Result<Option<GovernanceContract>, DomainError>;

    async fn create_module(&self, module: &Module) -> Result<i64, DomainError>;

    async fn get_module(&self, id: i64) -> Result<Option<Module>, DomainError>;

    async fn get_module_by_slug(&self, slug: &str) -> Result<Option<Module>, DomainError>;

    async fn update_module(
        &self,
        id: i64,
        friendly_name: &str,
        description: Option<&str>,
    ) -> Result<(), DomainError>;

    async fn delete_module(&self, id: i64) -> Result<(), DomainError>;

    async fn list_root_modules(&self) -> Result<Vec<Module>, DomainError>;

    async fn list_child_modules(&self, parent_id: i64) -> Result<Vec<Module>, DomainError>;

    async fn get_module_with_features(
        &self,
        id: i64,
    ) -> Result<Option<ModuleWithFeatures>, DomainError>;

    async fn create_cycle(&self, cycle: &Cycle) -> Result<i64, DomainError>;

    async fn get_cycle(&self, id: i64) -> Result<Option<Cycle>, DomainError>;

    async fn update_cycle_state(&self, id: i64, state: CycleState) -> Result<(), DomainError>;

    async fn list_cycles_by_state(&self, state: CycleState) -> Result<Vec<Cycle>, DomainError>;

    async fn list_cycles_by_module(&self, module_id: i64) -> Result<Vec<Cycle>, DomainError>;

    async fn list_all_cycles(&self) -> Result<Vec<Cycle>, DomainError>;

    async fn get_cycle_with_features(
        &self,
        id: i64,
    ) -> Result<Option<CycleWithFeatures>, DomainError>;

    async fn tag_feature_to_module(&self, tag: &ModuleFeatureTag) -> Result<(), DomainError>;

    async fn untag_feature_from_module(
        &self,
        module_id: i64,
        feature_id: i64,
    ) -> Result<(), DomainError>;

    async fn add_feature_to_cycle(&self, entry: &CycleFeature) -> Result<(), DomainError>;

    async fn remove_feature_from_cycle(
        &self,
        cycle_id: i64,
        feature_id: i64,
    ) -> Result<(), DomainError>;

    async fn get_sync_mapping(
        &self,
        entity_type: &str,
        entity_id: i64,
    ) -> Result<Option<SyncMapping>, DomainError>;

    async fn upsert_sync_mapping(&self, mapping: &SyncMapping) -> Result<(), DomainError>;

    async fn get_sync_mapping_by_plane_id(
        &self,
        entity_type: &str,
        plane_issue_id: &str,
    ) -> Result<Option<SyncMapping>, DomainError>;

    async fn delete_sync_mapping(
        &self,
        entity_type: &str,
        entity_id: i64,
    ) -> Result<(), DomainError>;

    // -- Project CRUD --

    /// Create a new project, returning its assigned ID.
    async fn create_project(&self, project: &Project) -> Result<i64, DomainError>;

    /// Look up a project by its slug. Returns None if not found.
    async fn get_project_by_slug(&self, slug: &str) -> Result<Option<Project>, DomainError>;
}
