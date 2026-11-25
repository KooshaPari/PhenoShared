//! Bundle compiler — orchestrates all four extractors over a session and
//! produces an injectable [`ContinuationBundle`].
//!
//! The compiler runs the [`IntentExtractor`], [`ContextExtractor`],
//! [`ContractExtractor`], and [`AcceptanceExtractor`] over a normalized
//! [`Session`] and assembles the results into a
//! [`ContinuationBundle`] with provenance. It also provides a method to render
//! the bundle as an injectable text payload for a new session.
//!
//! # Example
//!
//! ```rust
//! use session_ledger::distill::compiler::BundleCompiler;
//! use session_ledger::distill::extractor::HeuristicIntentExtractor;
//! use session_ledger::distill::context_extractor::HeuristicContextExtractor;
//! use session_ledger::distill::contract_extractor::HeuristicContractExtractor;
//! use session_ledger::distill::acceptance_extractor::HeuristicAcceptanceExtractor;
//! use session_ledger::domain::session::{Session, Corpus};
//!
//! let session = Session::new("test", Corpus::Forge);
//! let compiler = BundleCompiler::new(
//!     HeuristicIntentExtractor,
//!     HeuristicContextExtractor,
//!     HeuristicContractExtractor,
//!     HeuristicAcceptanceExtractor,
//! );
//! let bundle = compiler.compile(&session).expect("compilation should succeed");
//! assert!(bundle.is_injectable());
//! let text = compiler.render_injectable(&bundle).expect("bundle should render");
//! assert!(!text.is_empty());
//! ```

use crate::distill::contract_compiler::ContractCompiler;
use crate::distill::token_estimator::{CharCountTokenEstimator, TokenEstimator};
use crate::domain::acceptance::Acceptance;
use crate::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use crate::domain::context::Context;
use crate::domain::contract::Contract;
use crate::domain::intent::Intent;
use crate::domain::session::Session;
use crate::inject::{InjectRenderError, PromptRenderer};
use crate::ports::{
    AcceptanceExtractor, ContextExtractor, ContractExtractor, IntentExtractor, PortError,
};
use serde_json::json;

fn sized_bundle(kind: BundleKind, body: serde_json::Value) -> Bundle {
    let token_estimate = CharCountTokenEstimator.estimate_json(&body);
    Bundle { kind, token_estimate, body }
}

