# FR-QLL-006: Error Types

**Requirement:** `HttpError` SHALL include status, statusText, url, method, body. `NetworkError` for connection failures. `TimeoutError` for timeout.

**Traces To:** PRD.md

**Code Location:** `src/types.ts`

**Repository:** Quillr

**Status:** Active

**Test Traces:** `src/__tests__/traceability.test.ts::FR-QLL-006: Error Types`
