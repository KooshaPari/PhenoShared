use super::{Config, DiscordClient};
use crate::management::{Action, Command, Status, Store};
use anyhow::{bail, Context, Result};
use serde::Deserialize;
use serde_json::Value;

/// Never derive Debug: interaction tokens are capabilities and must not reach logs.
#[derive(Clone, Deserialize)]
pub struct Interaction {
    pub id: String,
    pub application_id: String,
    pub guild_id: Option<String>,
    pub channel_id: Option<String>,
    #[serde(rename = "type")]
    pub kind: u8,
    pub token: String,
    pub data: Option<InteractionData>,
    pub member: Option<Member>,
    pub message: Option<Message>,
}
#[derive(Debug, Clone, Deserialize)]
pub struct InteractionData {
    pub custom_id: Option<String>,
    pub component_type: Option<u8>,
    #[serde(default)]
    pub values: Vec<String>,
}
#[derive(Debug, Clone, Deserialize)]
pub struct Member {
    pub user: User,
    #[serde(default)]
    pub roles: Vec<String>,
}
#[derive(Debug, Clone, Deserialize)]
pub struct User {
    pub id: String,
    #[serde(default)]
    pub bot: bool,
}
#[derive(Debug, Clone, Deserialize)]
pub struct Message {
    pub id: String,
    pub author: User,
}
#[derive(Clone)]
pub struct InteractionHandler {
    pub store: Store,
    pub config: Config,
    pub client: DiscordClient,
}
impl InteractionHandler {
    pub fn new(store: Store, config: Config, client: DiscordClient) -> Result<Self> {
        config.validate()?;
        Ok(Self {
            store,
            config,
            client,
        })
    }
    /// Accept only authenticated Gateway events; arbitrary HTTP callers must not call this API.
    pub async fn handle_gateway(&self, event: Interaction) -> Result<bool> {
        let Some(data) = event.data.as_ref() else {
            return Ok(false);
        };
        if !data
            .custom_id
            .as_deref()
            .is_some_and(|s| s.starts_with("phinbox:v1:"))
        {
            return Ok(false);
        }
        if event.application_id != self.config.binding.application_id
            || event.guild_id.as_deref() != Some(&self.config.binding.guild_id)
        {
            bail!("interaction application/guild outside binding");
        }
        if event.kind != 3 {
            bail!("unsupported interaction type");
        }
        // ACK promptly before disk lookup, remote verification or domain work.
        self.client.acknowledge(&event.id, &event.token).await?;
        let result = self
            .command(&event)
            .and_then(|command| self.store.apply(command));
        let response = if result.is_ok() {
            "Workflow updated. This action did not grant a harness permission."
        } else {
            "Workflow action refused: unauthorized, stale, missing or conflicting binding. No permission granted."
        };
        self.client
            .ephemeral(&self.config.binding.application_id, &event.token, response)
            .await?;
        result?;
        Ok(true)
    }
    pub fn command(&self, event: &Interaction) -> Result<Command> {
        if event.application_id != self.config.binding.application_id
            || event.guild_id.as_deref() != Some(&self.config.binding.guild_id)
            || event.kind != 3
        {
            bail!("interaction outside binding");
        }
        let snowflake = event.id.parse::<u64>().context("invalid interaction id")?;
        let millis = (snowflake >> 22).saturating_add(1_420_070_400_000);
        let now = chrono::Utc::now().timestamp_millis();
        if millis > u64::try_from(now.saturating_add(5000)).unwrap_or(0)
            || u64::try_from(now.saturating_sub(120_000)).unwrap_or(0) > millis
        {
            bail!("expired interaction");
        }
        let member = event.member.as_ref().context("guild actor missing")?;
        super::config::validate_id(&member.user.id)?;
        if member.user.bot
            || !(self.config.binding.allowed_users.contains(&member.user.id)
                || member
                    .roles
                    .iter()
                    .any(|r| self.config.binding.allowed_roles.contains(r)))
        {
            bail!("actor not authorized");
        }
        let data = event.data.as_ref().context("component data missing")?;
        let id = data.custom_id.as_deref().context("component id missing")?;
        if id.len() > 100 {
            bail!("component identifier too long");
        }
        let parts = id.split(':').collect::<Vec<_>>();
        if parts.len() != 5 || parts[0] != "phinbox" || parts[1] != "v1" {
            bail!("unsupported component identifier");
        }
        let item_id = super::render::decode_id(parts[2])?;
        let revision = parts[3]
            .parse::<u64>()
            .context("invalid component revision")?;
        let item = self
            .store
            .get(&item_id)?
            .context("unknown management item")?;
        let map = self
            .store
            .thread(&item.id)?
            .context("management item has no Discord thread")?;
        self.config.check_map(&map)?;
        let message = event
            .message
            .as_ref()
            .context("originating message missing")?;
        if event.channel_id.as_deref() != Some(&map.thread_id)
            || message.id != map.message_id
            || message.author.id != self.config.binding.application_id
        {
            bail!("interaction thread/message outside binding");
        }
        let actor = format!("discord:{}", member.user.id);
        let action = match (parts[4], data.component_type) {
            ("ack", Some(2)) if data.values.is_empty() => Action::Ack,
            ("assign", Some(2)) if data.values.is_empty() => Action::Assign(actor.clone()),
            ("defer", Some(2)) if data.values.is_empty() => Action::Defer,
            ("close", Some(2)) if data.values.is_empty() => Action::Close,
            ("status", Some(3)) if data.values.len() == 1 => {
                Action::SetStatus(match data.values[0].as_str() {
                    "open" => Status::Open,
                    "running" => Status::Running,
                    "waiting" => Status::Waiting,
                    "deferred" => Status::Deferred,
                    "partial" => Status::Partial,
                    "blocked" => Status::Blocked,
                    _ => bail!("unsupported workflow status"),
                })
            },
            _ => bail!("unsupported management action"),
        };
        Ok(Command {
            event_id: format!("discord:{}", event.id),
            item_id,
            expected_revision: revision,
            actor,
            action,
        })
    }
    pub async fn dispatch_value(&self, value: Value) -> Result<bool> {
        let event: Interaction =
            serde_json::from_value(value).context("invalid Gateway interaction envelope")?;
        self.handle_gateway(event).await
    }
}
