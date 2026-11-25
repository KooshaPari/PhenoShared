# Python Template Specification

> Project template specification

## Overview

Cookiecutter template for Python projects.

## Structure

```
{{project_name}}/
├── src/
│   └── {{package_name}}/
│       ├── __init__.py
│       └── main.py
├── tests/
│   └── test_main.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

## Tools

- Poetry for dependencies
- Ruff for linting
- Black for formatting
- pytest for testing
- mypy for type checking
- pre-commit for hooks

## Variables

- `project_name` - Repository name
- `package_name` - Python package name
- `description` - Project description
- `author` - Author name
- `email` - Author email
