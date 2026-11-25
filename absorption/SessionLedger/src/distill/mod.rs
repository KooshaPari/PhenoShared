//! Distillation ("dream") — compiles a [`Session`] into a [`ContinuationBundle`]
//! and emits distilled facts into the [`MemoryStore`].
//!
//! Phase 1 ships the deterministic compiler skeleton: it assembles the bundle
//! envelope (Acceptance + Intent + Context + Provenance + Worklog) from a
//! session. Phase 3 adds episodic memory write-through behind the
//! [`crate::ports`] traits.
//!
//! The P1 [`extractor`] module provides the heuristic intent extractor adapter.
//! The P2 [`context_extractor`] and [`contract_extractor`] modules add heuristic
//! context and contract extraction adapters.
//! The P3 [`acceptance_extractor`] and [`compiler`] modules add the acceptance
//! extractor and the bundle compiler.

pub mod acceptance_extractor;
pub mod compiler;
pub mod context_extractor;
pub mod contract_compiler;
pub mod contract_extractor;
pub mod dedup_compiler;
pub mod extractor;
pub mod memory_writer;
pub mod token_estimator;

use crate::distill::contract_compiler::ContractCompiler;
use crate::distill::token_estimator::{CharCountTokenEstimator, TokenEstimator};
use crate::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use crate::domain::session::Session;
use crate::domain::worklog::WorklogProjection;
use crate::ports::{MemoryStore, PortError};
use serde_json::json;

pub use memory_writer::{DistillMemoryWriter, DistilledMemory};

/// Result of compiling a session and persisting its episodic facts.
#[derive(Debug, Clone, PartialEq)]
pub struct DistillOutput {
    pub bundle: ContinuationBundle,
    pub memories: Vec<DistilledMemory>,
}

fn sized_bundle(kind: BundleKind, body: serde_json::Value) -> Bundle {
    let token_estimate = CharCountTokenEstimator.estimate_json(&body);
    Bundle { kind, token_estimate, body }
}

/// Compile a normalized session into a continuation bundle.
///
/// The resulting bundle is injectable ([`ContinuationBundle::is_injectable`])
/// because it always carries an `Acceptance` slice.
#[must_use]
pub fn compile(session: &Session) -> ContinuationBundle {
    let mut bundle = ContinuationBundle::new(session.id.clone());

    let user_turns = session.user_turns();

    // Use the heuristic extractors to produce structured data.
    let intent = extractor::HeuristicIntentExtractor::extract_intent(session);
    let context = context_extractor::HeuristicContextExtractor::extract_context(session);
    let contract = contract_extractor::HeuristicContractExtractor::extract_contract(session);

    bundle.push(sized_bundle(
        BundleKind::Acceptance,
        json!({
            "ready": !session.messages.is_empty(),
            "scope_sized": true,
            "user_turns": user_turns,
        }),
    ));
    bundle.push(sized_bundle(
        BundleKind::Intent,
        json!({
            "goal": intent.goal,
            "acceptance_signals": intent.acceptance_signals,
            "constraints": intent.constraints,
            "user_turn_count": intent.user_turn_count,
        }),
    ));
    bundle.push(sized_bundle(
        BundleKind::Context,
        json!({
            "cwd": context.cwd,
            "title": context.title,
            "files_mentioned": context.files_mentioned,
            "key_decisions": context.key_decisions,
            "key_symbols": context.key_symbols,
            "environment_notes": context.environment_notes,
        }),
    ));
    bundle.push(ContractCompiler::new(CharCountTokenEstimator).compile(&contract));
    bundle.push(sized_bundle(
        BundleKind::Provenance,
        json!({ "corpus": session.corpus, "source_id": session.id }),
    ));
    let worklog = WorklogProjection::from_session(session);
    bundle.push(sized_bundle(
        BundleKind::Worklog,
        json!({
            "message_count": worklog.message_count,
            "unfinished": worklog.unfinished,
        }),
    ));

    bundle
}

/// Compile a session and write its intent, contract, and context to memory.
///
/// # Errors
///
/// Returns [`PortError::Backend`] if an episodic fact cannot be serialized or
/// persisted. Writes completed before an error remain persisted.
pub fn compile_and_store(
    session: &Session,
    memory_store: &dyn MemoryStore,
) -> Result<DistillOutput, PortError> {
    let bundle = compile(session);
    let memories = DistillMemoryWriter::new(memory_store).write(&bundle)?;
    Ok(DistillOutput { bundle, memories })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Message, Role};
    use crate::ports::adapters::InMemoryMemoryStore;

    #[test]
    fn compile_populates_serializable_unfinished_worklog() {
        let mut session = Session::new("crashed-session", Corpus::Codex);
        session.messages.push(Message::new(Role::User, "Finish the parser"));

        let bundle = compile(&session);
        let worklog = bundle
            .bundles
            .iter()
            .find(|slice| slice.kind == BundleKind::Worklog)
            .expect("compiled bundle should contain a worklog");
        let projection: WorklogProjection =
            serde_json::from_value(worklog.body.clone()).expect("worklog body should deserialize");

        assert_eq!(projection.unfinished.len(), 1);
        assert_eq!(projection.unfinished[0].session_id, "crashed-session");
    }

    #[test]
    fn compile_sizes_every_structured_slice() {
        let mut session = Session::new("sized-session", Corpus::Cursor);
        session.messages.push(Message::new(Role::User, "Run cargo test"));

        let bundle = compile(&session);

        assert!(bundle.bundles.iter().all(|slice| slice.token_estimate > 0));
        assert_eq!(
            bundle.total_token_estimate(),
            bundle.bundles.iter().map(|slice| slice.token_estimate).sum::<u32>()
        );
    }

    #[test]
    fn compile_and_store_exposes_the_end_to_end_distill_path() {
        let mut session = Session::new("stored-session", Corpus::Cursor);
        session.messages.push(Message::new(
            Role::User,
            "Goal: improve intent extraction\nConstraint: preserve public APIs",
        ));
        let store = InMemoryMemoryStore::default();

        let output = compile_and_store(&session, &store).expect("compile and store");

        assert!(output.bundle.is_injectable());
        assert_eq!(output.memories.len(), 3);
        assert_eq!(
            store.recall("session/stored-session/episodic", 10).expect("recall stored facts").len(),
            3
        );
    }
}
