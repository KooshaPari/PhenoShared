# focus-templates

Template-pack format: distributable bundle of focus `Rule` drafts plus recommended connectors and mascot-copy overrides. Serialized as TOML and shipped as `.fptpl` archive (tar.gz with detached ed25519 signature). Traces to FR-TEMPLATE-PACK-001, FR-TEMPLATE-SIGN-001.

## Purpose

Enables packaging and distribution of pre-built rule bundles. Authors write TOML, operator signs with ed25519 private key, users load via app UI and verify signature against Phenotype root public key. Supports version upgrades and custom mascot copy per domain (education, work, fitness).

## Key Types

- `TemplatePack` — name, version, description, rules[], recommended_connectors[], mascot_copy_overrides
- `signing::sign_pack()` — ed25519 sign TOML content
- `signing::verify_pack()` — verify signature against root pubkey before install
- TOML parser with `#[serde(default)]` for forward/backward compatibility

## Entry Points

- `TemplatePack::from_toml_str()` — parse TOML
- `signing::sign_pack()` — sign with private key
- `TemplatePack::verify_and_apply()` — verify signature + upsert rules via store
- `PHENOTYPE_ROOT_PUBKEYS` — hardcoded trusted roots for verification

## Functional Requirements

- FR-TEMPLATE-PACK-001 (Template pack format)
- FR-TEMPLATE-SIGN-001 (Signature verification)
- Additive-only TOML schema (unknown fields ignored)

## Consumers

- iOS/Android app (template discovery UI + install flow)
- Community template publishers
- FocalPoint official templates (morning focus, fitness, education)
