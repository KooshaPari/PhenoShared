# macOS Developer ID Release

ResearchLedger's normal `bun run dev`, `bun run build`, and `bun run tauri` workflows do not
access the Keychain or Apple services. The separate release lane creates a signed `app` and `dmg`,
submits the DMG with `notarytool`, staples the returned ticket, and verifies the final artifacts.

## Release configuration

`config/release/macos.json` is intentionally non-secret. It names:

- `RESEARCHLEDGER_DEVELOPER_IDENTITY`, the environment variable holding the exact Keychain display
  name of the approved `Developer ID Application` identity.
- `ResearchLedger-Notary`, the approved `notarytool` Keychain profile name.

The release operator must provision those two items outside this repository. Do not add certificate
material, API keys, app-specific passwords, Keychain exports, or a profile password to source control.
Use Apple's supported `notarytool` Keychain-profile workflow. The Tauri macOS overlay explicitly
enables the hardened runtime and uses an empty entitlement set; release builds must never gain
`com.apple.security.get-task-allow` or a hardened-runtime exception without a reviewed runtime need.

## Safe rehearsal

This command prints every protected action without querying the Keychain, building, signing,
uploading, stapling, or changing artifacts:

```sh
bun run release:macos -- --dry-run
```

## Production release gate

The operator supplies only the identity name; no credential value is supplied through the shell:

```sh
export RESEARCHLEDGER_DEVELOPER_IDENTITY='Developer ID Application: Legal Name (TEAMID)'
bun run release:macos -- --confirm-release
```

The command fails before building if it is not running on macOS, the required Xcode tools are
missing, the identity is absent from the Keychain, the named notary profile cannot authenticate, or
Tauri's Apple-ID/API-key notarization variables are present. It then fails unless exactly one current
version DMG is produced. After build, it verifies strict/deep Developer ID signing, hardened runtime,
and absence of `get-task-allow`; only then does it submit and wait for notarization, staple and
validate the DMG, and run Gatekeeper assessment on both the app and DMG.

No release is complete merely because this script exits successfully: distribute only the stapled
DMG that passed the resulting checks and record the hosted release and user-install dogfood evidence.

## References

- [Tauri 2 macOS signing](https://v2.tauri.app/distribute/sign/macos/)
- [Tauri 2 macOS configuration](https://v2.tauri.app/reference/config/#macconfig)
- [Apple notarization workflow](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Apple hardened runtime](https://developer.apple.com/documentation/security/hardened-runtime)
