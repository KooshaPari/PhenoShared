use super::{
    render::{marker, render_message, thread_name},
    Config, DiscordClient,
};
use crate::management::{Effect, EffectKind, Store, ThreadMap};
use anyhow::{bail, Context, Result};
use reqwest::Method;
use serde_json::json;

#[derive(Clone)]
pub struct Mirror {
    pub store: Store,
    pub config: Config,
    pub client: DiscordClient,
    owner: String,
}
impl Mirror {
    pub fn new(store: Store, config: Config, client: DiscordClient) -> Result<Self> {
        config.validate()?;
        Ok(Self {
            store,
            config,
            client,
            owner: uuid::Uuid::new_v4().to_string(),
        })
    }
    fn lease(&self) -> Result<()> {
        self.store.renew_projection_lease(&self.owner, 60_000)
    }
    pub async fn sync_once(&self) -> Result<usize> {
        if !self.store.acquire_projection_lease(
            &self.owner,
            u64::try_from(chrono::Utc::now().timestamp_millis())?,
            60_000,
        )? {
            bail!("another Discord projection worker holds the lease");
        }
        self.lease()?;
        let result = self.sync_owned().await;
        let release = self.store.release_projection_lease(&self.owner);
        match result {
            Err(e) => Err(e),
            Ok(n) => {
                release?;
                Ok(n)
            },
        }
    }
    async fn sync_owned(&self) -> Result<usize> {
        self.client.verify(&self.config).await?;
        let mut done = 0;
        for effect in self.store.pending_effects(32)? {
            self.lease()?;
            match self.project(&effect).await {
                Ok(()) => {
                    self.store
                        .acknowledge_effect_fenced(&effect.id, &self.owner)?;
                    done += 1;
                },
                Err(e) => {
                    self.store.record_attempt(&effect.id, &e.to_string())?;
                    return Err(e);
                },
            }
        }
        Ok(done)
    }
    async fn project(&self, effect: &Effect) -> Result<()> {
        let map = if let Some(map) = self.store.thread(&effect.item_id)? {
            map
        } else {
            let checkpoint = self.store.projection_checkpoint(&effect.item_id)?;
            if checkpoint.as_deref() == Some("create-inflight") {
                if let Some(map) = self.reconcile(effect).await? {
                    self.store
                        .bind_thread_fenced(&effect.item_id, map.clone(), &self.owner)?;
                    map
                } else {
                    bail!("ambiguous Discord create: no unique owned remote match; refusing duplicate post");
                }
            } else {
                self.store.set_projection_checkpoint_fenced(
                    &effect.item_id,
                    "create-inflight",
                    &self.owner,
                )?;
                self.lease()?;
                let created=self.client.request_item(Method::POST,&format!("/channels/{}/threads",self.config.binding.forum_id),&json!({
                    "name":thread_name(&effect.item)?,"auto_archive_duration":1440,
                    "applied_tags":[self.config.tag(effect.item.status)?],"message":render_message(&effect.item)?
                }),&effect.item).await?;
                let map = ThreadMap {
                    guild_id: self.config.binding.guild_id.clone(),
                    forum_id: self.config.binding.forum_id.clone(),
                    thread_id: created["id"]
                        .as_str()
                        .context("created thread id missing")?
                        .into(),
                    message_id: created["message"]["id"]
                        .as_str()
                        .context("created starter message missing")?
                        .into(),
                };
                self.config.check_map(&map)?;
                self.store
                    .bind_thread_fenced(&effect.item_id, map.clone(), &self.owner)?;
                map
            }
        };
        self.config.check_map(&map)?;
        self.lease()?;
        self.client.verify_thread(&self.config, &map).await?;
        self.lease()?;
        // Reopen only an owned mapping when projecting an older pending state.
        self.client
            .request(
                Method::PATCH,
                &format!("/channels/{}", map.thread_id),
                Some(&json!({"archived":false,"locked":false})),
            )
            .await?;
        self.lease()?;
        self.client
            .request_item(
                Method::PATCH,
                &format!("/channels/{}/messages/{}", map.thread_id, map.message_id),
                &render_message(&effect.item)?,
                &effect.item,
            )
            .await?;
        self.lease()?;
        let state = if effect.kind == EffectKind::Close {
            json!({"archived":true,"locked":true})
        } else {
            json!({"applied_tags":[self.config.tag(effect.item.status)?]})
        };
        self.client
            .request(
                Method::PATCH,
                &format!("/channels/{}", map.thread_id),
                Some(&state),
            )
            .await?;
        Ok(())
    }
    async fn reconcile(&self, effect: &Effect) -> Result<Option<ThreadMap>> {
        self.lease()?;
        let active = self
            .client
            .request(
                Method::GET,
                &format!("/guilds/{}/threads/active", self.config.binding.guild_id),
                None,
            )
            .await?;
        let mut threads = active["threads"]
            .as_array()
            .cloned()
            .context("active thread enumeration incomplete")?;
        self.lease()?;
        let archived = self
            .client
            .request(
                Method::GET,
                &format!(
                    "/channels/{}/threads/archived/public?limit=100",
                    self.config.binding.forum_id
                ),
                None,
            )
            .await?;
        // Do not create again if pagination or enumeration is incomplete.
        threads.extend(
            archived["threads"]
                .as_array()
                .cloned()
                .context("archived thread enumeration incomplete")?,
        );
        let prefix = format!("{} ", marker(&effect.item)?);
        let mut matches = Vec::new();
        for thread in threads {
            if thread["parent_id"].as_str() != Some(&self.config.binding.forum_id)
                || thread["owner_id"].as_str() != Some(&self.config.binding.application_id)
                || !thread["name"]
                    .as_str()
                    .is_some_and(|s| s.starts_with(&prefix))
            {
                continue;
            }
            let id = thread["id"]
                .as_str()
                .context("reconciled thread id missing")?;
            self.lease()?;
            let messages = self
                .client
                .request(
                    Method::GET,
                    &format!("/channels/{id}/messages?limit=100"),
                    None,
                )
                .await?;
            let expected = marker(&effect.item)?;
            let messages = messages
                .as_array()
                .context("reconciliation message enumeration incomplete")?;
            let found = messages
                .iter()
                .filter(|m| {
                    m["author"]["id"].as_str() == Some(&self.config.binding.application_id)
                        && m["embeds"].as_array().is_some_and(|es| {
                            es.iter()
                                .any(|e| e["footer"]["text"].as_str() == Some(&expected))
                        })
                })
                .collect::<Vec<_>>();
            if found.len() != 1 {
                bail!("remote creation marker is missing or ambiguous; manual reconciliation required");
            }
            matches.push(ThreadMap {
                guild_id: self.config.binding.guild_id.clone(),
                forum_id: self.config.binding.forum_id.clone(),
                thread_id: id.into(),
                message_id: found[0]["id"]
                    .as_str()
                    .context("reconciled message id missing")?
                    .into(),
            });
        }
        matches.sort_by(|a, b| a.thread_id.cmp(&b.thread_id));
        matches.dedup();
        if matches.len() > 1 {
            bail!("multiple owned Discord threads for one management item");
        }
        Ok(matches.pop())
    }
}
