# docslib - Documentation Engine

> Documentation engine with multiple output formats and plugin system.

## Overview

docslib is a Go library for building documentation systems with:
- **Multiple Formats**: Markdown, HTML, PDF, ePub
- **Plugin System**: Extensible renderers and parsers
- **Versioning**: Multi-version documentation support
- **Search**: Full-text search indexing

## Architecture

```
docslib/
├── pkg/
│   ├── parser/          # Documentation parser
│   ├── renderer/       # Output renderers
│   ├── plugins/        # Plugin system
│   └── api/            # Public API
├── templates/          # Output templates
└── examples/           # Usage examples
```

## xDD Methodologies Applied

| Category | Methodology |
|----------|-------------|
| Development | TDD, BDD, DDD, ATDD, SDD |
| Design | SOLID, DRY, KISS, YAGNI |
| Architecture | Clean, Hexagonal |

## Installation

```bash
go get github.com/kooshapari/docslib
```

## Quick Start

```go
package main

import (
    "github.com/kooshapari/docslib"
)

func main() {
    doc := docslib.Parse("README.md")
    html := doc.RenderHTML()
    docslib.Write("README.html", html)
}
```

## Features

### Parsers
- Markdown
- reStructuredText
- AsciiDoc

### Renderers
- HTML5
- PDF (via wkhtmltopdf)
- ePub
- Man pages

## Documentation

- [API Documentation](https://pkg.go.dev/github.com/kooshapari/docslib)
- [Examples](./examples/)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT OR Apache-2.0
