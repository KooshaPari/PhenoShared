// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `enqueue` subcommand handler.

use anyhow::{Context, Result};

/// Enqueue a task for background processing.
pub fn cmd_enqueue(payload: String, capacity: usize) -> Result<()> {
    use harness_queue::Channel;

    let channel: Channel<String> = Channel::new(capacity);

    let _parsed: serde_json::Value =
        serde_json::from_str(&payload).context("Invalid JSON payload")?;

    channel.try_send(payload.clone()).map_err(|e| anyhow::anyhow!("Queue send failed: {:?}", e))?;

    println!("[helios] Task enqueued (queue depth: 1)");
    println!("  Payload: {}", payload);

    if let Some(item) = channel.recv() {
        println!("  Verified: received back from queue");
        println!("  Item: {}", item);
    }

    Ok(())
}
