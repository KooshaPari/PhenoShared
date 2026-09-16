# Revision 1.1 validation and limits

## Executed in this revision

- All **175** reference tests passed: the prior 157 plus 18 new consumer-impact schema/linkage tests. See validation/test-results.txt.
- Ten JSON Schema 2020-12 schemas, registered examples, topic proposals, requirement/task/traceability IDs, DAG acyclicity, prompt hashes, prior-archive hashes and relative Markdown file targets were checked.
- The PDF was regenerated to 33 pages. All pages were reviewed in rendered contact sheets; the modified cover and new policy page were inspected at higher resolution. Text blocks passed boundary checks.
- The six original contextual archives remain byte-identical. The original top-level v1.0 ZIP is retained unchanged separately, with its digest in records/package.json.
- Full and delta archives have per-file inventory/hash manifests; the delta includes exact old/new file hashes for conflict-aware use. No automatic patch application or repository modification was executed.

## Inherited coverage, not a new measurement

The prior independent coverage reports under validation/ measure **scripts/assurance_check.py only**. That file was not modified in v1.1. Its tests were rerun, but coverage was not remeasured. Preserve these reports as baseline evidence, not new consumer-impact coverage or a claim about the whole package.

| Prior suite | Lines | Branches |
|---|---:|---:|
| Unit | 136/137 (99.27%) | 75/76 (98.68%) |
| Integration | 136/137 (99.27%) | 75/76 (98.68%) |
| CLI E2E | 134/137 (97.81%) | 75/76 (98.68%) |

The 18 new tests exercise structural requirements and negative examples only. They expressly demonstrate that a nonempty evidence-reference string can satisfy structural checks without authenticating a real receipt. This schema is not a production gate for ecosystem benefit, complete consumer discovery, compatibility, or approval.

## Reproduction

```sh
python -m unittest discover -s tests -v
python scripts/validate_package.py .
python scripts/estimate_dag.py work/tasks.json
```

Run in an appropriate isolated Python environment with scripts/requirements.txt. Redirect validation output outside docs/ while generating it, then copy after success, so the validator does not read its own partially written JSON.

## Not performed or certified

No fresh GitHub audit, native product test, live AgilePlus transition, source migration, package publication, DNS/deployment mutation, full consumer search, measured ecosystem benefit, production benchmark, user adoption or restore drill was performed. External sources and Markdown anchors were not revalidated. SROC/CDP and native engine compatibility remain unresolved as before. Product pilots remain planned and work packages remain unclaimed.

## Integrity

MANIFEST.json and SHA256SUMS cover every payload file except those two manifests themselves. A separate SHA-256 file covers the ZIP. Hashes establish byte integrity, not truth, semantic completeness or permission. Original contextual artifacts preserve their historical statuses and do not override new scoped human decisions.
