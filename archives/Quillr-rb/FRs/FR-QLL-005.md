# FR-QLL-005: Retry

**Requirement:** Retry delay SHALL use exponential backoff: `baseDelay * 2^attempt + jitter`.

**Traces To:** PRD.md

**Code Location:** `src/retry/`

**Repository:** Quillr

**Status:** Active

**Test Traces:** `src/__tests__/client.test.ts::Retry Logic`
