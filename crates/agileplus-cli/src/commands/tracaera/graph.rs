use std::collections::BTreeMap;

use agileplus_domain::domain::event::Event;
use agileplus_domain::domain::feature::Feature;
use agileplus_domain::domain::governance::{Evidence, GovernanceContract};
use agileplus_domain::domain::work_package::WorkPackage;
use agileplus_domain::ports::StoragePort;
use agileplus_events::EventStore;
use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::Serialize;

#[derive(Debug, Serialize)]
pub(super) struct TracaeraTraceGraph {
    schema: &'static str,
    exported_at: DateTime<Utc>,
    feature: FeatureNode,
    requirements: Vec<RequirementNode>,
    implementation_refs: Vec<ImplementationRef>,
    test_refs: Vec<TestRef>,
    evidence_refs: Vec<EvidenceRef>,
    event_provenance: Vec<EventProvenance>,
}

#[derive(Debug, Serialize)]
struct FeatureNode {
    id: String,
    slug: String,
    title: String,
    state: String,
    target_branch: String,
}

#[derive(Debug, Serialize)]
struct RequirementNode {
    id: String,
    evidence_type: String,
    threshold: Option<serde_json::Value>,
    source: String,
}

#[derive(Debug, Serialize)]
struct ImplementationRef {
    id: String,
    requirement_ids: Vec<String>,
    title: String,
    state: String,
    file_scope: Vec<String>,
    worktree_path: Option<String>,
    pr_url: Option<String>,
}

#[derive(Debug, Serialize)]
struct TestRef {
    id: String,
    requirement_ids: Vec<String>,
    acceptance_criteria: String,
}

