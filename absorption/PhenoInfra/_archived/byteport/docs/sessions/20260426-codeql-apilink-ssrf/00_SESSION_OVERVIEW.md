# CodeQL API Link SSRF Fix

## Goal

Resolve CodeQL `go/request-forgery` in `backend/byteport/lib/apilink.go` while preserving BytePort's portfolio API link validation behavior.

## Success Criteria

- Portfolio root endpoints are validated before outbound request construction.
- Unsafe localhost, private, and link-local targets are rejected by default.
- Operators can explicitly allow known portfolio hosts with `BYTEPORT_PORTFOLIO_API_ALLOWED_HOSTS`.
- Focused Go tests cover URL validation and host allowlisting.
