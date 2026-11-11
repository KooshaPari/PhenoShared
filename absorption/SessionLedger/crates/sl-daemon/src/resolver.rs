//! Native-agent session resolution shared by ShareCLI and SessionLedger.
//!
//! The daemon deliberately accepts evidence rather than process handles. This
//! keeps the wire contract portable and lets the caller gather platform-specific
//! facts (PID, tty, argv, cwd) without giving the daemon authority to inspect or
//! control processes.

use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use std::{
    fs::OpenOptions,
    io::{BufRead, BufReader, Write},
};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub struct ProcessEvidence {
    pub executable: Option<String>,
    pub executable_fingerprint: Option<String>,
    pub argv: Vec<String>,
    pub environment: Vec<(String, String)>,
    pub cwd: Option<String>,
    pub pid: Option<u32>,
    pub tty: Option<String>,
    pub started_at: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ResumeRecipe {
    pub executable: String,
    pub args: Vec<String>,
    pub cwd: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct AgentSession {
    pub session_id: String,
    pub harness: String,
    pub cwd: Option<String>,
    pub pid: Option<u32>,
    pub tty: Option<String>,
    pub resume: ResumeRecipe,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ResolutionConfidence {
    Exact,
    Corroborated,
    Heuristic,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct SessionCandidate {
    pub session: AgentSession,
    pub confidence: ResolutionConfidence,
    pub matched_fields: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ResolveRequest {
    pub evidence: ProcessEvidence,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq, Eq)]
pub struct ResolveResponse {
    pub candidates: Vec<SessionCandidate>,
}

#[derive(Clone)]
pub struct Resolver {
    sessions: Arc<RwLock<Vec<AgentSession>>>,
    persistence: Option<Arc<PathBuf>>,
}

impl Resolver {
    pub fn open(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref().to_owned();
        let mut sessions: Vec<AgentSession> = Vec::new();
        if let Ok(file) = std::fs::File::open(&path) {
            for line in BufReader::new(file).lines().map_while(Result::ok) {
                if let Ok(session) = serde_json::from_str::<AgentSession>(&line) {
                    sessions.retain(|existing| existing.session_id != session.session_id);
                    sessions.push(session);
                }
            }
        }
        Ok(Self { sessions: Arc::new(RwLock::new(sessions)), persistence: Some(Arc::new(path)) })
    }

    pub fn register(&self, session: AgentSession) -> std::io::Result<()> {
        let mut sessions = self.sessions.write().expect("resolver lock poisoned");
        if let Some(path) = &self.persistence {
            let encoded = serde_json::to_string(&session).expect("serializable");
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let mut file = OpenOptions::new().create(true).append(true).open(path.as_ref())?;
            writeln!(file, "{encoded}")?;
        }
        sessions.retain(|existing| existing.session_id != session.session_id);
        sessions.push(session);
        Ok(())
    }

    pub fn resolve(&self, evidence: &ProcessEvidence) -> ResolveResponse {
        let sessions = self.sessions.read().expect("resolver lock poisoned");
        let mut candidates =
            sessions.iter().filter_map(|session| score(session, evidence)).collect::<Vec<_>>();
        candidates
            .sort_by_key(|candidate| std::cmp::Reverse(confidence_rank(&candidate.confidence)));
        ResolveResponse { candidates }
    }
}

impl Default for Resolver {
    fn default() -> Self {
        Self { sessions: Arc::new(RwLock::new(Vec::new())), persistence: None }
    }
}

fn score(session: &AgentSession, evidence: &ProcessEvidence) -> Option<SessionCandidate> {
    let mut matched = Vec::new();
    if let (Some(pid), Some(expected)) = (evidence.pid, session.pid) {
        if pid == expected {
            matched.push("pid".into());
        }
    }
    if let (Some(tty), Some(expected)) = (evidence.tty.as_ref(), session.tty.as_ref()) {
        if tty == expected {
            matched.push("tty".into());
        }
    }
    if let (Some(cwd), Some(expected)) = (evidence.cwd.as_ref(), session.cwd.as_ref()) {
        if cwd == expected {
            matched.push("cwd".into());
        }
    }
    if matched.is_empty() {
        return None;
    }
    let confidence = if matched.iter().any(|f| f == "pid") && matched.iter().any(|f| f == "tty") {
        ResolutionConfidence::Exact
    } else if matched.len() >= 2 {
        ResolutionConfidence::Corroborated
    } else {
        ResolutionConfidence::Heuristic
    };
    Some(SessionCandidate { session: session.clone(), confidence, matched_fields: matched })
}

fn confidence_rank(confidence: &ResolutionConfidence) -> u8 {
    match confidence {
        ResolutionConfidence::Exact => 3,
        ResolutionConfidence::Corroborated => 2,
        ResolutionConfidence::Heuristic => 1,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn session() -> AgentSession {
        AgentSession {
            session_id: "s1".into(),
            harness: "codex".into(),
            cwd: Some("/tmp/project".into()),
            pid: Some(42),
            tty: Some("ttys001".into()),
            resume: ResumeRecipe {
                executable: "codex".into(),
                args: vec!["resume".into(), "s1".into()],
                cwd: Some("/tmp/project".into()),
            },
        }
    }

    #[test]
    fn exact_pid_and_tty_match_wins() {
        let resolver = Resolver::default();
        resolver.register(session()).unwrap();
        let response = resolver.resolve(&ProcessEvidence {
            pid: Some(42),
            tty: Some("ttys001".into()),
            cwd: Some("/tmp/project".into()),
            ..Default::default()
        });
        assert_eq!(response.candidates[0].confidence, ResolutionConfidence::Exact);
    }

    #[test]
    fn unrelated_evidence_returns_no_candidate() {
        let resolver = Resolver::default();
        resolver.register(session()).unwrap();
        let response = resolver.resolve(&ProcessEvidence {
            pid: Some(7),
            cwd: Some("/other".into()),
            ..Default::default()
        });
        assert!(response.candidates.is_empty());
    }

    #[test]
    fn file_registry_survives_reopen() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("native-sessions.jsonl");
        let resolver = Resolver::open(&path).unwrap();
        resolver.register(session()).unwrap();
        drop(resolver);
        let reopened = Resolver::open(&path).unwrap();
        assert_eq!(
            reopened
                .resolve(&ProcessEvidence {
                    pid: Some(42),
                    tty: Some("ttys001".into()),
                    ..Default::default()
                })
                .candidates
                .len(),
            1
        );
    }
}
