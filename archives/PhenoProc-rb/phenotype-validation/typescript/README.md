# Phenotype.Validation - TypeScript

## Overview

TypeScript implementation of the Phenotype.Validation schema validation library.

## Installation

```bash
npm install @phenotype/validation
```

## Quick Start

```typescript
import { JsonSchemaValidator } from '@phenotype/validation';

const validator = new JsonSchemaValidator();
const result = validator.validate(schema, document);
if (!result.isValid) {
    console.log(result.errors);
}
```

## License

MIT
