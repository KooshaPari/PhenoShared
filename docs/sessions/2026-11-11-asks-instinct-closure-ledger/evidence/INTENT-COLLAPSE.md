# Intent Collapse: distinct strings vs. distinct intents

Generated 2026-11-11 by `collapse_intents.py` (streaming, line-by-line; no file loaded whole).
Machine-readable sidecar: `collapse_results.json`. Raw run cost: ~27 s (raw tiers), ~67 s (with noise tier).

Reference denominator: **2,259 register entries** (the ask register).

## 0. Input filtering, as specified

| Source | lines read | kept (human, non-injected, >=12 chars) | excluded `is_injected:true` | excluded non-human | short nudges (<12 chars) |
|---|---|---|---|---|---|
| jcode | 55,122 | 21,511 | 21,189 | 3,699 | 8,723 |
| codex | 9,650 | 6,736 | 0 | 0 | 2,914 |
| **total** | **64,772** | **28,247** | **21,189** | **3,699** | **11,637** |

After normalization + dedupe: **8,506 distinct strings** (the 8,290 jcode + 405 codex figure collapses by 189
cross-source duplicates, which is consistent with it).

**Short nudges are counted, not dropped:** 11,637 records (<12 chars) collapsing to **382 distinct
strings** (`go`, `continue`, `yes`, `do it`, `.`, etc.). They are excluded from the intent clusters
below on the assumption that each nudge re-asserts an ask already counted, but they are reported so
the exclusion is visible. If nudges were treated as distinct intents, add up to 382.

## 1. Three independent collapse methods

Each method is stated with its rule so no single threshold is presented as truth.

| # | Method | Rule | Clusters | Ratio vs 2,259 |
|---|---|---|---|---|
| a | Exact normalized match | lowercase, whitespace-collapsed, edge-punctuation/fence-stripped equality | **8,506** | **3.77x** |
| b | Prefix-40 collapse | group by first 40 normalized characters | **5,250** | **2.32x** |
| c | Token-set Jaccard >= 0.8 | union-find over pairs inside the same prefix-40 bucket | **6,990** | **3.09x** |

Method c produces *more* clusters than method b because prefix-40 is a hard merge: two asks that
open with the same boilerplate merge even when their bodies differ. c only merges when the token
sets actually overlap heavily, so it is strictly less aggressive than b at the bucket level.

## 2. Cleanup tier (heuristic): 31.8% of "kept" strings are harness-generated

The upstream `is_injected` flag is incomplete. `codex_user_turns_v2.jsonl` has **no `is_injected`
field at all** (verified: 0 of 9,650 records carry the key), and jcode's flag leaves large families
of harness text marked human. The largest prefix-40 buckets are all harness artifacts, not operator
asks:

| Bucket prefix | Members | What it is |
|---|---|---|
| `🐝 **swarm await finished** all members d...` | 810 | swarm bee status message |
| `auto] do more validation on the work bel...` | 364 | `[auto]` continuation nudge |
| `🐝 **swarm await finished** await incompl...` | 353 | swarm bee status message |
| `attached image associated with the prece...` | 202 | image placeholder |
| `auto] before you treat this turn as fini...` | 197 | `[auto]` continuation nudge |
| `environment_context> <current_date>2026-...` | 154 | Codex env block |
| `codex_internal_context source="goal"> co...` | 136 | Codex internal context |
| `🐝 **swarm await finished** await satisfi...` | 128 | swarm bee status message |
| `agents.md instructions <instructions> ##...` | 89 | injected AGENTS.md |

A labelled pattern pass over the 8,506 distinct strings (patterns listed in the script) tags
**2,707 as harness-like (31.8%)**:

| Label | Distinct strings |
|---|---|
| swarm_bee | 1,453 |
| auto_nudge | 699 |
| attached_image | 248 |
| env_context | 155 |
| internal_context | 139 |
| tool_timing | 9 |
| system_reminder | 4 |

Re-running all three methods on the remaining **5,799** distinct strings:

| # | Method | Clean clusters | Ratio vs 2,259 |
|---|---|---|---|
| a | Exact normalized | **5,799** | 2.57x |
| b | Prefix-40 | **5,216** | 2.31x |
| c | Jaccard >= 0.8 in prefix-40 | **5,623** | 2.49x |

## 3. Shape of the distinct-string population (raw tier, n = 8,506)

| Bucket | Distinct strings | Share |
|---|---|---|
| <= 4 words (likely nudges or terse instructions) | 633 | 7.4% |
| >= 40 characters (likely substantive asks) | 7,542 | 88.7% |
| < 40 characters | 964 | 11.3% |

The 88.7% "substantive" share is inflated by the harness artifacts in section 2, which are long by
construction (bee status lines run to hundreds of characters).

## 4. Why none of these is the true intent count

1. **The threshold is the answer.** Moving from exact equality (8,506) to first-40-characters
   (5,250) is a 38% swing with no change to the underlying data. Choosing 0.7 or 0.9 Jaccard, or a
   20- or 80-character prefix, moves the number again. A reported count is a statement about a
   threshold, not about the operator.
2. **Every method is lexical, so none of them sees a paraphrase.** "Fix the CI failure on PR 63" and
   "the PR 63 build is red, sort it out" share almost no tokens and land in different clusters under
   all three methods. Semantic paraphrases of one ask therefore inflate every count here. The true
   intent count is lower than any number on this page, by an amount these methods cannot measure.
3. **The comparison to 2,259 is asymmetric.** The register's 2,259 entries were **not** put through
   this normalization, edge-punctuation stripping, or dedupe. If the register also contains retries
   and rephrasings of one ask (very likely, given it is an ask ledger), its own distinct-intent count
   is below 2,259 while our side has been collapsed aggressively. The ratio is therefore biased
   *upward*: part of the 2.3x-2.6x gap is a difference in processing, not a difference in behaviour.
4. **The source population is not clean.** 31.8% of the strings measured here are harness text that
   the `is_injected` flag failed to mark (section 2), and codex carries no such field at all. The
   noise tier is a labelled heuristic with its own error rate in both directions.
5. **Nudge exclusion is a modelling choice.** 11,637 nudge records (382 distinct) were removed from
   the clusters. If any of them preceded a genuinely new ask, the count is understated by up to 382.

## 5. Defensible range

**Between ~5,200 and ~5,800 distinct intents.**

- Lower bound (most aggressive): prefix-40 collapse on the cleaned population = **5,216**.
- Upper bound (most conservative): exact normalized match on the cleaned population = **5,799**.

Against the 2,259 register entries that is a **2.3x to 2.6x** gap.

For transparency, the same bounds without the heuristic cleanup tier are **5,250** (prefix-40) and
**8,506** (exact), i.e. 2.3x to 3.8x. The wider band is dominated by harness artifacts, so it is
reported but not used as the headline range. No point estimate is offered: the three methods differ by
up to 3,256 clusters and the lexical/semantic gap is unmeasured.
