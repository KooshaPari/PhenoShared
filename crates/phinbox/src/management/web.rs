use super::Store;
use anyhow::Result;

/// Read-only inbox view backed by the same ledger used by CLI and Discord.
pub fn render(store: &Store) -> Result<String> {
    let mut rows = String::new();
    for item in store.list()? {
        rows.push_str(&format!("<tr><td>{}</td><td>{}</td><td>{:?}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
            escape(&item.id),escape(&item.title),item.status,item.revision,
            escape(item.lane.as_deref().unwrap_or("")),escape(item.eta.as_deref().unwrap_or("")),escape(item.assignee.as_deref().unwrap_or(""))));
    }
    Ok(format!("<!doctype html><html lang=en><meta charset=utf-8><title>Phinbox management</title><body><h1>Management workflow</h1><p>Management status never grants a harness permission. <a href=/inbox>Decision inbox</a> | <a href=/api/management>JSON ledger view</a></p><table><thead><tr><th>Item</th><th>Title</th><th>Status</th><th>Revision</th><th>Lane</th><th>ETA</th><th>Assignee</th></tr></thead><tbody>{rows}</tbody></table></body></html>"))
}
fn escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}
