# Architecture

`phenotype-xdd-lib` follows a layered model:

## Layers

- Domain: pure business logic
- Application: ports and use cases
- Infrastructure: adapters for proptest, quickcheck, and related tooling

## Design Notes

- Keep concerns separated by feature area.
- Re-export commonly used items at the crate root for easy consumption.
- Favor shared abstractions over duplicate helper logic.
