# FORGE Record Authenticity Assessment

**Target:** `~/CodeProjects/temp/asks-coverage/mined/forge_clean.jsonl`
**Corpus size:** 15,209 JSONL records, 169.7 MB (full file not read)
**Sample:** first 2,000 records (streaming, line-by-line; file never loaded into memory)
**Script:** `~/CodeProjects/temp/asks-coverage/sample_forge.py`
**Machine-readable sidecar:** `~/CodeProjects/temp/asks-coverage/forge_sample_summary.json`

---

## 1. Flag definitions (verbatim)

Each record's `text` field (JSONL schema confirmed: `source`, `source_file`, `session_id`,
`msg_id`, `ts`, `role`, `text`, `text_sha256`, `chars`, `substantive` — `text` is a string)
was scored with six independent boolean flags:

```
f_wrap    = re.search(r'[a-z]\n[a-z]', text)          # mid-word line wrap
f_ansi    = '\x1b[' in text                            # ANSI escape bytes
f_chrome  = any(s in text for s in ("Thinking:", "hide in /settings"))
f_tool    = any(s in text for s in ("Bash(", "Read(", "Result:", "```diff"))
f_box     = any(c in text for c in "─│┌┐└┘├┤")
f_long    = len(text) > 20000
```

A record's **flag count** is the number of these six that evaluate true. Records are bucketed
by flag count (0, 1, 2, 3+). The `text` field was extracted directly from each parsed JSON
object; all 2,000 sampled lines parsed cleanly (0 JSON parse errors).

---

## 2. Bucket table

| Flags | Records | rec % | Text bytes | byte % |
|------:|--------:|------:|-----------:|-------:|
| 0     |   1,556 | 77.80 |    453,339 |  0.47 |
| 1     |     153 |  7.65 |  1,549,184 |  1.60 |
| 2     |      55 |  2.75 |  9,060,641 |  9.35 |
| 3+    |     236 | 11.80 | 85,873,729 | 88.59 |
| **Total** | **2,000** | **100.00** | **96,936,893** | **100.00** |

Byte percentages are computed against the sum of `text` bytes in the sample (96,936,893 B).
Raw JSONL line bytes for the same sample were 100,910,841 B (the delta is JSON escaping).

**Zero-flag percentage: 77.80%** (1,556 of 2,000 records).

Note the concentration: the 291 records with ≥1 flag hold 99.53% of the sampled bytes, and the
236 records with 3+ flags alone hold 88.59%. Contamination is not spread evenly — it is a small
number of very large scrollback captures.

---

## 3. Highest-character records (3 examples)

Truncated to 300 characters, control bytes escaped via `repr`.

**Example 1** — line_index 1812, 814,400 chars:

```
'Last login: Mon Mar 30 18:23:22 on ttys035\n\ue0b6   ~/C/P/repos \ue0b4\ue0b6  chore/consolidation-20260329 \ue0b4\ue0b6 $⇡2 \ue0b4\ue0b6  v25.8.2 \ue0b4\ue0b6  v1.96.\n\ue0b6   ~/C/P/repos \ue0b4\ue0b6  stack/core-domain \ue0b4\ue0b6  12$ 1✓ \ue0b4\ue0b6  v25.8.2 \ue0b4\ue0b6  v1.96.0-nightly \ue0b4 18:25❯ kilof\nc^R\nforge\n\ue0b6   ~/C/P/repos \ue0b4\ue0b6  main \ue0b4\ue0b6 $ 1⇕4/3 \ue0b4\ue0b6  v25.8.2 \ue0b4\ue0b6  v1.96.0-nightly \ue0b4 18'
```

**Example 2** — line_index 1826, 722,400 chars:

```
'ypes":["bin"],"name":"event_replay","src_path":"/Users/kooshapari/CodeProjects/Phenotype/repos/crates/agileplus-benchmarks/benches/event_replay.rs","edition":"2024","doc":false,"doctest":false,"test":false},{"kind":["bench"],"crate_types":["bin"],"name":"graph_query_perf","src_path":"/Users/kooshapa'
```

**Example 3** — line_index 1814, 720,248 chars:

```
'ang/crates.io-index","req":"^2","kind":null,"rename":null,"optional":false,"uses_default_features":true,"features":[],"target":null,"registry":null},{"name":"tokio","source":"registry+https://github.com/rust-lang/crates.io-index","req":"^1","kind":null,"rename":null,"optional":false,"uses_fe'
```

Example 1 is unambiguous terminal scrollback: a login banner, prompt chrome with Powerline glyphs
(`\ue0b6` / `\ue0b4`), a git branch and node version in the prompt, a control character (`^R`),
and a `❯` prompt marker. Examples 2 and 3 are raw `cargo metadata` JSON dumps captured mid-stream
(starting mid-token: `ypes":[` / `ang/crates.io-index`), which is characteristic of a terminal
capture truncated at an arbitrary byte boundary rather than a discrete operator turn.

---

## 4. Verdict

**PARTIALLY_CONTAMINATED**

Zero-flag records are 77.80% of the sampled records, which falls in the 50–80% band. By count the
corpus looks predominantly like discrete operator turns, but by volume it does not: 11.80% of
records account for 88.59% of the bytes, and those are demonstrably terminal scrollback captures
(login banners, prompt chrome, control characters, mid-token `cargo metadata` dumps). Roughly one
operator turn in nine is contaminated, and those contaminated records are orders of magnitude
larger than genuine turns — so per-byte contamination is severe even though per-record
contamination is moderate.

Sample of first 2,000 records; not the full corpus. A flag is evidence of contamination, not proof; zero flags does not prove a single turn.
