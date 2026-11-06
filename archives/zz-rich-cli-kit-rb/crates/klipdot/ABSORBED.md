# KlipDot absorbed (FR-COLLECTION-2026-06, 2026-06-21)

Rust terminal image/clipboard interceptor daemon from `KooshaPari/KlipDot`
moved into `crates/klipdot/` as staged source. Excluded from the parent
`cargo` workspace because KlipDot pins `crossterm 0.27` and `image 0.24`,
while `rich-cli-kit` resolves `crossterm 0.29` / `image 0.25` — unified
build would require a workspace-wide dep bump.

To build KlipDot standalone:

```bash
cd crates/klipdot
cargo build --release
```

Source repo archived/deleted; user's override of KlipDot's prior
"DO NOT DELETE NOR UNARCHIVE" description marker is recorded in the
parent `crates/ABSORPTION_MANIFEST.md`-equivalent section.
