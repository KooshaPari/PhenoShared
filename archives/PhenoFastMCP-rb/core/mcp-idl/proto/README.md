# Source-of-truth Proto Definitions

Drop `.proto` files here from the upstream MCP spec:

```bash
git subtree pull --prefix core/mcp-idl/proto \
    https://github.com/modelcontextprotocol/specification main --squash
```

Then regenerate:

```bash
./tools/codegen.sh
```
