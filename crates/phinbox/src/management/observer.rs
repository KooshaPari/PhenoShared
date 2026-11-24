use super::{Action, Command, Item, Status, Store};
use crate::{
    inbox::{PendingRequest, RequestState},
    spec::{FieldSpec, Urgency},
};
use anyhow::Result;
use std::path::Path;

impl Store {
    /// Reconcile durable files, including changes made by other CLI/native processes.
    /// Secret prompts and all answer values are excluded from management projection.
    /// No inbox file is ever written by this observer or by management actions.
    pub fn observe_inbox(&self, root: &Path) -> Result<usize> {
        let mut observed = 0;
        for subdir in ["inbox", "answered"] {
            let dir = root.join(subdir);
            if !dir.exists() {
                continue;
            }
            for entry in std::fs::read_dir(dir)? {
                let path = entry?.path();
                if path.extension().and_then(|s| s.to_str()) != Some("json") {
                    continue;
                }
                let bytes = match std::fs::read(&path) {
                    Ok(b) => b,
                    Err(_) => continue,
                };
                let request: PendingRequest = match serde_json::from_slice(&bytes) {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let restricted = matches!(request.spec.urgency, Urgency::Secret)
                    || matches!(request.spec.field, FieldSpec::Text { secret: true, .. });
                let id = format!("inbox:{}", request.request_id);
                let existing = self.get(&id)?;
                let mut item = if let Some(i) = existing {
                    i
                } else {
                    let original = if restricted {
                        "Restricted elicitation item: open the local Phinbox inbox to review. Authored secret content and answers are not exported.".to_string()
                    } else {
                        serde_json::to_string_pretty(&request.spec)?
                    };
                    let mut i = Item::new(&id, original);
                    i.title = if restricted {
                        "Restricted elicitation item".into()
                    } else {
                        request.spec.title.clone()
                    };
                    if restricted {
                        i.status = Status::Blocked;
                    }
                    i.source_request_id = Some(request.request_id.clone());
                    self.create(i)?
                };
                let terminal = matches!(
                    request.state,
                    RequestState::Answered | RequestState::Cancelled | RequestState::Expired
                ) || request.is_expired_now();
                if terminal && item.status != Status::Closed {
                    item = self.apply(Command {
                        event_id: format!("inbox-terminal:{}", request.request_id),
                        item_id: id,
                        expected_revision: item.revision,
                        actor: "inbox-observer".into(),
                        action: Action::Close,
                    })?;
                }
                let _ = item;
                observed += 1;
            }
        }
        Ok(observed)
    }
}
