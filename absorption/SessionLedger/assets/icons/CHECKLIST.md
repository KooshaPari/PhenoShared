# SessionLedger icon-set CI verification checklist

This file documents the file-presence + palette invariants for the
`assets/icons/sessionledger.iconset/` directory. It replaces the Rust
integration test (which would require compiling the sl-viewer lib — currently
blocked by two pre-existing compile errors in `crates/sl-viewer/src/` that are
out of scope for the iconset PR).

## To verify locally

```bash
# 1. All required Apple sizes present
for sz in 16 32 48 64 128 256 512 1024; do
  test -f assets/icons/sessionledger.iconset/icon_${sz}x${sz}.png || echo "MISSING $sz"
done

# 2. @2x variants present
for sz in 16 32 128 256; do
  test -f assets/icons/sessionledger.iconset/icon_${sz}x${sz}@2x.png || echo "MISSING @2x $sz"
done

# 3. .ico + Linux PNG present
test -f assets/icons/sessionledger.ico
test -f assets/icons/sessionledger-256x256.png

# 4. Brand palette present in SVG
for hex in f6f8fa 1f2937 2563eb f97316 14b8a6; do
  grep -qi "#$hex" assets/brand/sessionledger-icon.svg || echo "MISSING palette $hex"
done

# 4b. No MelosViz warn hex leaked (must NOT find f59e0b as a color)
for forbidden in f59e0b; do
  grep -qi "#$forbidden" assets/brand/sessionledger-icon.svg && echo "LEAKED $forbidden (was amber in original draft; swapped to f97316 to avoid MelosViz mv-warn collision)" || true
done

# 5. No Backbone-2 hex leaked into Lab-Coat mark
for forbidden in 0a0d12 161b22 a371f7 3fb950; do
  grep -qi "#$forbidden" assets/brand/sessionledger-icon.svg && echo "LEAKED $forbidden" || true
done

# 6. No Tracera hex leaked into Lab-Coat mark
for forbidden in 090a0c 7ebab5 6366f1 a5b4fc; do
  grep -qi "#$forbidden" assets/brand/sessionledger-icon.svg && echo "LEAKED $forbidden" || true
done

# 7. Cargo.toml has bundle block
grep -q "package.metadata.bundle" crates/sl-viewer/Cargo.toml
grep -q "sessionledger.iconset" crates/sl-viewer/Cargo.toml
```

When the sl-viewer lib compile errors are fixed (owned-repos scope), convert
this checklist back to a proper `crates/sl-viewer/tests/iconset.rs` integration
test with the same checks but in `assert!()` form.

## Pre-existing sl-viewer lib errors (out of scope for iconset PR)

```
error[E0583]: file not found for module `theme`
  --> crates/sl-viewer/src/app.rs
error[E0599]: no method named `json` found for struct `reqwest::Response`
  --> crates/sl-viewer/src/search_view.rs:294:10
    (reqwest needs the `json` feature flag)
```

These block `cargo test -p sl-viewer` for ANY integration test. Owned-repos
should fix before the iconset PR can ship its Rust-level CI verification.
