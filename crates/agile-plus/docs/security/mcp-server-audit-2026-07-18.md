# Security Audit: Python MCP Server Code

**Date:** 2026-07-18
**Scope:** `/workspace/python/src/agileplus_mcp/`, `/workspace/agileplus-mcp/src/agileplus_mcp/`, `/workspace/dispatch-mcp/src/dispatch_mcp/`
**Auditor:** Automated security review

---

## Executive Summary

The Python MCP server codebase is **generally well-structured from a security perspective**. No critical command-injection or deserialization vulnerabilities were found. The code avoids common dangerous patterns (`subprocess`, `eval`, `exec`, `pickle`, unsafe `yaml.load`). However, several **medium- and low-severity issues** were identified that should be addressed to harden the codebase for production use.

**Finding count:** 7 findings (0 Critical, 2 Medium, 5 Low/Informational)

---

## Findings

### FINDING 1 — Unvalidated `from_file` path passed to Rust core via gRPC [MEDIUM]

**File:** `python/src/agileplus_mcp/tools/features.py`, lines 29-47
**Category:** Input Validation / Path Traversal

```python
@mcp.tool(name="agileplus_specify")
async def specify(
    feature_slug: str, from_file: str = "", target_branch: str = "main"
) -> dict[str, Any]:
    kwargs: dict[str, str] = {"target_branch": target_branch}
    if from_file:
        kwargs["from_file"] = from_file
    result = await client.run_command("specify", feature_slug=feature_slug, **kwargs)
```

**Issue:** The `from_file` parameter is a user-controlled file path passed directly to the Rust backend via `run_command()` with zero validation. If the Rust core uses this path for file I/O, an attacker could supply a traversal path like `../../../etc/passwd` or `/etc/shadow`.

**Exploitability:** Medium. The actual risk depends on how the Rust backend handles the `from_file` argument. If the Rust side opens and reads this file, this is a path traversal vulnerability. The MCP layer acts as a pass-through with no sanitization.

**Remediation:**
- Validate `from_file` against an allowlist of directories (e.g., must be under `kitty-specs/`)
- Reject paths containing `..` components
- Resolve the path and verify it stays within the workspace root

---

### FINDING 2 — gRPC channel uses `insecure_channel` (no TLS) [MEDIUM]

**Files:**
- `python/src/agileplus_mcp/grpc_client.py`, line 59
- `agileplus-mcp/src/agileplus_mcp/grpc_client.py`, line 32

```python
# python/src/agileplus_mcp/grpc_client.py:59
self._channel = grpc.aio.insecure_channel(self._address)

# agileplus-mcp/src/agileplus_mcp/grpc_client.py:32
self._channel = grpc.insecure_channel(self.target)
```

**Issue:** Both gRPC clients connect to the Rust backend over an **unencrypted, unauthenticated channel**. Traffic between the MCP server and the Rust core (including feature data, governance checks, audit trails) is transmitted in plaintext.

**Exploitability:** Medium in production. On localhost this is acceptable for development, but if the gRPC server runs on a different host (the address is configurable via `AGILEPLUS_GRPC_ADDRESS`), any network observer can read or tamper with traffic. There is no mutual authentication, so a malicious actor could impersonate the Rust core.

**Remediation:**
- Support `grpc.aio.secure_channel()` with TLS certificates
- Make TLS the default for non-localhost addresses
- Add mTLS or token-based authentication for production deployments

---

### FINDING 3 — No input validation on MCP tool string parameters [LOW]

**Files:** All tool modules:
- `python/src/agileplus_mcp/tools/features.py` (lines 28-47, 54-68, 71-88, 90-111)
- `python/src/agileplus_mcp/tools/governance.py` (lines 24-45, 47-58, 60-79, 81-92)
- `python/src/agileplus_mcp/tools/status.py` (lines 25-49, 51-70, 72-88, 90-105)
- `python/src/agileplus_mcp/tools/queue.py` (lines 15-34, 36-55, 64-69, 71-79)
- `python/src/agileplus_mcp/server.py` (lines 93-152, 155-198, 206-222)

