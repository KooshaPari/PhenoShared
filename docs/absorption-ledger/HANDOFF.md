# Handoff — absorption batch, 2026-11-12

One page. Two open items, both requiring the operator. Everything else is closed.

## Act on these

### 1. Rotate the Caddy basic-auth password

A bcrypt hash for Caddy basic auth sits on the **public default branch** of
`zz-ref-HeliosLite` at `ops/caddy/Caddyfile.helioslite`, introduced in commit
`9d67435d0`.

```
$2a$14$...        # bcrypt, cost 14, publicly readable
```

Rotation is the mitigation, not a history rewrite. Do **not** ask an agent to
edit the file: replacing the hash with an environment variable would break a
deployment that reads this file, and the hash remains in history regardless.

Everything else in that repository scanned clean across all refs — zero hits for
AWS, `sk-` keys, GitHub tokens and PATs, Slack, PEM, Tailscale, Google, npm,
HuggingFace, GitLab, CGNAT.

### 2. Decide whether to publish the `Personal` public code

The split is materialised at `E:\koosh\Agents\scratch\personal-split\S`
(185 files, reproduced exactly from the recorded bucket enumeration; buckets are
S=185 / R=23 / P=50).

The scrub question is now narrow and is **not** a secrets question:

| Finding | Detail |
|---|---|
| 137 identifier occurrences | 92 are test fixtures, and a further 9 were miscounted by a heuristic that missed `test-*.mjs` |
| Real exposure | ~12 service hostnames (`agent-comms.*`, `dash.*`, `*.workers.dev`), **1** D1 database id in `jobs-collector/wrangler.toml`, 9 launchd labels, 1 real email |
| Credentials | **none** |

So the decision is whether disclosing your service hostnames is acceptable. If
yes, the scrub is a handful of placeholders and the push is mechanical.

**Scrub applied** to `E:\koosh\Agents\scratch\personal-split\S-scrubbed`
(185 files). Two passes, 113 replacements across 43 files. The first pass had real
blind spots worth recording: it matched `C:\Users\koosh` but not
`/Users/kooshapari`, so macOS home paths kept the username, and an escaped dot
(`agents\.kooshapari\.com` inside a regex literal) defeated both the hostname
and email patterns. Post-scrub verification is now clean on home paths, real
UUIDs, and the handle inside hostnames. The only residue is `KooshaPari` as the
public GitHub org name, which is not a disclosure.

Replacements keep the shapes valid so the code still parses: hostnames became
`example.com`, UUIDs became a well-formed nil-shaped UUID, launchd labels became
`com.example.*`. Publishing from `S-scrubbed` rather than `S` is the safer path.

## Do not redo

- **Helios histories are preserved.** HeliosLite: 1,061 refs / 5 namespaces.
  HeliosCLI: 1,340 refs / 3 namespaces. Both verified by full ref-map equality,
  not by counting.
- **`HeliosLite` and `HeliosCLI` are the same repos as `zz-ref-HeliosLite` and
  `zz-ref-HeliosCLI`** — they are renames, not duplicates. Compare repository
  **ids**, never names: this mistake was made twice.
- **The phenoagent residue needs nothing.** `agents/phenoagent/` has 1,532 paths
  in both Agentora and PhenoAI with 0 missing, and all 11 differing files are
  newer in PhenoAI (2026-09-15 vs 2026-06-17). Pushing would regress it.
- **The Agentora contracts crate is integrated**, not copied: it is a workspace
  member and `cargo check -p phenotype-agent-contracts` exits 0.
- **The 11 deleted forks are deliberately not restored.** Their refs are all
  preserved under `refs/preserved/` and `scripts/restore_preserved.py` reverses
  it, but restoring eleven forks would undo the consolidation the no-delete rule
  exists to protect.
- **The recovery stores are not redundant.** No ref set matches a live repo, no
  two of 83 repos share a default-branch tree, and the four same-named archives
  hold no commit present in their namesake.

## Not actionable

`chatta` is held by no repository anywhere, and `PhenoApps` — its suggested
destination — is a read-only sunset shelf whose own README forbids adding source.
`phenotype-archives-20261108` is the terminal preservation envelope for 12
deleted-upstream repos; there is no destination to merge it into.

## Read this before trusting any previous summary

Eleven claims in this session were wrong and were corrected by running a check
rather than trusting the write-up. The pattern is consistent and worth carrying
forward:

- a "full" bundle was stored in the wrong repository
- a crate reported as integrated was unbuildable
- a disk threshold "breach" was GiB compared against decimal bytes
- three verification scripts were broken while the data they checked was fine
- two absorption manifests absorbed a repository into itself, graded HIGH
- `zz-ref-*` "duplicates" were the same repos renamed
- a `PhenoAI` "blocker" did not exist
- a split described as "staged" was only a report
- a test-file heuristic inflated real exposure from 1 to 10

Detail and evidence for each: [`WAVE-2026-11-12B.md`](WAVE-2026-11-12B.md).
