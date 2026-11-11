# Reproducible build checks

SessionLedger checks whether two clean release builds of the same binary produce
the same SHA-256 digest. This is reproducibility evidence, not a claim that the
build is fully hermetic or SLSA Build Level 3.

## Release packaging contract (`SOURCE_DATE_EPOCH`)

Release packaging **must** set `SOURCE_DATE_EPOCH` to the Unix timestamp of the
tagged commit (or the commit being packaged) before invoking `cargo build
--release`. Tools that honor the variable then embed a stable timestamp instead
of wall-clock time.

Contract:

1. `.github/workflows/release.yml` derives `SOURCE_DATE_EPOCH` from
   `git log -1 --pretty=%ct` and exports it for every matrix build step, with
   `CARGO_INCREMENTAL=0`.
2. Local packaging scripts should export the same variable (or accept an
   explicit epoch) before building release binaries.
3. Consumers comparing rebuilds must use the same epoch, toolchain, target, and
   lockfile; archive/ZIP metadata is out of scope for the binary digest check.

Policy-only CI (cheap, no dual compile) verifies the docs mandate and the
release workflow export:

```powershell
pwsh ./scripts/repro-check.ps1 -PolicyOnly
```

## Quick check

Requirements:

- the repository's Rust toolchain and committed `Cargo.lock`;
- PowerShell 7 (`pwsh` on Linux/macOS or `pwsh.exe` on Windows);
- Git, so the script can derive a stable timestamp from the current commit.

From the repository root, run:

```powershell
pwsh ./scripts/repro-check.ps1
```

The script:

1. asserts the release packaging `SOURCE_DATE_EPOCH` contract (docs + workflow);
2. prefers an already-exported `SOURCE_DATE_EPOCH`, otherwise derives it from the
   current commit timestamp;
3. disables Cargo incremental compilation;
4. builds `sl-daemon` twice with `--release --locked` into separate temporary
   target directories;
5. hashes each release binary with SHA-256 and fails if the digests differ; and
6. removes both build directories.

To reproduce an earlier result, pass its epoch explicitly (or export
`SOURCE_DATE_EPOCH` in the environment):

```powershell
pwsh ./scripts/repro-check.ps1 -SourceDateEpoch 1783900000
```

CI runs the dual-build check on Linux as a blocking pull-request smoke test, and
runs `-PolicyOnly` from the hermetic workflow so release wiring stays enforced
without a second full compile matrix. For a release candidate, run the dual-build
check on every release target and record the two hashes, commit, Rust version,
target triple, `SOURCE_DATE_EPOCH`, and host image beside the release evidence.
The script accepts `-ManifestPath` and `-BinaryName` for another Rust binary.

## Interpretation and limits

A matching digest demonstrates that two isolated target directories on one host
produced the same binary. It does not isolate the build from the network, pin the
runner image or system linker, vendor dependencies, compare independent hosts,
or prove that archives have deterministic metadata. `SOURCE_DATE_EPOCH` only
affects tools that honor it.

Windows is best-effort because the MSVC linker, PDB generation, SDK, and host
toolchain may add nondeterministic data. By default, the script reports a
Windows mismatch as a warning; pass `-Strict` to make it blocking. For a
mismatch, preserve both binaries, compare PE sections and PDB behavior, and
record the runner and toolchain versions. Linux CI is always strict.

For stronger hermetic evidence, start with the `sl-daemon` offline dependency
gate in [`hermetic-builds.md`](hermetic-builds.md), then use an immutable builder
image, vendor and build dependencies offline, pin the exact Rust toolchain and
system packages, and run the comparison on two fresh workers. Compare unpacked
binaries separately from ZIP or tar metadata.

### Environment isolation (partial SLSA L3)