**Issue:** None of the MCP tool handlers validate their string inputs beyond Python's type system. Parameters like `feature_slug`, `transition`, `target_branch`, `wp_id`, `item_type`, and `tier` are passed directly to gRPC calls without:
- Length limits (a 100MB string could be sent as a feature_slug)
- Character set validation (feature_slug should be kebab-case per the docstrings, but this isn't enforced)
- Format validation (transition should match a pattern like `state->state`)

**Exploitability:** Low. The Rust core via protobuf will enforce its own schema constraints, and gRPC has default message size limits (~4MB). However, defense-in-depth mandates validating at the MCP boundary.

**Remediation:**
- Add a `validate_slug(s: str)` helper that enforces `^[a-z0-9][a-z0-9-]*$` and a max length (e.g., 128 chars)
- Add length limits to free-text fields
- Validate `transition` format (e.g., `^[a-z_]+->[a-z_]+$`)
- Validate `item_type` against an allowlist

---

### FINDING 4 — gRPC server address configurable via environment variable without validation [LOW]

**File:** `python/src/agileplus_mcp/server.py`, line 35

```python
GRPC_ADDRESS = os.environ.get("AGILEPLUS_GRPC_ADDRESS", "localhost:50051")
```

**Issue:** The gRPC target address is read from the environment with no validation. While environment variables are generally trusted (they require host-level access to set), a misconfiguration could point the MCP server to an attacker-controlled gRPC endpoint.

**Exploitability:** Low. Requires control over the process environment, which typically implies existing host compromise. However, in containerized deployments, environment variable injection can sometimes occur via misconfigured orchestrators.

**Remediation:**
- Validate the address format (host:port)
- Consider an allowlist of permitted gRPC addresses
- Log a warning if the address is not localhost

---

### FINDING 5 — `dispatch-mcp`: OMNIROUTE_URL from environment with partial validation [LOW]

**File:** `dispatch-mcp/src/dispatch_mcp/server.py`, lines 51-67

```python
def _call_omniroute(route: str, payload: dict[str, Any]) -> dict[str, Any]:
    base = os.environ.get("OMNIROUTE_URL")
    if not base:
        raise ValueError("OMNIROUTE_URL environment variable is not set.")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"OMNIROUTE_URL must use http or https scheme, got: {parsed.scheme!r}")
```

**Issue:** The URL is validated for scheme but not for hostname. The `route` parameter (which comes from hardcoded string literals in the current code, not from user input) is concatenated via string formatting. The `follow_redirects=False` setting is good — it prevents open-redirect SSRF. However, the response sanitization in `_sanitize_response` only strips keys at the top level.

**Exploitability:** Low. The route values are hardcoded (`"dispatch"`, `"health"`), not user-controlled. The `OMNIROUTE_URL` requires env-var control. The response allowlist (`_ALLOWED_RESPONSE_KEYS`) is a good defense.

**Positive notes:**
- `follow_redirects=False` prevents SSRF via redirect
- Response key allowlisting prevents information leakage
- Message length is bounded by `MAX_MESSAGE_LENGTH = 4096`
- Tier is validated against `VALID_TIERS` allowlist

---

### FINDING 6 — `queue_import` accepts arbitrary dicts without schema validation [LOW]

**File:** `python/src/agileplus_mcp/tools/queue.py`, lines 71-79

```python
@mcp.tool(name="agileplus_queue_import")
async def queue_import(items: list[dict[str, Any]]) -> dict[str, Any]:
    for item in items:
        title = item.get("title")
        if not title:
            raise ValueError("Each imported backlog item requires a title")
    imported = await client.import_backlog_items(items)
```

Also in `python/src/agileplus_mcp/grpc_backlog.py`, lines 80-105:

```python
async def import_backlog_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item in items:
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError("Each imported backlog item requires a title")
        request_items.append(
            integrations_pb2.CreateBacklogItemRequest(
                type=str(item.get("type") or item.get("item_type") or "task"),
                title=title,
                ...
            )
        )
```

**Issue:** The batch import accepts a list of arbitrary dicts. While `title` is checked for presence, there is:
- No limit on the number of items in a batch (DoS vector via sending thousands of items)
- No validation of individual field lengths
- No validation of field types beyond coercion via `str()`

**Exploitability:** Low. Protobuf serialization provides some inherent limits, and the gRPC max message size caps the total payload. But a malicious MCP client could submit a very large batch causing memory pressure.

**Remediation:**
- Add a batch size limit (e.g., max 100 items per import)
- Add field length limits
- Validate `item_type` against an allowlist

---

### FINDING 7 — Workspace roots expose slug values in file URIs without sanitization [INFORMATIONAL]

**File:** `python/src/agileplus_mcp/server.py`, lines 70-83

```python
for feature in features:
    slug = feature["slug"]
    roots.append({
        "uri": f"file://kitty-specs/{slug}/",
        "name": f"feature-spec-{slug}",
    })
    roots.append({
        "uri": f"file://.worktrees/{slug}/",
        "name": f"feature-worktree-{slug}",
    })
```

**Issue:** Feature slugs returned from gRPC are interpolated into file URIs without validation. If a slug contained path-traversal characters (e.g., `../../etc`), it would produce a malicious URI. However, slugs originate from the Rust backend (a trusted source), not directly from MCP tool input.

**Exploitability:** Very Low. The slug comes from the Rust core, which presumably validates slug format. However, defense-in-depth suggests validating the slug format before interpolation.

**Remediation:**
- Validate slug format (`^[a-z0-9-]+$`) before interpolating into URIs

---

## What Was NOT Found (Positive Findings)

These are security-positive patterns observed in the codebase:

1. **No `subprocess`, `os.system`, `os.popen`, `eval`, or `exec` calls** in any MCP server Python code. Command injection is not possible through the Python layer.

2. **No `pickle.loads`, `yaml.load` (unsafe), or `marshal.loads`** — no deserialization vulnerabilities.

3. **No direct HTTP requests from user input** in the agileplus-mcp server. All external communication goes through structured gRPC protobuf messages.

4. **dispatch-mcp has good output sanitization** — response keys are allowlisted via `_ALLOWED_RESPONSE_KEYS`, preventing information leakage from OmniRoute internals.

5. **dispatch-mcp validates tier and message length** — `VALID_TIERS` allowlist and `MAX_MESSAGE_LENGTH = 4096` prevent abuse.

6. **dispatch-mcp disables HTTP redirect following** — `follow_redirects=False` prevents SSRF via redirect chains.

7. **gRPC retry logic only retries transient errors** — UNAVAILABLE and DEADLINE_EXCEEDED. Non-transient errors are raised immediately, preventing retry-amplification attacks.

8. **Protobuf serialization** provides inherent type safety — fields are typed, and malformed data is rejected at the protocol level.

---

## Risk Matrix

| ID | Severity | Category | File | Exploitable? |
|----|----------|----------|------|-------------|
| F1 | Medium | Path Traversal | `tools/features.py` | Depends on Rust backend |
| F2 | Medium | Cleartext Transport | `grpc_client.py` | Yes, if non-localhost |
| F3 | Low | Input Validation | All tool modules | Limited by protobuf |
| F4 | Low | Configuration | `server.py` | Requires env control |
| F5 | Low | SSRF (partial) | `dispatch-mcp/server.py` | Mitigated well |
| F6 | Low | DoS / Batch Abuse | `tools/queue.py` | Limited by gRPC size |
| F7 | Info | URI Injection | `server.py` | Very low (trusted source) |

---

## Recommended Remediation Priority

1. **F1** — Add `from_file` path validation in `features.py` (quick fix, high value)
2. **F2** — Add TLS support to gRPC client (medium effort, important for production)
3. **F3** — Add input validation helper for slugs and string parameters (moderate effort)
4. **F6** — Add batch size limits to `queue_import` (quick fix)
5. **F7** — Add slug format validation before URI interpolation (quick fix)
6. **F4** — Add gRPC address format validation (quick fix)
7. **F5** — Already well-mitigated; consider hostname allowlist for defense-in-depth
