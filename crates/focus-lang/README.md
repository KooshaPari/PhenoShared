# focus-lang

FocalPoint Language (FPL) compiler from Starlark to IR. First slice focuses on Rule primitive only. Converts human-readable Starlark programs into `focus-ir::Document` with full error recovery and source location tracking.

## Purpose

Enables rule authors to write policies in a familiar Python-like syntax without learning JSON/IR format. Starlark provides safety (no arbitrary code execution), familiarity (Python-like), and extensibility. Compiler produces IR that other layers (templates, storage, transpilers) consume.

## Key Types

- `Compiler` — transforms Starlark AST to IR documents
- `CompileError` — variants with source location, helpful messages
- `RuleBuilder` — constructs Rule IR from Starlark declarations
- `Diagnostics` — error recovery and multi-error collection

## Entry Points

- `Compiler::compile()` — parse and compile Starlark source to IR
- `Compiler::compile_rule()` — compile single rule declaration
- Error handling with source location and context

## Functional Requirements

- FPL syntax validation
- Starlark → Rule IR compilation
- Error messages with line numbers and context

## Consumers

- `focus-templates` (load and validate rule packs)
- Web/CLI rule editors (IDE integration)
- Admin tooling for rule deployment
