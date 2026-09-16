# phenotype-registry Python SDK

Python bindings for [phenotype-registry](https://github.com/kooshapari/phenotype-registry), built with [PyO3](https://pyo3.rs) and [maturin](https://github.com/PyO3/maturin).

## Installation

Install from PyPI:

```bash
pip install phenotype-registry
```

Or install directly from source (requires a Rust toolchain):

```bash
pip install maturin
git clone https://github.com/kooshapari/phenotype-registry.git
cd phenotype-registry/crates/pheno-registry-python
maturin develop
```

## Usage

```python
from phenotype_registry import parse_ecosystem_map

ecosystem_md = """
| Repository   | Role        | Language | Status |
|------------- |------------ |----------|--------|
| my-app       | SDK         | Rust     | Active |
| my-lib       | shared-lib  | Python   | Active |
"""

entries = parse_ecosystem_map(ecosystem_md)
for entry in entries:
    print(entry.name, entry.role)
    print(entry.to_dict())
```

## API

### `parse_ecosystem_map(input: str) -> list[RepoEntry]`

Parse an ecosystem map markdown document and return a list of `RepoEntry` objects.

**Raises:** `ValueError` if the input is empty or contains malformed tables.

### `RepoEntry`

A parsed repository entry with the following attributes:

| Attribute      | Type              | Description                                    |
|---------------|-------------------|------------------------------------------------|
| `name`        | `str`             | Repository name                                |
| `role`        | `str`             | Role classification (e.g. `"shared-lib"`, `"SDK"`) |
| `language`    | `str \| None`     | Primary programming language                   |
| `status`      | `str \| None`     | Lifecycle status (e.g. `"Active"`, `"Archived"`) |
| `notes`       | `str \| None`     | Free-form notes                                |
| `dependencies`| `list[str]`       | Names of repositories this one depends on      |

#### Methods

- **`to_dict()`** — Return a `dict` representation of the entry.
- **`__repr__()`** / **`__str__()`** — String representations.

## Development

```bash
# Run tests
cd crates/pheno-registry-python
maturin develop
pytest python/tests/

# Build a release wheel
maturin build --release
```

## License

MIT — see [LICENSE-MIT](../../LICENSE-MIT) for details.
