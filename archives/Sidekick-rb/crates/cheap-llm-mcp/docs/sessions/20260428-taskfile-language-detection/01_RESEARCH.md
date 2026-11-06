# Research

- Repo language is Python.
- `pyproject.toml` is the only language manifest in the checkout.
- `Taskfile.yml` already existed on `main`, so this change updates the file rather than adding it
  from scratch.

Detection rule used:
- `pyproject.toml`, `requirements.txt`, or `setup.py` -> Python
- `package.json` -> Node
- `Cargo.toml` -> Rust
- `go.mod` -> Go
- `Makefile` -> make fallback
