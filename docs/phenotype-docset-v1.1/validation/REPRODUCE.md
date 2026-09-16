# Reproduce the package checks

Use an isolated Python 3.11+ environment. Install scripts/requirements.txt for structural checks; scripts/test-requirements.txt adds the coverage version used here. Report rendering optionally uses scripts/report-requirements.txt.

Run the following from the docs root. Write actively generated validation JSON outside the scanned docs tree, then copy it in after success; otherwise the checker correctly sees its own incomplete output as invalid JSON.

```sh
python -m unittest discover -s tests -v
python scripts/validate_package.py .
python scripts/estimate_dag.py work/tasks.json
```

For each of unit and integration, use a separate coverage database and run only the corresponding test_assurance_<family>.py module:

```sh
python -m coverage run --branch --source=scripts --data-file=/tmp/atlas-coverage-unit -m unittest discover -s tests -p test_assurance_unit.py
python -m coverage json --data-file=/tmp/atlas-coverage-unit --include='*/assurance_check.py' -o /tmp/atlas-unit.json
```

The E2E test runner supports QA_REFERENCE_COVERAGE_DIR pointing to a new empty temporary directory. Each actual child CLI is instrumented separately there; combine only those E2E databases using coverage combine with the matching .coverage.e2e base name. Report only assurance_check.py for the scope recorded in coverage-summary.json. Never combine different families to satisfy an independent gate.

The shared corpus contains 41 semantic negative vectors. Unit tests use direct functions and mocked CLI read failures; integration tests use real JSON files and the entrypoint in process; E2E uses actual CLI subprocesses. All are synthetic teaching/reference fixtures. They are not production evidence for any portfolio repository.

The first final-output redirection attempted inside the scanned tree was correctly rejected as an empty active JSON file. Validation was rerun with an external output file, then the completed report was copied back. No checker bypass or exclusion was introduced to hide that condition.
