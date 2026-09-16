# CodeQL API Link SSRF Fix

Goal: resolve CodeQL go/request-forgery in backend/byteport/lib/apilink.go while preserving portfolio API validation behavior.

Research:
- CodeQL go/request-forgery guidance recommends validating user-controlled network request URLs against authorized URLs or hosts before issuing outbound requests.
- BytePort stores a user-provided Portfolio.RootEndpoint and validates it by calling <root>/byteport.
- Existing repo config has broad Spin outbound host examples but no backend/byteport portfolio API allowlist.

Decision:
- Validate portfolio root URLs before request construction.
- Block unsafe schemes, credentials, query strings, fragments, and private/local/link-local destinations by default.
- Support explicit deployment allowlisting through BYTEPORT_PORTFOLIO_API_ALLOWED_HOSTS, including exact localhost for documented local development.
- Revalidate redirect and dial targets to prevent redirect/DNS based SSRF.
