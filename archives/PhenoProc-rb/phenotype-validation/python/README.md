# Phenotype.Validation - Python

## Overview

Python implementation of the Phenotype.Validation schema validation library.

## Installation

```bash
pip install phenotype-validation
```

## Quick Start

```python
from phenotype_validation import JsonSchemaValidator

validator = JsonSchemaValidator()
result = validator.validate(schema_json, document_json)
if not result.is_valid:
    for error in result.errors:
        print(error)
```

## License

MIT
