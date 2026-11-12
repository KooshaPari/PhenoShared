# Agentora absorbed residue

Source: `KooshaPari/zz-zz-agentcheck-zz-pause-Agentora` (private, archived),
default branch `main` at commit `4bdf9841521eb25a051fcb032276e05db435e41d`.

This tree lives at `absorption-residue-Agentora/`, deliberately outside the
`absorption/` namespace, because it is residue rather than a full absorption:
2100 of the source repos 2205 paths are intentionally absent, so placing it
under `absorption/` would make `verify_absorption.py` correctly report it as
incomplete. Keeping that invariant strict is worth more than the convenience of
a uniform path.

It holds the 105 source paths that existed in neither `PhenoShared` nor
`PhenoAI` after the Rust-crate and phenoagent split. The split itself was
already complete: all 47 crate names collided and 0 were new.

Only public-safe content is here. Sixteen paths are withheld, chiefly because
they describe internal topology - retired repositories, internal absorption
waves and charter identifiers - rather than because they carry credentials.
A secret scan over all 123 gap paths found zero credential hits.

Every file was verified byte-identical to the source by SHA-256.
See `docs/absorption-ledger/WAVE-2026-11-12B.md` for the full classification.
