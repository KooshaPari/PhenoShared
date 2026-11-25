//! Distilled Memory wiki tab.
//!
//! A wiki / docs-style view of distilled facts extracted from sessions:
//! intents (goals, signals, constraints), context (files, decisions, symbols,
//! environment), contracts (criteria, tests, do-not-touch), and acceptance
//! evidence.

use dioxus::prelude::*;

use session_ledger::domain::acceptance::Acceptance;
use session_ledger::domain::context::Context;
use session_ledger::domain::contract::Contract;
use session_ledger::domain::intent::Intent;

use crate::app::SessionContext;
use session_ledger::distill::acceptance_extractor::HeuristicAcceptanceExtractor;
use session_ledger::distill::context_extractor::HeuristicContextExtractor;
use session_ledger::distill::contract_extractor::HeuristicContractExtractor;
use session_ledger::distill::extractor::HeuristicIntentExtractor;

/// A single wiki page representing the distilled memory for one session.
#[derive(Debug, Clone, PartialEq)]
pub struct MemoryWikiPage {
    pub session_id: String,
    pub title: Option<String>,
    pub intent: Intent,
    pub context: Context,
    pub contract: Contract,
    pub acceptance: Acceptance,
}

/// Derive a wiki page from a session by running the heuristic extractors.
#[must_use]
pub fn to_wiki_page(session: &session_ledger::domain::session::Session) -> MemoryWikiPage {
    let intent = HeuristicIntentExtractor::extract_intent(session);
    let context = HeuristicContextExtractor::extract_context(session);
    let contract = HeuristicContractExtractor::extract_contract(session);
    let acceptance = HeuristicAcceptanceExtractor::extract_acceptance(session);

    MemoryWikiPage {
        session_id: session.id.clone(),
        title: session.title.clone(),
        intent,
        context,
        contract,
        acceptance,
    }
}

/// Build wiki pages from real sessions via context.
#[must_use]
pub fn all_wiki_pages_from_sessions(
    sessions: &[session_ledger::domain::session::Session],
) -> Vec<MemoryWikiPage> {
    sessions.iter().map(to_wiki_page).collect()
}

