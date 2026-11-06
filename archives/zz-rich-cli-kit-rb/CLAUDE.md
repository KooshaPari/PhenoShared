# rich-cli-kit

Inline rich terminal output — images, progress bars, status panels — emitted via the kitty graphics protocol when the terminal supports it (Ghostty, kitty, WezTerm), with graceful plain-ASCII fallback. Also ships an MCP server exposing rich output tools.

## Stack
| Layer | Technology |
|-------|------------|
| Core | Rust (cargo workspace, 2 crates) |
| MCP | Python (FastMCP) |
| Graphics | kitty graphics protocol |
| Terminal | ANSI/TUI escape sequences |
| Testing | Rust tests, Python tests |

## Key Commands
```bash
# Rust crates
cargo build --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
cargo fmt --all

# Python MCP server
cd mcp/rich_cli_mcp
pip install -e .
python -m rich_cli_mcp

# CLI tool (rck binary)
cargo run -p rck-cli -- --help
rck detect
rck image path/to/image.png
rck progress --title "Building..." --current 5 --total 10
rck demo
```

## Key Files
- `crates/rck-core/` — Capability detection + kitty-graphics encoder
- `crates/rck-cli/` — `rck` binary (detect | image | progress | panel | demo)
- `mcp/rich_cli_mcp/` — FastMCP server with rich.* tools over stdio
- `shaders/` — GLSL/shader assets
- `tests/` — Integration tests
- `docs/` — Documentation
- `deny.toml` — cargo-deny config

## Reference
Global Phenotype rules: see `~/.claude/CLAUDE.md` or `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md`
