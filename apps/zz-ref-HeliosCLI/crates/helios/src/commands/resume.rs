// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `resume` subcommand handler.

use anyhow::{Context, Result};

/// Resume a previous chat session.
pub fn cmd_resume(last: bool, session_id: Option<String>) -> Result<()> {
    use helios_ai::{load_last_session, load_session, session_from_record, session_path};

    if !last && session_id.is_none() {
        anyhow::bail!("Specify --last to resume the most recent session, or --session-id <uuid>");
    }

    let record = if last {
        println!("[helios:resume] Loading most recent session...");
        match load_last_session()? {
            Some(r) => r,
            None => {
                anyhow::bail!("No saved sessions found in ~/.helios/sessions/");
            }
        }
    } else {
        let id_str = session_id.unwrap();
        let id: uuid::Uuid = id_str.parse().context("Invalid session UUID")?;
        let path = session_path(&id)?;
        println!("[helios:resume] Loading session {}...", id);
        load_session(&path)?
    };

    println!("[helios:resume] Session ID:    {}", record.id);
    println!("[helios:resume] Created:       {}", record.created_at);
    println!("[helios:resume] Last saved:    {}", record.saved_at);
    println!("[helios:resume] Model:         {}", record.config.model);
    println!("[helios:resume] Messages:      {}", record.messages.len());
    println!();

    let _session = session_from_record(&record).context("Failed to reconstruct session")?;

    println!("[helios:resume] Session restored successfully.");
    println!(
        "[helios:resume] Use 'helios ask --chat' or 'helios exec' to continue the conversation."
    );

    Ok(())
}
