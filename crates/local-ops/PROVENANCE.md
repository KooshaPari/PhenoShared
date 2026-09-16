# Initial source capture

- Captured: 2026-08-15
- Inputs: six executable files from `~/bin` and two guard scripts from
  `~/.local/bin`.
- Admission check: no literal assignment to a key, secret, token, password,
  authorization, or bearer value was detected.
- Validation: Bash/Zsh syntax checks passed before this repository was
  published.
- Exclusions: package-managed client shims, product-owned source, broken
  legacy wrappers, binaries, backups, and all volatile runtime data.

## Absorption into phenotype-tooling

- Absorbed: 2026-09-14
- Source repo: [KooshaPari/zz-merge-unk-local-ops](https://github.com/KooshaPari/zz-merge-unk-local-ops)
- Destination: `crates/local-ops/` in [KooshaPari/PhenoTooling](https://github.com/KooshaPari/PhenoTooling)
- Source repo preserved as-is; no further development expected there.
