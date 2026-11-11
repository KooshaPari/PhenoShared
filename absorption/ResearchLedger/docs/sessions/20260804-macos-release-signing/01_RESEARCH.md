# Research

Tauri 2.11 supports `bundle.macOS.signingIdentity`, `entitlements`, and `hardenedRuntime`.
Apple requires Developer ID signing, hardened runtime, secure timestamps, no enabled
`get-task-allow`, notarization, and ticket stapling for direct distribution.

Sources: [Tauri](https://v2.tauri.app/distribute/sign/macos/),
[Tauri config](https://v2.tauri.app/reference/config/#macconfig), and
[Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
