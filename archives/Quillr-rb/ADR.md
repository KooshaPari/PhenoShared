# ADR: quill — Type-Safe HTTP Client

## ADR-001: Fetch API as Underlying Transport

**Status**: Accepted

**Context**: HTTP transport options: native `fetch`, `node:http`, `undici`, `axios`.

**Decision**: Native `fetch` API (via global or `node-fetch` polyfill for older Node versions).

**Rationale**: `fetch` is now a global in Node 18+ and all modern browsers. No external dependency needed for the transport layer. `undici` (what `fetch` uses in Node) is performant. Avoids bundling axios which is 13KB.

**Consequences**: Requires Node 18+ for native support. Older Node versions need `node-fetch` as a dev/peer dependency.

---

## ADR-002: Generic Type Parameters over Schema Validation

**Status**: Accepted

**Context**: Two approaches to type-safe responses: (a) generic `<T>` with cast, (b) runtime schema validation and TypeScript inference.

**Decision**: Generic `<T>` parameters without runtime validation. Users bring their own validation (e.g., `model` library `.parse()`).

**Rationale**: Runtime validation adds bundle overhead. quill is a transport layer; schema validation is the caller's responsibility. Users can compose quill with `model` for full validation.

**Consequences**: Incorrect `<T>` annotations are not caught at runtime. Document clearly that `<T>` is a cast, not a validated assertion.

---

## ADR-003: Interceptor API Compatible with axios

**Status**: Accepted

**Context**: Many codebases use axios interceptors. quill should minimize migration friction.

**Decision**: `client.interceptors.request.use()` and `client.interceptors.response.use()` API identical to axios interceptors.

**Rationale**: Teams migrating from axios can reuse their interceptor code with minimal changes. Familiar API lowers adoption friction.

**Consequences**: quill is tied to an API design shaped by axios history. If axios changes its interceptor API, quill must decide whether to track it.
