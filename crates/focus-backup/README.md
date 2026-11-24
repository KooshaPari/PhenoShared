# focus-backup

Full encrypted backup and restore for FocalPoint state. Creates versioned, tamper-evident tar+zstd archives with age encryption (passphrase or public-key based). Restores by decrypting, unpacking, and upserting into target storage adapter.

## Purpose

Enables users to export encrypted offline backups of all focus rules, wallet state, penalty records, and task data. Supports round-trip restore with automatic conflict resolution. Includes recovery for corrupted state and migration across devices.

## Key Types

- `BackupManifest` — versioned archive structure with content sections (rules, wallet, penalties, tasks, audit)
- `tar_builder::TarBuilder` — constructs tar blob from state snapshots
- `BackupError` — variants for encryption, format, version mismatch, missing data
- Encryption wrapper using age with passphrase or public key

## Entry Points

- `create_backup()` — snapshot all state via storage adapters, tar+zstd+encrypt, return bytes
- `restore_backup()` — decrypt archive, unpack, upsert into target adapter
- `verify_backup()` — validate manifest structure without full restore

## Functional Requirements

- FR-PRIVACY-001 (Data export/wiping)
- Round-trip encryption/decryption
- Conflict detection and user prompts

## Consumers

- iOS/Android native apps (user-triggered export/import)
- Device migration flows
- Emergency recovery procedures
