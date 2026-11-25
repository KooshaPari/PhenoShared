# DAG and work breakdown

`non-secret configuration -> release preflight -> Tauri signed app and DMG -> signature verification
-> notary submission -> DMG staple and validation -> Gatekeeper assessment`

The release command stops at the first failed edge. Credentials are an operator-owned prerequisite,
not a repository artifact.