/// The main Memory Wiki component.
#[component]
pub fn MemoryWiki() -> Element {
    let ctx = use_context::<SessionContext>();
    // Reactive read: re-runs on every render that sees a session signal
    // change. Mirrors the HistoryTimeline fix — `use_signal(move || ...)`
    // initializer only runs once at mount, so the previous code froze on
    // the initial empty value.
    let pages = all_wiki_pages_from_sessions(&ctx.0.read());
    let mut selected_idx: Signal<Option<usize>> = use_signal(|| None);

    let selected = selected_idx().and_then(|idx| pages.get(idx)).map(|r| (*r).clone());

    rsx! {
        style { r#"
            .wiki-entry {{
                padding: 14px 20px;
                cursor: pointer;
                border-bottom: 1px solid #1e2029;
                transition: background 0.15s;
            }}
            .wiki-entry:hover {{ background: #1c1f2b; }}
            .wiki-entry.selected {{ background: #252836; border-left: 3px solid #4ade80; }}
            .wiki-entry .wiki-title {{
                font-size: 14px; font-weight: 600; color: #e1e4ea;
            }}
            .wiki-entry .wiki-id {{
                font-size: 11px; color: #8b8fa3; font-family: monospace; margin-top: 2px;
            }}
            .wiki-entry .wiki-tags {{
                margin-top: 6px; display: flex; gap: 6px; flex-wrap: wrap;
            }}
            .wiki-tag {{
                display: inline-block; padding: 1px 7px; border-radius: 4px;
                font-size: 10px; font-weight: 600;
            }}
            .wiki-tag-goal {{ background: #1a3a2a; color: #4ade80; }}
            .wiki-tag-decisions {{ background: #1a2a3a; color: #60a5fa; }}
            .wiki-tag-files {{ background: #2a1a3a; color: #c084fc; }}
            .wiki-tag-acceptance {{ background: #2a2a1a; color: #facc15; }}
            .wiki-tag-contract {{ background: #1a2a2a; color: #2dd4bf; }}
            .wiki-page {{
                flex: 1; overflow-y: auto; padding: 32px 40px;
            }}
            .wiki-page h1 {{
                font-size: 18px; font-weight: 600; margin: 0 0 24px 0; color: #e1e4ea;
            }}
            .wiki-card {{
                background: #1a1c26; border-radius: 8px; padding: 20px; margin-bottom: 16px;
                border: 1px solid #2a2d35;
            }}
            .wiki-card h2 {{
                font-size: 13px; font-weight: 600; text-transform: uppercase;
                letter-spacing: 0.5px; color: #6c8cff; margin: 0 0 12px 0;
            }}
            .wiki-card h3 {{
                font-size: 12px; font-weight: 600; color: #8b8fa3; margin: 12px 0 4px 0;
            }}
            .wiki-card p {{
                font-size: 14px; line-height: 1.6; margin: 0; color: #c8cdd6;
            }}
            .wiki-card ul {{
                margin: 4px 0 0 0; padding-left: 18px;
            }}
            .wiki-card li {{
                font-size: 13px; line-height: 1.7; color: #a1a6b5;
            }}
            .wiki-card .score-bar {{
                height: 6px; border-radius: 3px; background: #2a2d35; margin-top: 8px; overflow: hidden;
            }}
            .wiki-card .score-fill {{
                height: 100%; border-radius: 3px; background: linear-gradient(90deg, #4ade80, #22d3ee);
                transition: width 0.3s;
            }}
            .wiki-empty {{
                flex: 1; display: flex; align-items: center; justify-content: center;
                color: #8b8fa3; font-size: 14px;
            }}
        "# }
        div { class: "sidebar",
            h2 { "Distilled Memory" }
            for (i, page) in pages.iter().enumerate() {
                WikiRow {
                    key: "{page.session_id}",
                    page: page.clone(),
                    is_selected: selected_idx() == Some(i),
                    on_click: move |_| { selected_idx.set(Some(i)); },
                }
            }
        }
        match selected {
            Some(ref page) => rsx! { WikiPageDetail { page: page.clone() } },
            None => rsx! {
                div { class: "wiki-empty", "Select a memory entry to view its distilled facts" }
            },
        }
    }
}

/// A single row in the wiki sidebar.
#[component]
fn WikiRow(page: MemoryWikiPage, is_selected: bool, on_click: EventHandler<()>) -> Element {
    let sel_class = if is_selected { " selected" } else { "" };
    let title_text = page.title.clone().unwrap_or_else(|| "(untitled)".into());

    let mut tags: Vec<&'static str> = Vec::new();
    if page.intent.goal.is_some() {
        tags.push("goal");
    }
    if !page.context.key_decisions.is_empty() {
        tags.push("decisions");
    }
    if !page.context.files_mentioned.is_empty() {
        tags.push("files");
    }
    if !page.acceptance.evidence.is_empty() {
        tags.push("acceptance");
    }
    if !page.contract.success_criteria.is_empty() {
        tags.push("contract");
    }

    rsx! {
        div {
            class: "wiki-entry{sel_class}",
            onclick: move |_| on_click.call(()),
            div { class: "wiki-title",
                "{title_text}"
            }
            div { class: "wiki-id", "{page.session_id}" }
            div { class: "wiki-tags",
                for tag in &tags {
                    span { class: "wiki-tag wiki-tag-{tag}", "{tag}" }
                }
            }
        }
    }
}

/// Full wiki page detail — all distilled facts for one session.
#[component]
fn WikiPageDetail(page: MemoryWikiPage) -> Element {
    let title_text = page.title.clone().unwrap_or_else(|| "Distilled Memory".into());
    let confirmation_text =
        if page.acceptance.user_confirmed { "user confirmed" } else { "no explicit confirmation" };

    rsx! {
        div { class: "wiki-page",
            h1 { "{title_text}" }

            // --- Intent card ---
            div { class: "wiki-card",
                h2 { "Intent" }
                if let Some(ref goal) = page.intent.goal {
                    h3 { "Goal" }
                    p { "{goal}" }
                }
                if !page.intent.acceptance_signals.is_empty() {
                    h3 { "Acceptance Signals" }
                    ul {
                        for sig in &page.intent.acceptance_signals {
                            li { "{sig}" }
                        }
                    }
                }
                if !page.intent.constraints.is_empty() {
                    h3 { "Constraints" }
                    ul {
                        for c in &page.intent.constraints {
                            li { "{c}" }
                        }
                    }
                }
                p { "User turns: {page.intent.user_turn_count}" }
            }

            // --- Context card ---
            div { class: "wiki-card",
                h2 { "Working Context" }
                if let Some(ref cwd) = page.context.cwd {
                    h3 { "Directory" }
                    p { "{cwd}" }
                }
                if let Some(ref title) = page.context.title {
                    h3 { "Title" }
                    p { "{title}" }
                }
                if !page.context.files_mentioned.is_empty() {
                    h3 { "Files Mentioned" }
                    ul {
                        for f in &page.context.files_mentioned {
                            li { "{f}" }
                        }
                    }
                }
                if !page.context.key_decisions.is_empty() {
                    h3 { "Key Decisions" }
                    ul {
                        for d in &page.context.key_decisions {
                            li {
                                "{d.summary}"
                                if let Some(ref rationale) = d.rationale {
                                    br {}
                                    span { "(context: {rationale})" }
                                }
                            }
                        }
                    }
                }
                if !page.context.key_symbols.is_empty() {
                    h3 { "Key Symbols" }
                    ul {
                        for sym in &page.context.key_symbols {
                            li { "{sym}" }
                        }
                    }
                }
                if !page.context.environment_notes.is_empty() {
                    h3 { "Environment" }
                    ul {
                        for note in &page.context.environment_notes {
                            li { "{note}" }
                        }
                    }
                }
            }

            // --- Contract card ---
            if !page.contract.is_empty() {
                div { class: "wiki-card",
                    h2 { "Contract" }
                    if !page.contract.success_criteria.is_empty() {
                        h3 { "Success Criteria" }
                        ul {
                            for c in &page.contract.success_criteria {
                                li { "{c}" }
                            }
                        }
                    }
                    if !page.contract.tests_or_verifications.is_empty() {
                        h3 { "Tests / Verifications" }
                        ul {
                            for t in &page.contract.tests_or_verifications {
                                li { "{t}" }
                            }
                        }
                    }
                    if !page.contract.constraints.is_empty() {
                        h3 { "Constraints" }
                        ul {
                            for c in &page.contract.constraints {
                                li { "{c}" }
                            }
                        }
                    }
                    if !page.contract.do_not_touch.is_empty() {
                        h3 { "Do Not Touch" }
                        ul {
                            for d in &page.contract.do_not_touch {
                                li { "{d}" }
                            }
                        }
                    }
                }
            }

            // --- Acceptance card ---
            if !page.acceptance.is_empty() {
                div { class: "wiki-card",
                    h2 { "Acceptance Evidence" }
                    if !page.acceptance.evidence.is_empty() {
                        h3 { "Evidence" }
                        ul {
                            for e in &page.acceptance.evidence {
                                li { "{e}" }
                            }
                        }
                    }
                    if !page.acceptance.testing_evidence.is_empty() {
                        h3 { "Testing Evidence" }
                        ul {
                            for t in &page.acceptance.testing_evidence {
                                li { "{t}" }
                            }
                        }
                    }
                    h3 { "Satisfaction Score" }
                    div { class: "score-bar",
                        div {
                            class: "score-fill",
                            style: "width: {page.acceptance.satisfaction_score}%",
                        }
                    }
                    p { "{page.acceptance.satisfaction_score}/100 — {confirmation_text}" }
                }
            }
        }
    }
}