#[derive(Debug, Serialize)]
struct EvidenceRef {
    id: String,
    requirement_id: String,
    work_package_id: String,
    evidence_type: String,
    artifact_path: String,
    metadata: Option<serde_json::Value>,
    created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
struct EventProvenance {
    id: i64,
    entity_type: String,
    entity_id: i64,
    event_type: String,
    actor: String,
    sequence: i64,
    timestamp: DateTime<Utc>,
    hash: String,
}

pub(super) async fn build_trace_graph<S>(
    storage: &S,
    feature: Feature,
) -> Result<TracaeraTraceGraph>
where
    S: StoragePort + EventStore,
{
    let wps = storage
        .list_wps_by_feature(feature.id)
        .await
        .context("listing work packages for Tracaera export")?;
    let contract = storage
        .get_latest_governance_contract(feature.id)
        .await
        .context("loading governance contract for Tracaera export")?;
    let audit_events = storage
        .get_audit_trail(feature.id)
        .await
        .context("loading audit trail for Tracaera export")?;
    let mut events = storage
        .get_events("feature", feature.id)
        .await
        .context("loading feature event provenance")?;
    for wp in &wps {
        events.extend(
            storage
                .get_events("wp", wp.id)
                .await
                .with_context(|| format!("loading event provenance for WP {}", wp.id))?,
        );
    }

    let requirements = requirement_nodes(contract.as_ref());
    let requirement_ids: Vec<String> = requirements.iter().map(|req| req.id.clone()).collect();
    let evidence_refs = evidence_refs_for_requirements(storage, &requirement_ids).await?;
    let evidence_requirement_ids = requirement_ids_by_work_package(&evidence_refs);

    Ok(TracaeraTraceGraph {
        schema: "agileplus.tracaera.trace_graph.v1",
        exported_at: Utc::now(),
        feature: feature_node(&feature),
        requirements,
        implementation_refs: implementation_refs(&wps, &requirement_ids, &evidence_requirement_ids),
        test_refs: test_refs(&wps, &requirement_ids, &evidence_requirement_ids),
        evidence_refs,
        event_provenance: event_provenance(events, audit_events),
    })
}

fn feature_node(feature: &Feature) -> FeatureNode {
    FeatureNode {
        id: format!("feature:{}", feature.id),
        slug: feature.slug.clone(),
        title: feature.friendly_name.clone(),
        state: feature.state.to_string(),
        target_branch: feature.target_branch.clone(),
    }
}

fn requirement_nodes(contract: Option<&GovernanceContract>) -> Vec<RequirementNode> {
    let mut requirements = Vec::new();
    if let Some(contract) = contract {
        for rule in &contract.rules {
            for req in &rule.required_evidence {
                requirements.push(RequirementNode {
                    id: req.fr_id.clone(),
                    evidence_type: format!("{:?}", req.evidence_type),
                    threshold: req.threshold.clone(),
                    source: format!("governance_contract:v{}", contract.version),
                });
            }
        }
    }
    requirements.sort_by(|a, b| a.id.cmp(&b.id).then(a.evidence_type.cmp(&b.evidence_type)));
    requirements.dedup_by(|a, b| a.id == b.id && a.evidence_type == b.evidence_type);
    requirements
}

fn implementation_refs(
    wps: &[WorkPackage],
    requirement_ids: &[String],
    evidence_requirement_ids: &BTreeMap<String, Vec<String>>,
) -> Vec<ImplementationRef> {
    wps.iter()
        .map(|wp| ImplementationRef {
            id: format!("wp:{}", wp.id),
            requirement_ids: matching_requirement_ids(
                wp,
                requirement_ids,
                evidence_requirement_ids,
            ),
            title: wp.title.clone(),
            state: format!("{:?}", wp.state),
            file_scope: wp.file_scope.clone(),
            worktree_path: wp.worktree_path.clone(),
            pr_url: wp.pr_url.clone(),
        })
        .collect()
}

fn test_refs(
    wps: &[WorkPackage],
    requirement_ids: &[String],
    evidence_requirement_ids: &BTreeMap<String, Vec<String>>,
) -> Vec<TestRef> {
    wps.iter()
        .map(|wp| TestRef {
            id: format!("wp:{}:acceptance", wp.id),
            requirement_ids: matching_requirement_ids(
                wp,
                requirement_ids,
                evidence_requirement_ids,
            ),
            acceptance_criteria: wp.acceptance_criteria.clone(),
        })
        .collect()
}

fn matching_requirement_ids(
    wp: &WorkPackage,
    requirement_ids: &[String],
    evidence_requirement_ids: &BTreeMap<String, Vec<String>>,
) -> Vec<String> {
    let mut matches: Vec<String> = requirement_ids
        .iter()
        .filter(|id| {
            wp.title.contains(id.as_str())
                || wp.acceptance_criteria.contains(id.as_str())
                || wp
                    .file_scope
                    .iter()
                    .any(|scope| scope.contains(id.as_str()))
        })
        .cloned()
        .collect();
    if let Some(evidence_ids) = evidence_requirement_ids.get(&wp.id.to_string()) {
        matches.extend(evidence_ids.iter().cloned());
    }
    matches.sort();
    matches.dedup();
    matches
}

async fn evidence_refs_for_requirements<S>(
    storage: &S,
    requirement_ids: &[String],
) -> Result<Vec<EvidenceRef>>
where
    S: StoragePort,
{
    let mut refs = Vec::new();
    for req_id in requirement_ids {
        let evidence = storage
            .get_evidence_by_fr(req_id)
            .await
            .with_context(|| format!("loading evidence for requirement {req_id}"))?;
        refs.extend(evidence.into_iter().map(evidence_ref));
    }
    refs.sort_by(|a, b| a.id.cmp(&b.id));
    Ok(refs)
}

fn evidence_ref(evidence: Evidence) -> EvidenceRef {
    EvidenceRef {
        id: format!("evidence:{}", evidence.id),
        requirement_id: evidence.fr_id,
        work_package_id: format!("wp:{}", evidence.wp_id),
        evidence_type: format!("{:?}", evidence.evidence_type),
        artifact_path: evidence.artifact_path,
        metadata: evidence.metadata,
        created_at: evidence.created_at,
    }
}

fn requirement_ids_by_work_package(evidence_refs: &[EvidenceRef]) -> BTreeMap<String, Vec<String>> {
    let mut by_wp: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for evidence in evidence_refs {
        by_wp
            .entry(
                evidence
                    .work_package_id
                    .strip_prefix("wp:")
                    .unwrap_or(&evidence.work_package_id)
                    .to_string(),
            )
            .or_default()
            .push(evidence.requirement_id.clone());
    }
    for ids in by_wp.values_mut() {
        ids.sort();
        ids.dedup();
    }
    by_wp
}

fn event_provenance(
    mut events: Vec<Event>,
    audit_events: Vec<agileplus_domain::domain::audit::AuditEntry>,
) -> Vec<EventProvenance> {
    events.sort_by_key(|event| (event.timestamp, event.sequence, event.id));
    let mut provenance: Vec<EventProvenance> = events
        .into_iter()
        .map(|event| EventProvenance {
            id: event.id,
            entity_type: event.entity_type,
            entity_id: event.entity_id,
            event_type: event.event_type,
            actor: event.actor,
            sequence: event.sequence,
            timestamp: event.timestamp,
            hash: hex_hash(&event.hash),
        })
        .collect();
    provenance.extend(audit_events.into_iter().map(|entry| EventProvenance {
        id: entry.id,
        entity_type: "audit".to_string(),
        entity_id: entry.feature_id,
        event_type: entry.transition,
        actor: entry.actor,
        sequence: entry.id,
        timestamp: entry.timestamp,
        hash: hex_hash(&entry.hash),
    }));
    provenance
}

fn hex_hash(hash: &[u8; 32]) -> String {
    hash.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use agileplus_domain::domain::governance::{EvidenceRequirement, EvidenceType, GovernanceRule};
    use agileplus_domain::domain::work_package::WpState;

    use super::*;

    #[test]
    fn requirement_nodes_deduplicate_contract_requirements() {
        let contract = GovernanceContract {
            id: 1,
            feature_id: 1,
            version: 2,
            rules: vec![GovernanceRule {
                transition: "Implementing -> Validated".to_string(),
                required_evidence: vec![
                    EvidenceRequirement {
                        fr_id: "FR-001".to_string(),
                        evidence_type: EvidenceType::TestResult,
                        threshold: Some(serde_json::json!({"min_coverage": 80.0})),
                    },
                    EvidenceRequirement {
                        fr_id: "FR-001".to_string(),
                        evidence_type: EvidenceType::TestResult,
                        threshold: None,
                    },
                ],
                policy_refs: vec![],
            }],
            bound_at: Utc::now(),
        };

        let requirements = requirement_nodes(Some(&contract));

        assert_eq!(requirements.len(), 1);
        assert_eq!(requirements[0].id, "FR-001");
        assert_eq!(requirements[0].source, "governance_contract:v2");
    }

    #[test]
    fn implementation_and_test_refs_include_matching_requirement_ids() {
        let wp = WorkPackage {
            id: 7,
            feature_id: 1,
            title: "Implement FR-001 export".to_string(),
            state: WpState::Doing,
            sequence: 1,
            file_scope: vec!["src/fr_001.rs".to_string()],
            acceptance_criteria: "Verify FR-001 and FR-002".to_string(),
            agent_id: None,
            pr_url: Some("https://example.invalid/pr/1".to_string()),
            pr_state: None,
            worktree_path: None,
            plane_sub_issue_id: None,
            base_commit: None,
            head_commit: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };
        let ids = vec![
            "FR-001".to_string(),
            "FR-002".to_string(),
            "FR-999".to_string(),
        ];

        let evidence_ids = BTreeMap::new();
        let implementation = implementation_refs(std::slice::from_ref(&wp), &ids, &evidence_ids);
        let tests = test_refs(&[wp], &ids, &evidence_ids);

        assert_eq!(implementation[0].requirement_ids, vec!["FR-001", "FR-002"]);
        assert_eq!(tests[0].requirement_ids, vec!["FR-001", "FR-002"]);
    }

    #[test]
    fn implementation_and_test_refs_include_evidence_requirement_ids() {
        let wp = WorkPackage {
            id: 7,
            feature_id: 1,
            title: "Implement dogfood export".to_string(),
            state: WpState::Done,
            sequence: 1,
            file_scope: vec!["docs/specs/{slug}/.".to_string()],
            acceptance_criteria: "Verify FR-1, FR-2, and FR-3".to_string(),
            agent_id: None,
            pr_url: None,
            pr_state: None,
            worktree_path: None,
            plane_sub_issue_id: None,
            base_commit: None,
            head_commit: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };
        let ids = vec!["FR-CI".to_string(), "FR-REVIEW".to_string()];
        let evidence_refs = vec![
            EvidenceRef {
                id: "evidence:1".to_string(),
                requirement_id: "FR-CI".to_string(),
                work_package_id: "wp:7".to_string(),
                evidence_type: "CiOutput".to_string(),
                artifact_path: "ci.md".to_string(),
                metadata: None,
                created_at: Utc::now(),
            },
            EvidenceRef {
                id: "evidence:2".to_string(),
                requirement_id: "FR-REVIEW".to_string(),
                work_package_id: "wp:7".to_string(),
                evidence_type: "ReviewApproval".to_string(),
                artifact_path: "review.md".to_string(),
                metadata: None,
                created_at: Utc::now(),
            },
        ];
        let evidence_ids = requirement_ids_by_work_package(&evidence_refs);

        let implementation = implementation_refs(std::slice::from_ref(&wp), &ids, &evidence_ids);
        let tests = test_refs(&[wp], &ids, &evidence_ids);

        assert_eq!(
            implementation[0].requirement_ids,
            vec!["FR-CI", "FR-REVIEW"]
        );
        assert_eq!(tests[0].requirement_ids, vec!["FR-CI", "FR-REVIEW"]);
    }
}
