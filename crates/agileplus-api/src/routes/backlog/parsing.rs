use agileplus_domain::domain::backlog::{BacklogPriority, BacklogSort, BacklogStatus, Intent};

use crate::error::ApiError;

pub(super) fn parse_intent(value: Option<String>) -> Result<Intent, ApiError> {
    let value = value.unwrap_or_else(|| "task".to_string());
    value
        .parse::<Intent>()
        .map_err(|e| ApiError::BadRequest(e.to_string()))
}

pub(super) fn parse_intent_opt(value: Option<String>) -> Result<Option<Intent>, ApiError> {
    value.map(|v| parse_intent(Some(v))).transpose()
}

pub(super) fn parse_priority(value: String) -> Result<BacklogPriority, ApiError> {
    value
        .parse::<BacklogPriority>()
        .map_err(|e| ApiError::BadRequest(e.to_string()))
}

pub(super) fn parse_priority_opt(
    value: Option<String>,
) -> Result<Option<BacklogPriority>, ApiError> {
    value.map(parse_priority).transpose()
}

pub(super) fn parse_status(value: &str) -> Result<BacklogStatus, ApiError> {
    value
        .parse::<BacklogStatus>()
        .map_err(|e| ApiError::BadRequest(e.to_string()))
}

pub(super) fn parse_status_opt(value: Option<String>) -> Result<Option<BacklogStatus>, ApiError> {
    value.as_deref().map(parse_status).transpose()
}

pub(super) fn parse_sort(value: &str) -> Result<BacklogSort, ApiError> {
    value
        .parse::<BacklogSort>()
        .map_err(|e| ApiError::BadRequest(e.to_string()))
}
