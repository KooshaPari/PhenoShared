# ForgeCode Fork Specification

> Extended code generation system

## Overview

Fork of forgecode with Phenotype-specific enhancements.

## Extensions

### Templates
- Phenotype API templates
- Hexagonal architecture scaffolds
- Microservice boilerplate

### Transformers
- Phenotype naming conventions
- Integration patterns
- Standard configurations

### Hooks
- Pre-generation validation
- Post-generation formatting
- Auto-commit support

## Configuration

```yaml
forgecode:
  templates_dir: ./templates
  output_dir: ./generated
  
  hooks:
    pre_generate:
      - validate_schema
    post_generate:
      - format_code
      - run_linter
```