/// Compilation error.
#[derive(Debug, thiserror::Error)]
pub enum CompileError {
    #[error("extraction failed: {0}")]
    Extraction(#[from] PortError),
}

/// Orchestrator that runs all four extractors over a session and produces an
/// injectable [`ContinuationBundle`].
///
/// Generic over the four extractor types so different backends (heuristic, LLM,
/// etc.) can be injected at compile time.
#[derive(Debug, Clone)]
pub struct BundleCompiler<IE, CE, CtrE, AE> {
    intent: IE,
    context: CE,
    contract: CtrE,
    acceptance: AE,
}

impl<IE, CE, CtrE, AE> BundleCompiler<IE, CE, CtrE, AE>
where
    IE: IntentExtractor,
    CE: ContextExtractor,
    CtrE: ContractExtractor,
    AE: AcceptanceExtractor,
{
    /// Create a new compiler with the given extractors.
    #[must_use]
    pub fn new(
        intent_extractor: IE,
        context_extractor: CE,
        contract_extractor: CtrE,
        acceptance_extractor: AE,
    ) -> Self {
        Self {
            intent: intent_extractor,
            context: context_extractor,
            contract: contract_extractor,
            acceptance: acceptance_extractor,
        }
    }

    /// Run all extractors and assemble the bundle.
    ///
    /// # Errors
    /// Returns [`CompileError::Extraction`] if any extractor fails.
    pub fn compile(&self, session: &Session) -> Result<ContinuationBundle, CompileError> {
        let intent: Intent = self.intent.extract(session)?;
        let context: Context = self.context.extract(session)?;
        let contract: Contract = self.contract.extract(session)?;
        let acceptance: Acceptance = self.acceptance.extract(session)?;

        let mut bundle = ContinuationBundle::new(session.id.clone());

        // Check if session appears ready for injection.
        let ready = acceptance.satisfaction_score > 0 || !session.messages.is_empty();

        bundle.push(sized_bundle(
            BundleKind::Acceptance,
            json!({
                "ready": ready,
                "scope_sized": ready,
                "user_turns": session.user_turns(),
                "evidence": acceptance.evidence,
                "user_confirmed": acceptance.user_confirmed,
                "testing_evidence": acceptance.testing_evidence,
                "satisfaction_score": acceptance.satisfaction_score,
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

        Ok(bundle)
    }

    /// Render a compiled bundle as injectable text payload for a new session.
    ///
    /// The output is a formatted prompt suitable for a new agent session.
    ///
    /// # Errors
    ///
    /// Returns [`InjectRenderError::MissingAcceptance`] when the supplied
    /// bundle does not carry the required resume gate.
    pub fn render_injectable(
        &self,
        bundle: &ContinuationBundle,
    ) -> Result<String, InjectRenderError> {
        PromptRenderer::new().render_bundle(bundle)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distill::acceptance_extractor::HeuristicAcceptanceExtractor;
    use crate::distill::context_extractor::HeuristicContextExtractor;
    use crate::distill::contract_extractor::HeuristicContractExtractor;
    use crate::distill::extractor::HeuristicIntentExtractor;
    use crate::domain::session::{Corpus, Message, Role};

    fn sample_session() -> Session {
        let mut s = Session::new("sess-compile-test", Corpus::Forge);
        s.cwd = Some("/home/user/proj".into());
        s.title = Some("add auth".into());
        s.messages.push(Message::new(Role::User, "add JWT authentication to the API"));
        s.messages
            .push(Message::new(Role::Assistant, "I'll add jsonwebtoken and implement middleware"));
        s.messages.push(Message::new(Role::User, "looks good, all tests pass, ship it"));
        s
    }

    fn make_compiler() -> BundleCompiler<
        HeuristicIntentExtractor,
        HeuristicContextExtractor,
        HeuristicContractExtractor,
        HeuristicAcceptanceExtractor,
    > {
        BundleCompiler::new(
            HeuristicIntentExtractor,
            HeuristicContextExtractor,
            HeuristicContractExtractor,
            HeuristicAcceptanceExtractor,
        )
    }

    #[test]
    fn full_bundle_compilation_produces_all_expected_kinds() {
        let compiler = make_compiler();
        let bundle = compiler.compile(&sample_session()).expect("compilation should succeed");

        assert!(bundle.is_injectable(), "bundle must be injectable");

        for kind in [
            BundleKind::Acceptance,
            BundleKind::Intent,
            BundleKind::Context,
            BundleKind::Contract,
            BundleKind::Provenance,
        ] {
            assert!(bundle.has(kind), "missing bundle kind {kind:?}");
        }

        // Should NOT include Worklog or Dedup (not in the 4-extractor compiler).
        assert!(!bundle.has(BundleKind::Worklog));
        assert!(!bundle.has(BundleKind::Dedup));
        assert!(bundle.bundles.iter().all(|slice| slice.token_estimate > 0));
    }

    #[test]
    fn render_injectable_produces_non_empty_text() {
        let compiler = make_compiler();
        let bundle = compiler.compile(&sample_session()).expect("compilation should succeed");
        let text = compiler.render_injectable(&bundle).expect("bundle should render");

        assert!(!text.is_empty(), "injectable text must not be empty");
        assert!(text.contains("CONTINUATION PROMPT"), "must have bundle header");
        assert!(text.contains("source_id: \"sess-compile-test\""), "must contain source id");
        assert!(text.contains("ACCEPTANCE"), "must contain acceptance section");
        assert!(text.contains("INTENT"), "must contain intent section");
        assert!(text.contains("CONTEXT"), "must contain context section");
        assert!(text.contains("CONTRACT"), "must contain contract section");
        assert!(text.contains("PROVENANCE"), "must contain provenance section");
        assert!(text.contains("END SESSIONLEDGER CONTINUATION PROMPT"), "must have footer");
    }

    /// Acceptance extractor returning a fixed satisfaction score, so the
    /// `ready` boundary in `compile()` can be pinned independent of heuristics.
    struct FixedScoreAcceptance(u8);
    impl AcceptanceExtractor for FixedScoreAcceptance {
        fn extract(&self, _session: &Session) -> Result<Acceptance, PortError> {
            let mut a = Acceptance::empty();
            a.satisfaction_score = self.0;
            Ok(a)
        }
    }

    fn compiler_with_score(
        score: u8,
    ) -> BundleCompiler<
        HeuristicIntentExtractor,
        HeuristicContextExtractor,
        HeuristicContractExtractor,
        FixedScoreAcceptance,
    > {
        BundleCompiler::new(
            HeuristicIntentExtractor,
            HeuristicContextExtractor,
            HeuristicContractExtractor,
            FixedScoreAcceptance(score),
        )
    }

    fn empty_session() -> Session {
        Session::new("sess-empty", Corpus::Forge)
    }

    fn session_with_one_message() -> Session {
        let mut s = Session::new("sess-one-msg", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "hello"));
        s
    }

    /// Read the `ready` flag the compiler wrote into the Acceptance slice.
    fn ready_flag(bundle: &ContinuationBundle) -> bool {
        let slice = bundle
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Acceptance)
            .expect("acceptance slice must exist");
        slice.body.get("ready").and_then(serde_json::Value::as_bool).expect("ready must be a bool")
    }

    // `ready = satisfaction_score > 0 || !session.messages.is_empty();`
    // The four combinations below pin every operator on that line so the
    // surviving mutants (`> -> ==`, `> -> <`, `> -> >=`, `|| -> &&`, `delete !`)
    // all flip at least one asserted value.

    #[test]
    fn ready_false_when_score_zero_and_no_messages() {
        // score == 0, messages empty -> orig: false.
        // Anchors: `> -> >=` (0>=0 true), `> -> ==` (0==0 true), `delete !`
        // (is_empty() true) would each flip this to `true`.
        let bundle =
            compiler_with_score(0).compile(&empty_session()).expect("compilation should succeed");
        assert!(!ready_flag(&bundle), "empty session with score 0 must NOT be ready");
    }

    #[test]
    fn ready_true_when_score_positive_and_no_messages() {
        // score == 1, messages empty -> orig: true (via score > 0).
        // Anchors: `> -> <` (1<0 false) and `|| -> &&` (true && false) would
        // each flip this to `false`.
        let bundle =
            compiler_with_score(1).compile(&empty_session()).expect("compilation should succeed");
        assert!(ready_flag(&bundle), "score 1 must be ready even with no messages");
    }

    #[test]
    fn ready_true_when_score_zero_but_messages_present() {
        // score == 0, messages non-empty -> orig: true (via !is_empty()).
        // Anchors: `|| -> &&` (false && true) and `delete !` (false || is_empty()
        // = false) would each flip this to `false`.
        let bundle = compiler_with_score(0)
            .compile(&session_with_one_message())
            .expect("compilation should succeed");
        assert!(ready_flag(&bundle), "non-empty session must be ready even at score 0");
    }

    #[test]
    fn ready_flag_mirrors_into_scope_sized() {
        // `scope_sized` is derived from the same `ready` value; assert they track
        // together across the boundary so a mutation on line 100 can't silently
        // desync the two fields.
        let unready =
            compiler_with_score(0).compile(&empty_session()).expect("compilation should succeed");
        let unready_slice = unready
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Acceptance)
            .expect("acceptance slice");
        assert_eq!(
            unready_slice.body.get("scope_sized").and_then(serde_json::Value::as_bool),
            Some(false)
        );

        let ready = compiler_with_score(1)
            .compile(&session_with_one_message())
            .expect("compilation should succeed");
        let ready_slice = ready
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Acceptance)
            .expect("acceptance slice");
        assert_eq!(
            ready_slice.body.get("scope_sized").and_then(serde_json::Value::as_bool),
            Some(true)
        );
    }

    #[test]
    fn compiler_rejects_on_extractor_failure() {
        // Use a compiler where an extractor always fails.
        use crate::ports::PortError;
        struct FailingExtractor;
        impl IntentExtractor for FailingExtractor {
            fn extract(&self, _session: &Session) -> Result<Intent, PortError> {
                Err(PortError::Backend("simulated failure".to_string()))
            }
        }

        let compiler = BundleCompiler::new(
            FailingExtractor,
            HeuristicContextExtractor,
            HeuristicContractExtractor,
            HeuristicAcceptanceExtractor,
        );
        let result = compiler.compile(&sample_session());
        assert!(result.is_err(), "should fail when an extractor fails");
    }
}
