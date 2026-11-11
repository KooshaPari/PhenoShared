//! Native Discord composition root. No helper process or live configuration writes.
use anyhow::Result;
use phinbox::{
    discord::{run_gateway, Config, DiscordClient, InteractionHandler, Mirror},
    management::Store,
};
use std::{path::Path, time::Duration};

pub fn run(root: &Path, path: &Path, once: bool) -> Result<serde_json::Value> {
    let config = Config::load(path)?;
    let store = Store::open(root.join("management.sqlite"))?;
    store.observe_inbox(root)?;
    let client = DiscordClient::from_config(&config)?;
    let mirror = Mirror::new(store.clone(), config.clone(), client.clone())?;
    let handler = InteractionHandler::new(store.clone(), config, client)?;
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()?;
    let root = root.to_path_buf();
    runtime.block_on(async move {
        if once {
            return Ok(serde_json::json!({"projected":mirror.sync_once().await?}));
        }
        // Separate tasks keep Gateway heartbeat/ACK processing live during REST retries.
        let mut gateway = tokio::spawn(run_gateway(handler));
        let observer = store.clone();
        let mut projector = tokio::spawn(async move {
            loop {
                if observer.observe_inbox(&root).is_err() {
                    eprintln!("phinbox: workflow observation failed; retrying");
                }
                if mirror.sync_once().await.is_err() {
                    eprintln!("phinbox: Discord projection incomplete; durable retry pending");
                }
                tokio::time::sleep(Duration::from_secs(5)).await;
            }
        });
        let result: Result<serde_json::Value> = loop {
            tokio::select! {
                result=&mut gateway=>break match result {
                    Ok(result)=>result.map(|()|serde_json::json!({"stopped":true})),
                    Err(_)=>Err(anyhow::anyhow!("Discord Gateway task failed")),
                },
                _=tokio::signal::ctrl_c()=>break Ok(serde_json::json!({"stopped":true})),
                _=&mut projector=>break Err(anyhow::anyhow!("Discord projector task failed")),
            }
        };
        if !gateway.is_finished() {
            gateway.abort();
            let _ = gateway.await;
        }
        if !projector.is_finished() {
            projector.abort();
            let _ = projector.await;
        }
        result
    })
}
