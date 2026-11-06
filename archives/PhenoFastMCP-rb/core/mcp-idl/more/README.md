# Additional Runtimes

This directory hosts bindings for additional language runtimes beyond Rust and Go.

## Adding a new language

1. Create a subdirectory named after the language (e.g., `swift/`, `kotlin/`)
2. Add a CI job to `.github/workflows/build.yml` that builds/tests the binding
3. Add a code-gen step to `tools/codegen.sh`
4. Update the top-level `core/mcp-idl/README.md` with the new layout
