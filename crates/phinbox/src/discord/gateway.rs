use super::{DiscordClient, InteractionHandler};
use anyhow::{bail, Context, Result};
use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use tokio_tungstenite::{connect_async, tungstenite::Message};

/// Opt-in elected receiver using the existing Instinct identity, never a new bot.
pub async fn run_gateway(handler: InteractionHandler) -> Result<()> {
    if handler.config.receiver_owner != "phinbox" {
        bail!("Phinbox Gateway receiver not explicitly elected");
    }
    handler.config.validate_board()?;
    handler.client.verify(&handler.config).await?;
    let app = handler
        .client
        .request(reqwest::Method::GET, "/oauth2/applications/@me", None)
        .await?;
    if !app["interactions_endpoint_url"].is_null() {
        bail!("existing Discord application is configured for HTTP interactions; Gateway activation refused");
    }
    let owner = uuid::Uuid::new_v4().to_string();
    let _cleanup = ReceiverGuard {
        store: handler.store.clone(),
        owner: owner.clone(),
    };
    let mut session: Option<(String, String)> = None;
    let mut sequence: Option<u64> = None;
    loop {
        if !handler.store.acquire_receiver_lease(
            &owner,
            u64::try_from(chrono::Utc::now().timestamp_millis())?,
            30_000,
        )? {
            bail!("another native Gateway receiver holds lease");
        }
        let result = connection(&handler, &owner, &mut session, &mut sequence).await;
        match result {
            Ok(()) => {},
            Err(error) if error.downcast_ref::<FatalGateway>().is_some() => return Err(error),
            Err(error) => {
                tracing::warn!(
                    "Discord Gateway connection lost; retrying without event/token detail"
                );
                drop(error);
            },
        }
        tokio::time::sleep(std::time::Duration::from_secs(5)).await;
    }
}
async fn connection(
    handler: &InteractionHandler,
    owner: &str,
    session: &mut Option<(String, String)>,
    seq: &mut Option<u64>,
) -> Result<()> {
    let url = if let Some((_, resume)) = session.as_ref() {
        resume.clone()
    } else {
        handler.client.gateway_url().await?
    };
    let (mut ws, _) = connect_async(&url)
        .await
        .map_err(|_| anyhow::anyhow!("Gateway connection failed"))?;
    let hello = tokio::time::timeout(std::time::Duration::from_secs(8), ws.next())
        .await
        .context("Gateway hello timeout")?
        .context("Gateway closed before hello")?
        .map_err(|_| anyhow::anyhow!("Gateway hello failed"))?;
    let hello: Value = serde_json::from_str(hello.to_text().context("Gateway hello is not text")?)
        .context("Gateway hello invalid")?;
    if hello["op"] != 10 {
        bail!("Gateway hello opcode missing");
    }
    let interval = hello["d"]["heartbeat_interval"]
        .as_u64()
        .context("Gateway heartbeat interval missing")?;
    if !(1000..=120_000).contains(&interval) {
        bail!("unsafe Gateway heartbeat interval");
    }
    let token = DiscordClient::gateway_token(&handler.config.credential_file)?;
    let identify = if let Some((id, _)) = session.as_ref() {
        json!({"op":6,"d":{"token":token,"session_id":id,"seq":seq}})
    } else {
        json!({"op":2,"d":{"token":token,"intents":1,"properties":{"os":std::env::consts::OS,"browser":"phinbox","device":"phinbox"}}})
    };
    ws.send(Message::Text(identify.to_string().into()))
        .await
        .map_err(|_| anyhow::anyhow!("Gateway identify failed"))?;
    let mut beat = tokio::time::interval(std::time::Duration::from_millis(interval));
    let mut renewal = tokio::time::interval(std::time::Duration::from_secs(5));
    let mut awaiting_ack = false;
    loop {
        tokio::select! {
            _=renewal.tick()=>{
                if !handler.store.acquire_receiver_lease(owner,u64::try_from(chrono::Utc::now().timestamp_millis())?,30_000)? {bail!("Gateway receiver lease lost");}
            }
            _=beat.tick()=>{
                if awaiting_ack {bail!("Gateway heartbeat acknowledgement missing");}
                ws.send(Message::Text(json!({"op":1,"d":seq}).to_string().into())).await.map_err(|_|anyhow::anyhow!("Gateway heartbeat failed"))?;
                awaiting_ack=true;
            }
            incoming=ws.next()=>{
                let Some(incoming)=incoming else {bail!("Gateway disconnected");};
                let incoming=incoming.map_err(|_|anyhow::anyhow!("Gateway receive failed"))?;
                if let Message::Close(close)=incoming {
                    if close.as_ref().is_some_and(|c|matches!(u16::from(c.code),4004|4010|4011|4013|4014)) {
                        // Stop identifying on invalid credentials/intents/sharding.
                        *session=None;handler.store.release_receiver_lease(owner)?;return Err(FatalGateway.into());
                    }
                    bail!("Gateway closed");
                }
                if let Message::Ping(bytes)=incoming {ws.send(Message::Pong(bytes)).await.map_err(|_|anyhow::anyhow!("Gateway pong failed"))?;continue;}
                let Message::Text(text)=incoming else {continue};
                let event:Value=serde_json::from_str(&text).context("Gateway event invalid")?;
                if let Some(s)=event["s"].as_u64(){*seq=Some(s);}
                match event["op"].as_u64() {
                    Some(11)=>awaiting_ack=false,
                    Some(1)=>{ws.send(Message::Text(json!({"op":1,"d":seq}).to_string().into())).await.map_err(|_|anyhow::anyhow!("Gateway requested heartbeat failed"))?;}
                    Some(7)=>return Ok(()),
                    Some(9)=>{if event["d"]!=true {*session=None;*seq=None;}return Ok(());}
                    Some(0)=>match event["t"].as_str() {
                        Some("READY")=>{
                            let d=&event["d"];
                            if d["user"]["id"].as_str()!=Some(&handler.config.binding.application_id) {bail!("Gateway READY identity mismatch");}
                            let resume=d["resume_gateway_url"].as_str().context("Gateway resume URL missing")?;
                            let resume=handler.client.gateway_endpoint(resume).map_err(|_|FatalGateway)?;
                            *session=Some((d["session_id"].as_str().context("Gateway session missing")?.into(),resume));
                        }
                        Some("INTERACTION_CREATE")=>{
                            let handler=handler.clone();let payload=event["d"].clone();
                            tokio::spawn(async move {if handler.dispatch_value(payload).await.is_err(){tracing::warn!("Discord management interaction refused or delivery failed");}});
                        }
                        _=>{}
                    },
                    _=>{}
                }
            }
        }
    }
}

#[derive(Debug)]
struct FatalGateway;
impl std::fmt::Display for FatalGateway {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Gateway rejected configured identity/intents; receiver stopped"
        )
    }
}
impl std::error::Error for FatalGateway {}

struct ReceiverGuard {
    store: crate::management::Store,
    owner: String,
}
impl Drop for ReceiverGuard {
    fn drop(&mut self) {
        let _ = self.store.release_receiver_lease(&self.owner);
    }
}
