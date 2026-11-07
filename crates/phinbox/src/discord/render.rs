use crate::management::{Item, Status};
use anyhow::{bail, Result};
use serde_json::{json, Value};

pub fn custom_id(item: &Item, action: &str) -> Result<String> {
    if item.id.is_empty() {
        bail!("empty management identifier");
    }
    let encoded = item
        .id
        .bytes()
        .map(|b| {
            if b.is_ascii_alphanumeric() || b == b'-' || b == b'_' {
                char::from(b).to_string()
            } else {
                format!("~{b:02x}")
            }
        })
        .collect::<String>();
    let id = format!("phinbox:v1:{}:{}:{action}", encoded, item.revision);
    if id.len() > 100 {
        bail!("Discord component identifier too long");
    }
    Ok(id)
}
pub(super) fn marker(item: &Item) -> Result<String> {
    custom_id(item, "marker")?;
    Ok(format!("phinbox:{}", item.id))
}
fn clipped(s: &str, max: usize) -> String {
    s.chars().take(max).collect()
}
pub fn render_message(item: &Item) -> Result<Value> {
    // Full original and full lane/ETA are included by request_item as unabridged attachments.
    let content=format!("**{}**\nWorkflow: {:?} | revision {}\nAcknowledged: {}\nLane: {} | ETA: {}\nAssignee: {}\nManagement only; no permission granted.",
        clipped(&item.title,500),item.status,item.revision,item.acknowledged,
        clipped(item.lane.as_deref().unwrap_or("unassigned"),120),
        clipped(item.eta.as_deref().unwrap_or("unknown"),120),
        clipped(item.assignee.as_deref().unwrap_or("unassigned"),100));
    let closed = item.status == Status::Closed;
    let mut buttons = Vec::new();
    for (label, action, style) in [
        ("Acknowledge", "ack", 2),
        ("Assign to me", "assign", 1),
        ("Defer", "defer", 2),
        ("Close workflow", "close", 4),
    ] {
        buttons.push(json!({"type":2,"style":style,"label":label,"custom_id":custom_id(item,action)?,"disabled":closed}));
    }
    let options = [
        "open", "running", "waiting", "deferred", "partial", "blocked",
    ]
    .into_iter()
    .map(|s| json!({"label":s,"value":s}))
    .collect::<Vec<_>>();
    Ok(json!({"content":content,"allowed_mentions":{"parse":[]},
        "embeds":[{"footer":{"text":marker(item)?}}],
        "components":[{"type":1,"components":buttons},
            {"type":1,"components":[{"type":3,"custom_id":custom_id(item,"status")?,
                "min_values":1,"max_values":1,"disabled":closed,"options":options}]}]}))
}
pub(super) fn thread_name(item: &Item) -> Result<String> {
    let prefix = marker(item)?;
    Ok(clipped(
        &format!("{prefix} {}", item.title.replace(['\r', '\n'], " ")),
        100,
    ))
}

pub(super) fn decode_id(encoded: &str) -> Result<String> {
    let bytes = encoded.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    fn nibble(b: u8) -> Result<u8> {
        match b {
            b'0'..=b'9' => Ok(b - b'0'),
            b'a'..=b'f' => Ok(b - b'a' + 10),
            _ => bail!("invalid item encoding"),
        }
    }
    while i < bytes.len() {
        if bytes[i] == b'~' {
            if i + 2 >= bytes.len() {
                bail!("invalid item encoding");
            }
            out.push(nibble(bytes[i + 1])? * 16 + nibble(bytes[i + 2])?);
            i += 3;
        } else if bytes[i].is_ascii_alphanumeric() || matches!(bytes[i], b'-' | b'_') {
            out.push(bytes[i]);
            i += 1;
        } else {
            bail!("invalid item encoding");
        }
    }
    Ok(String::from_utf8(out)?)
}
