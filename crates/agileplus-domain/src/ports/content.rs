use crate::domain::backlog::{BacklogFilters, BacklogItem, BacklogPriority, BacklogStatus};
use crate::domain::feature::Feature;
use crate::domain::state_machine::FeatureState;
use crate::domain::work_package::{WorkPackage, WpDependency, WpState};
use crate::error::DomainError;

/// Content-storage operations for features, backlog, and work packages.
#[async_trait::async_trait]
pub trait ContentStoragePort: Send + Sync {
    /// Create a new feature, returning its assigned ID.
    async fn create_feature(&self, feature: &Feature) -> Result<i64, DomainError>;

    async fn get_feature_by_slug(&self, slug: &str) -> Result<Option<Feature>, DomainError>;

    async fn get_feature_by_id(&self, id: i64) -> Result<Option<Feature>, DomainError>;

    async fn update_feature_state(&self, id: i64, state: FeatureState) -> Result<(), DomainError>;

    async fn update_feature(&self, feature: &Feature) -> Result<(), DomainError>;

    async fn list_features_by_state(
        &self,
        state: FeatureState,
    ) -> Result<Vec<Feature>, DomainError>;

    async fn list_all_features(&self) -> Result<Vec<Feature>, DomainError>;

    async fn create_backlog_item(&self, item: &BacklogItem) -> Result<i64, DomainError>;

    async fn get_backlog_item(&self, id: i64) -> Result<Option<BacklogItem>, DomainError>;

    async fn list_backlog_items(
        &self,
        filters: &BacklogFilters,
    ) -> Result<Vec<BacklogItem>, DomainError>;

    async fn update_backlog_status(
        &self,
        id: i64,
        status: BacklogStatus,
    ) -> Result<(), DomainError>;

    async fn update_backlog_priority(
        &self,
        id: i64,
        priority: BacklogPriority,
    ) -> Result<(), DomainError>;

    async fn pop_next_backlog_item(&self) -> Result<Option<BacklogItem>, DomainError>;

    async fn create_work_package(&self, wp: &WorkPackage) -> Result<i64, DomainError>;

    async fn get_work_package(&self, id: i64) -> Result<Option<WorkPackage>, DomainError>;

    async fn update_wp_state(&self, id: i64, state: WpState) -> Result<(), DomainError>;

    async fn update_work_package(&self, wp: &WorkPackage) -> Result<(), DomainError>;

    async fn list_wps_by_feature(&self, feature_id: i64) -> Result<Vec<WorkPackage>, DomainError>;

    async fn add_wp_dependency(&self, dep: &WpDependency) -> Result<(), DomainError>;

    async fn get_wp_dependencies(&self, wp_id: i64) -> Result<Vec<WpDependency>, DomainError>;

    async fn get_ready_wps(&self, feature_id: i64) -> Result<Vec<WorkPackage>, DomainError>;
}
