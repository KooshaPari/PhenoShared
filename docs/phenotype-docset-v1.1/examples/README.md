# Worked schema and assurance examples

All records in this directory are synthetic teaching fixtures, not actual repository requirements, coverage, accepted work or pilot results. Unknown source and actual evidence remain absent. The QA report carries data_origin=synthetic and must be explicitly admitted only for testing the reference checker.

Run `python scripts/assurance_check.py examples/qa-manifest.json examples/qa-report-synthetic.json` and expect rejection. Add `--allow-synthetic` only to test record consistency. A consistent result still states lifecycle_approval=false and authenticated_producer=false.

The schema examples illustrate purpose/obligation/port/work links. They do not automatically create native AgilePlus objects, implement SROC/CDP, or qualify Tracera's runtime. Replace them with actual source-derived records only through approved adapters and preserve the original source data/visibility.

## Ecosystem impact attachment

`ecosystem-impact.json` is a synthetic planning example for owned reuse and tiered consumers. It records no real consumer discovery, executed test, benefit measurement or approval. `schemas/ecosystem-impact.schema.json` can require fields but cannot assess actual architecture or prove semantic compatibility.
