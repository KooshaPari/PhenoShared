# PhenoLM Migration

`pheno-specs` was created as a separate documentation/spec repository for
`pheno-harness`. The new target is `PhenoLM`: the LLM policy, eval, trace,
reward, and self-improvement layer owned by this repo.

## Target State

- `pheno-harness` contains the living PhenoLM docs, configs, eval adapters,
  trace schemas, garden gates, and benchmark reports.
- `agileplus-specs/` is no longer the primary spec source.
- The remote `pheno-specs` repo is either archived or renamed to `PhenoLM`
  after its content is imported and checked.

## Migration Steps

1. Fetch the missing submodule content.
   ```powershell
   git submodule update --init --recursive agileplus-specs
   ```

2. Inventory imported content.
   - `agileplus-specs/index/spec.md`
   - `agileplus-specs/research-doc-map.md`
   - `agileplus-specs/sources/chatgpt-master-digest.md`
   - `agileplus-specs/sources/raw/`

3. Move durable content into this repo.
   - Specs -> `docs/phenolm/specs/`
   - Research maps -> `docs/phenolm/research/`
   - Raw source pointers -> `docs/phenolm/sources/`
   - Machine-readable policy -> `config/`

4. Replace references.
   - `README.md`
   - `AGENTS.md`
   - `specs.lock`
   - `.gitmodules`
   - any scripts that read `agileplus-specs`

5. Remove the submodule only after import verification.
   - Delete `.gitmodules` entry.
   - Remove submodule gitlink.
   - Keep an archive pointer in `docs/phenolm/ARCHIVE.md`.

6. Remote cleanup.
   - Preferred: rename `<REDACTED>/pheno-specs` to `<REDACTED>/PhenoLM` if the
     repo remains useful as a standalone spec layer.
   - Otherwise archive `pheno-specs` after this repo becomes authoritative.

## Do Not Do Yet

- Do not delete `agileplus-specs/` while the submodule is uninitialized.
- Do not assume the local empty directory contains all remote spec content.
- Do not make `PhenoLM` a separate runtime service until the garden loop and
  eval ledger are stable inside `pheno-harness`.
