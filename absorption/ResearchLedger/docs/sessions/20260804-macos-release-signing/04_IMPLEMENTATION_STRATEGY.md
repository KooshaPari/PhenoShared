# Implementation strategy

Tauri's macOS-only configuration provides the entitlement path and hardened runtime while its
documented `APPLE_SIGNING_IDENTITY` override receives the exact Developer ID name at release time.
The script deliberately uses manual `notarytool --keychain-profile` instead of Tauri's Apple-ID/API
notarization environment variables, and rejects those variables to prevent two competing workflows.
