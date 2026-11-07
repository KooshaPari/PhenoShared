//! Authorization/correlation checks at the native Gateway management boundary.
//! These tests do not claim that arbitrary HTTP JSON is authenticated Gateway data.
use phinbox::{
    discord::{
        custom_id, Binding, Config, DiscordClient, Interaction, InteractionData,
        InteractionHandler, Member, Message, User,
    },
    management::{Action, Item, Store, ThreadMap},
};
use std::collections::{BTreeMap, BTreeSet};

fn fixture(root: &std::path::Path) -> (InteractionHandler, Item, Interaction) {
    let token = root.join("test-token");
    std::fs::write(&token, "TEST-ONLY-TOKEN").unwrap();
    let config = Config {
        binding: Binding {
            persona_reference: "existing-instinct-fixture".into(),
            application_id: "1558640911297028147".into(),
            guild_id: "1558641659778961432".into(),
            forum_id: "1560878303286534164".into(),
            allowed_users: BTreeSet::from(["42".into()]),
            allowed_roles: BTreeSet::new(),
        },
        credential_file: token.clone(),
        board_map_file: root.join("board.json"),
        receiver_owner: "fixture".into(),
        tags: [
            "open", "running", "waiting", "deferred", "partial", "blocked",
        ]
        .into_iter()
        .enumerate()
        .map(|(i, s)| (s.into(), (100 + i).to_string()))
        .collect::<BTreeMap<_, _>>(),
    };
    let store = Store::open(root.join("ledger.db")).unwrap();
    let item = store
        .create(Item::new("inbox:request-123", "Exact original"))
        .unwrap();
    store
        .bind_thread(
            &item.id,
            ThreadMap {
                guild_id: config.binding.guild_id.clone(),
                forum_id: config.binding.forum_id.clone(),
                thread_id: "700".into(),
                message_id: "701".into(),
            },
        )
        .unwrap();
    let millis = u64::try_from(chrono::Utc::now().timestamp_millis()).unwrap();
    let id = ((millis - 1_420_070_400_000) << 22) | 1;
    let event = Interaction {
        id: id.to_string(),
        application_id: config.binding.application_id.clone(),
        guild_id: Some(config.binding.guild_id.clone()),
        channel_id: Some("700".into()),
        kind: 3,
        token: "test-interaction-token".into(),
        data: Some(InteractionData {
            custom_id: Some(custom_id(&item, "ack").unwrap()),
            component_type: Some(2),
            values: vec![],
        }),
        member: Some(Member {
            user: User {
                id: "42".into(),
                bot: false,
            },
            roles: vec![],
        }),
        message: Some(Message {
            id: "701".into(),
            author: User {
                id: config.binding.application_id.clone(),
                bot: true,
            },
        }),
    };
    let client = DiscordClient::with_endpoint("http://127.0.0.1:9/api/v10", &token).unwrap();
    (
        InteractionHandler::new(store, config, client).unwrap(),
        item,
        event,
    )
}

#[tokio::test]
async fn canonical_inbox_id_roundtrips_and_replay_does_not_create_a_new_revision() {
    let tmp = tempfile::tempdir().unwrap();
    let (handler, item, event) = fixture(tmp.path());
    let command = handler.command(&event).unwrap();
    assert_eq!(command.item_id, item.id);
    assert_eq!(command.action, Action::Ack);
    let receipt = handler.store.apply(command).unwrap();
    assert_eq!(
        handler
            .store
            .apply(handler.command(&event).unwrap())
            .unwrap(),
        receipt
    );
    assert_eq!(handler.store.pending_effects(10).unwrap().len(), 2);
    let mut stale = event.clone();
    stale.id = (event.id.parse::<u64>().unwrap() + 1).to_string();
    assert!(handler
        .store
        .apply(handler.command(&stale).unwrap())
        .is_err());
    assert_eq!(handler.store.get(&item.id).unwrap().unwrap(), receipt);
}

#[tokio::test]
async fn forged_scope_member_thread_message_and_expired_events_are_rejected() {
    let tmp = tempfile::tempdir().unwrap();
    let (handler, item, event) = fixture(tmp.path());
    let mut bad = Vec::new();
    let mut e = event.clone();
    e.guild_id = Some("999".into());
    bad.push(e);
    let mut e = event.clone();
    e.application_id = "999".into();
    bad.push(e);
    let mut e = event.clone();
    e.channel_id = Some("999".into());
    bad.push(e);
    let mut e = event.clone();
    e.message.as_mut().unwrap().id = "999".into();
    bad.push(e);
    let mut e = event.clone();
    e.message.as_mut().unwrap().author.id = "999".into();
    bad.push(e);
    let mut e = event.clone();
    e.member.as_mut().unwrap().user.id = "43".into();
    bad.push(e);
    let mut e = event.clone();
    e.member.as_mut().unwrap().user.bot = true;
    bad.push(e);
    let mut e = event.clone();
    e.id = "1".into();
    bad.push(e);
    for e in bad {
        assert!(
            handler.command(&e).is_err(),
            "forged or expired event reached authority"
        );
    }
    assert_eq!(handler.store.get(&item.id).unwrap().unwrap(), item);
    assert_eq!(handler.store.pending_effects(10).unwrap().len(), 1);
}

#[tokio::test]
async fn assignment_is_bound_to_authenticated_actor_and_permission_actions_are_not_supported() {
    let tmp = tempfile::tempdir().unwrap();
    let (handler, item, mut event) = fixture(tmp.path());
    event.data.as_mut().unwrap().custom_id = Some(custom_id(&item, "assign").unwrap());
    assert_eq!(
        handler.command(&event).unwrap().action,
        Action::Assign("discord:42".into())
    );
    event.data.as_mut().unwrap().custom_id = Some(custom_id(&item, "approve").unwrap());
    assert!(handler.command(&event).is_err());
    event.data.as_mut().unwrap().custom_id = Some(custom_id(&item, "status").unwrap());
    event.data.as_mut().unwrap().component_type = Some(3);
    event.data.as_mut().unwrap().values = vec!["approved".into()];
    assert!(handler.command(&event).is_err());
    assert_eq!(handler.store.get(&item.id).unwrap().unwrap(), item);
}
