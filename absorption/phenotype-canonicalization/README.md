# Phenotype canonical engineering — audit and agent handoff

**Research snapshot: September 16, 2026 · Version 0.1 · Proposed operationalization, not deployed policy**

See sibling audit: [phenotype-cvp-audit-2026-09-14](../phenotype-cvp-audit-2026-09-14/README.md) — touches shared source/harvest work.

This packet turns the request for canonical tooling, patterns, shared consumption and aggressive optimization into scoped decisions, explicit alternatives, qualification requirements, and a migration plan. It is an amendment candidate for the existing Phenotype handbook and policy capabilities—not another governance product or competing registry.

## Read in this order

1. **REPORT.html** (self-contained reading copy) or **REPORT.md** — diagnosis, decisions, architecture and implementation sequence.
2. **AGENT-HANDOFF.md** — standalone instructions for the implementing agents.
3. **AUDIT-RUNBOOK.md** — how to finish the source/history/consumer audit and collect proof.
4. **decisions.json**, **profiles.json**, **pattern-matrix.json**, **decision-trees.json** — machine-readable decision inventory.
5. **audit/findings.json**, **audit/sources.json**, **audit/repositories.json**, **coverage.json** — actual observations and their limits.
6. **migration/work-packages.json** and **research/** — bounded execution DAG and optimization experiments.
7. **tools/**, **tests/**, **verification/** — small reference collectors, negative controls and actual local results.

## What was actually done

Connected discovery returned **46 repository identities**. Selected current source files were read in **nine repositories**: PhenoShared, PhenoRegistry, PhenoInfra, Tracera, AgilePlus, HeliosLab, OmniRoute, PhenoDesign and Portage. Additional targeted code searches, recent PhenoShared history and Tracera typecheck path history were inspected. Relevant earlier context and Library document excerpts were retrieved. Current primary documentation was checked for the named tooling and language candidates.

The result contains **15 source-grounded findings, 24 proposed decisions, 13 component profiles**, 36 pattern routes, three decision trees, and ten bounded work packages. It does **not** certify all 46 repositories. No complete repository build, full multi-branch history analysis, hosted workflow run, actual installed consumer test, or production performance tournament was executed.

A synthetic two-project experiment **did** run with the locally available TypeScript **5.8.3**. A failing first project followed by a clean second project in one repeated-`-p` command returned exit 0. This is a reproduced counterexample to the command pattern, not a run of Tracera's pinned TypeScript 5.9.3. The exact commands and output are retained in `verification/typescript-multiple-projects.json`.

Reference-tool tests and their measured code coverage are in `verification/`. They validate these small tools only. Their successful run does not authenticate supplied receipts, qualify a product, or authorize migration.

## Working with the reference tools

The collector, receipt checks and default packet checks use Python's standard library, require Python 3.11 or newer, and were executed here with Python 3.13.5. Their eventual deployment under the requested 3.14t profile still needs target-environment qualification. Do not mistake their bootstrap compatibility minimum for a production runtime decision.

```sh
# Validate the packet and its machine-readable cross-references.
python tools/validate_packet.py .

# Test the reference tools, not the user's repositories.
python -m unittest discover -s tests -v

# Read manifests from an immutable commit without running repository scripts.
python tools/audit.py --repo /absolute/path/to/checkout --ref HEAD --output /tmp/manifest-observations.json

# Validate a deliberately synthetic receipt's structure and floors only.
python tools/receipt_validator.py examples/synthetic-receipt.json \
  --expected-source aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --expected-evaluator bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

`python tools/validate_packet.py . --jsonschema` additionally requires the `jsonschema` package; it fails explicitly when that requested dependency is absent. The full schema check was executed for this packet.

The collector reads Git objects, ignores dirty/untracked changes, and does not install packages, run hooks, execute scripts or import repository code. Exit 0 means collection completed, **not compliance**. The receipt validator reports `STRUCTURALLY_VALID_NOT_AUTHENTICATED`; production qualification remains `NOT_EVALUATED`.

## Authority and integration

The current `PhenoShared/docs/GLOBAL_HANDBOOK.md`, pinned September 16, is an important observed authority declaration. Its exact source and limitations are recorded as **G13**. Existing registry, stack policy, assessment schemas, work claims and product records must be reconciled—not overwritten with a new set of identities. Packet-local D/F/WP/P identifiers are draft references. Map them to existing IDs before incorporation and preserve aliases.

No repository edits, account changes, deployment, publication, archive operation or deletion were performed or authorized by this packet. Independent product delivery need not wait for a perfect ecosystem atlas.
