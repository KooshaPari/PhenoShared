# Reference tooling boundaries

Use Python 3.11 or newer in an isolated environment. `validate_package.py` additionally uses jsonschema from requirements.txt. Commands are read-only with respect to the supplied package; redirect their output to an appropriate report file if needed.

- `python scripts/validate_package.py .` checks documentation/registry integrity and schema examples. It does not scan external links, verify every anchor or prove semantic completeness.
- `python scripts/assurance_check.py examples/qa-manifest.json examples/qa-report-synthetic.json` deliberately rejects synthetic evidence. `--allow-synthetic` enables teaching fixtures only. The checker enforces a subset of record semantics and always refuses to grant lifecycle approval.
- `python scripts/estimate_dag.py work/tasks.json` reports UNESTIMATED while three-point estimates are absent. It can calculate dependency-only PERT once real estimates are supplied. It never fabricates a resource-constrained or calendar schedule.
- `python -m unittest discover -s tests -v` exercises reference tooling only.

These scripts are not replacements for native code indexing, test execution, coverage generation, signed CI receipts, actual AgilePlus operations or a production security policy. An authenticated producer can still make a wrong claim; payload hashes and JSON validity alone do not establish truth. Qualify real adapters before using these records to accept a product.
