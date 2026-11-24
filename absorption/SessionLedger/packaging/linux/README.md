# Linux installer scaffolds

These scripts turn an existing Linux `sl-viewer` release binary into local
installer candidates:

```bash
cargo build --release -p sl-viewer --locked
./packaging/linux/package-appimage.sh
./packaging/linux/package-deb.sh
```

Set `VERSION`, `BINARY`, `DIST`, or `ARCH` to override defaults. AppImage
packaging requires `appimagetool`; Debian packaging requires `dpkg-deb`.

Status is **partial**: the scripts are developer scaffolds, are not run by
release CI, and do not publish repository metadata, desktop icons, signatures,
or update feeds. Test generated packages on supported clean distributions
before considering them release artifacts.

Platform package signing remains deferred. Release checksums, keyless cosign,
and GitHub provenance continue to provide the repository-level integrity path;
see [`docs/ops/distribution.md`](../../docs/ops/distribution.md).
