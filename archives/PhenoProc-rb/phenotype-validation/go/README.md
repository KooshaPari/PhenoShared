# Phenotype.Validation - Go

## Overview

Go implementation of the Phenotype.Validation schema validation library.

## Installation

```bash
go get github.com/phenotype/validation-go
```

## Quick Start

```go
import "github.com/phenotype/validation-go/validation"

validator := validation.NewJSONSchemaValidator()
result, err := validator.Validate(schemaJSON, documentJSON)
if !result.IsValid {
    for _, err := range result.Errors {
        fmt.Println(err)
    }
}
```

## License

MIT