SessionLedger does **not** claim SLSA Build Level 3. Incremental isolation
evidence lives in the [environment isolation checklist](hermetic-builds.md#environment-isolation-checklist-slsa-l3-gaps):

- `scripts/slsa-isolation-check.ps1 -SelfCheck` machine-verifies checklist
  anchors, digest-pinned builder wiring, and the isolated container rebuild job
  in `.github/workflows/hermetic.yml` (single pinned GHCR image — not
  two-independent-builder proof).
- `scripts/reusable-provenance-check.ps1 -SelfCheck` machine-verifies the in-repo
  reusable hermetic build workflow caller SHA pin and `builder_image_digest`
  input contract ([`reusable-hermetic-pin.md`](reusable-hermetic-pin.md)).
- `scripts/repro-check.ps1 -PolicyOnly` also asserts the isolation doc anchors
  and container rebuild wiring alongside `SOURCE_DATE_EPOCH` release policy.

Protected GitHub Environments, hardened runners, vendored dependencies, and
two-builder rebuilds remain unpaid operator work documented in the checklist.

## Provenance enforcement path

The release workflow requires GitHub build provenance for assets published from
the canonical `KooshaPari/SessionLedger` repository. The attestation step is
skipped outside that repository so forks are not broken by unavailable OIDC
permissions. Checksum signing remains best-effort because Sigstore availability
is outside the build's control.

This is stronger provenance evidence, but it is not SLSA Build Level 3. To move
closer to that bar:

1. make release publication depend on successful per-platform attestations in
   each matrix build job, with a second aggregate attestation over collected
   Release assets;
2. verify each attestation's repository, workflow, commit, and subject digest
   before publishing; and
3. protect the release environment so bypassing the required workflow needs
   explicit maintainer approval.

Consumers must verify `SHA256SUMS`, its Sigstore bundle when present, and GitHub
attestations as described in [`distribution.md`](distribution.md).

## SLSA materials metadata (partial L3)

SessionLedger does not claim full SLSA Build Level 3. The release workflow does
require GitHub build provenance that binds each published archive **subject**
(name + SHA-256 digest) to **materials** describing the source inputs GitHub
Actions consumed (notably the tagged repository checkout). This is partial
material-metadata evidence: it documents what was built and from which commit, but
it does not prove hermetic isolation, full reusable-workflow SLSA signing, or
complete dependency closure. Partial in-repo reusable-workflow caller evidence
is tracked in [`reusable-hermetic-pin.md`](reusable-hermetic-pin.md) and checked
by `scripts/reusable-provenance-check.ps1 -SelfCheck`.

### Contract and fixture

The blocking contract is enforced by
[`scripts/provenance-contract-check.ps1`](../../scripts/provenance-contract-check.ps1)
and [`.github/workflows/provenance-contract.yml`](../../.github/workflows/provenance-contract.yml).
The script asserts that:

1. each matrix `build` job and the aggregate `release` job call
   `attest-build-provenance` with an explicit `subject-path` binding; and
2. [`docs/ops/fixtures/slsa-materials-contract.sample.json`](fixtures/slsa-materials-contract.sample.json)
   remains a valid in-toto statement containing both `subject` and materials
   (`predicate.materials` or `predicate.buildDefinition.resolvedDependencies`).

The fixture uses placeholder digests only; it documents the fields consumers and
maintainers should expect from canonical Release attestations without requiring
Sigstore certificates in CI.

### What to verify on a Release

After downloading an archive from a canonical Release:

1. confirm the archive SHA-256 matches `SHA256SUMS`;
2. run `gh attestation verify <archive> --repo KooshaPari/SessionLedger` and
   confirm the attestation subject digest matches the archive; and
3. inspect the attestation predicate for materials linking the build to
   `KooshaPari/SessionLedger` at the Release tag commit (SLSA v1
   `buildDefinition.resolvedDependencies`, or v0.2 `materials` when present).

Cross-check `session-ledger.cdx.json` when you need component-level dependency
metadata; the CycloneDX SBOM complements but does not replace provenance
materials on the archive subject.

Remaining gaps toward full SLSA-L3 include full reusable-workflow SLSA signing
and attestation breadth, protected release Environments, two-independent-builder
rebuilds, and mandatory SBOM-to-subject attestations for every matrix artifact.
Partial environment isolation and caller-pin evidence is tracked in
[`hermetic-builds.md` § Environment isolation](hermetic-builds.md#environment-isolation-checklist-slsa-l3-gaps)
(`scripts/slsa-isolation-check.ps1 -SelfCheck`) and
[`reusable-hermetic-pin.md`](reusable-hermetic-pin.md)
(`scripts/reusable-provenance-check.ps1 -SelfCheck`). Platform code-signing
remains deferred per
[`0003-platform-code-signing.md`](../adr/0003-platform-code-signing.md).
