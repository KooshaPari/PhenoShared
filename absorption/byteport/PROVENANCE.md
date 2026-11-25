# BytePort - absorption provenance

- **Source repo:** `KooshaPari/BytePort` (public)
- **Absorbed on:** 2026-11-11
- **Files copied here:** 361
- **Already present in `_archived/byteport/`:** 317
- **Routed to the private registry:** 2

## Why this was a partial absorption

`_archived/byteport/` held only 317 of the 680 files in the source tree, and
only 317 of those matched the source by path. 362 files were absent entirely.
They are copied here so the source repo can be deleted without loss.

## Routed privately

Three files carry tailnet addresses or handover detail and were sent to
`PhenoRegistry/repos/BytePort/` instead:

- `docs/handover/byteport-handover-to-windows-agent.md`
- `docs/sessions/20260918-byteport-handoff/HANDOFF.md`
- `docs/sessions/20260918-jcode-session-handoff/SESSION.md`

## Security note carried over from the source

BytePort's own handover doc records that an RSA private key
(`backend/byteport/byteport-ghkey.pem`) was committed to that **public** repo at
`8ab442c2` on 2024-11-26 and not deleted until `8f7a12c6` on 2026-05-06: about 17
months of public git history. The doc names the file and its md5 but does not
contain the key material. The key blob remains in BytePort's history unless that
history is rewritten, so **the key must be treated as compromised and rotated**.

## Deliberate exclusions

One file from the source tree is intentionally not carried anywhere:

- `backend/byteport/byteport-server.exe` (61 MB) is a compiled build artefact,
  not source. GitHub's own guidance flags files that size, and a Windows binary
  has no place in a public repo's history. It is reproducible from the source
  that *is* preserved here.

`python scripts/verify_absorption.py byteport --also _archived/byteport` will
therefore report exactly one missing file. That is this exclusion, not a gap.

## Verification

```bash
python scripts/verify_absorption.py byteport --also _archived/byteport
```

BytePort's content is split across two roots: the 317 files that already existed
in `_archived/byteport/` and the 361 recovered into `absorption/byteport/`. Any
verification has to count both, which is why the `--also` flag exists.
