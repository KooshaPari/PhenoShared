//! ContentStoragePort implementation for SQLite adapter.
//!
//! Traceability: WP06-T031

use agileplus_domain::domain::backlog::{
    BacklogFilters, BacklogItem, BacklogPriority, BacklogStatus,
};
use agileplus_domain::domain::feature::Feature;
use agileplus_domain::domain::state_machine::FeatureState;
use agileplus_domain::domain::work_package::{WorkPackage, WpDependency, WpState};
use agileplus_domain::error::DomainError;
use agileplus_domain::ports::ContentStoragePort;

use crate::ports::adapter::SqliteStorageAdapter;
use crate::repository::{backlog, features, work_packages};

#[async_trait::async_trait]
impl ContentStoragePort for SqliteStorageAdapter {
    // -- Feature CRUD --

    async fn create_feature(&self, feature: &Feature) -> Result<i64, DomainError> {
        let conn = self.lock()?;
        features::create_feature(&conn, feature)
    }

    async fn get_feature_by_slug(&self, slug: &str) -> Result<Option<Feature>, DomainError> {
        let conn = self.lock()?;
        features::get_feature_by_slug(&conn, slug)
    }

    async fn get_feature_by_id(&self, id: i64) -> Result<Option<Feature>, DomainError> {
        let conn = self.lock()?;
        features::get_feature_by_id(&conn, id)
    }

    async fn update_feature_state(&self, id: i64, state: FeatureState) -> Result<(), DomainError> {
        let conn = self.lock()?;
        features::update_feature_state(&conn, id, state)
    }

    async fn update_feature(&self, feature: &Feature) -> Result<(), DomainError> {
        let conn = self.lock()?;
        features::update_feature(&conn, feature)
    }

    async fn list_features_by_state(
        &self,
        state: FeatureState,
    ) -> Result<Vec<Feature>, DomainError> {
        let conn = self.lock()?;
        features::list_features_by_state(&conn, state)
    }

    async fn list_all_features(&self) -> Result<Vec<Feature>, DomainError> {
        let conn = self.lock()?;
        features::list_all_features(&conn)
    }

    // -- Backlog CRUD --

    async fn create_backlog_item(&self, item: &BacklogItem) -> Result<i64, DomainError> {
        let conn = self.lock()?;
        backlog::create_backlog_item(&conn, item)
    }

    async fn get_backlog_item(&self, id: i64) -> Result<Option<BacklogItem>, DomainError> {
        let conn = self.lock()?;
        backlog::get_backlog_item(&conn, id)
    }

    async fn list_backlog_items(
        &self,
        filters: &BacklogFilters,
    ) -> Result<Vec<BacklogItem>, DomainError> {
        let conn = self.lock()?;
        backlog::list_backlog_items(&conn, filters)
    }

    async fn update_backlog_status(
        &self,
        id: i64,
        status: BacklogStatus,
    ) -> Result<(), DomainError> {
        let conn = self.lock()?;
        backlog::update_backlog_status(&conn, id, status)
    }

    async fn update_backlog_priority(
        &self,
        id: i64,
        priority: BacklogPriority,
    ) -> Result<(), DomainError> {
        let conn = self.lock()?;
        backlog::update_backlog_priority(&conn, id, priority)
    }

    async fn pop_next_backlog_item(&self) -> Result<Option<BacklogItem>, DomainError> {
        let conn = self.lock()?;
        backlog::pop_next_backlog_item(&conn)
    }

    // -- Work Package CRUD --

    async fn create_work_package(&self, wp: &WorkPackage) -> Result<i64, DomainError> {
        let conn = self.lock()?;
        work_packages::create_work_package(&conn, wp)
    }

    async fn get_work_package(&self, id: i64) -> Result<Option<WorkPackage>, DomainError> {
        let conn = self.lock()?;
        work_packages::get_work_package(&conn, id)
    }

    async fn update_wp_state(&self, id: i64, state: WpState) -> Result<(), DomainError> {
        let conn = self.lock()?;
        work_packages::update_wp_state(&conn, id, state)
    }

    async fn update_work_package(&self, wp: &WorkPackage) -> Result<(), DomainError> {
        let conn = self.lock()?;
        work_packages::update_work_package(&conn, wp)
    }

    async fn list_wps_by_feature(&self, feature_id: i64) -> Result<Vec<WorkPackage>, DomainError> {
        let conn = self.lock()?;
        work_packages::list_wps_by_feature(&conn, feature_id)
    }

    async fn add_wp_dependency(&self, dep: &WpDependency) -> Result<(), DomainError> {
        let conn = self.lock()?;
        work_packages::add_wp_dependency(&conn, dep)
    }

    async fn get_wp_dependencies(&self, wp_id: i64) -> Result<Vec<WpDependency>, DomainError> {
        let conn = self.lock()?;
        work_packages::get_wp_dependencies(&conn, wp_id)
    }

    async fn get_ready_wps(&self, feature_id: i64) -> Result<Vec<WorkPackage>, DomainError> {
        let conn = self.lock()?;
        work_packages::get_ready_wps(&conn, feature_id)
    }
}
