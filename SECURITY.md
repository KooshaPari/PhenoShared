# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in NanoVMS, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. **Email** the maintainers at the address in `package.json` or `go.mod` with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)
3. **Response time:** We aim to acknowledge within 48 hours and provide a fix timeline within 7 days.

## Security Model

NanoVMS implements defense-in-depth across multiple isolation tiers:

### Isolation Tiers

| Tier | Mechanism | Trust Level | Use Case |
|------|-----------|-------------|----------|
| 1 (WASM) | Process + WASM sandbox | Trusted | Fast tools, known code |
| 2 (gVisor) | Container (runsc) | Semi-trusted | Browser automation, third-party tools |
| 3 (Firecracker) | MicroVM | Untrusted | Full isolation, untrusted workloads |

### API Security

- **Authentication:** Bearer token via `NVMS_TOKEN` environment variable
- **Authorization:** Token validated on every API request
- **Transport:** TLS for production deployments
- **Rate limiting:** Built-in rate limiter middleware

### Container Security

- Production Docker images run as **non-root** user (`nvms`)
- **Read-only filesystem** in production container
- **No new privileges** security option enabled
- **Minimal attack surface:** Only `ca-certificates` in runtime image

### Input Validation

- All API inputs validated via Go struct tags and custom validators
- Shell injection prevention on all adapter commands
- Environment variable isolation between sandboxes
- Path traversal protection on file operations

### Network Isolation

- Sandboxes run in isolated network namespaces
- No inter-sandbox communication unless explicitly configured
- Egress filtering via iptables/nftables rules

## Threat Model

### Assets Protected

1. **Sandbox isolation:** Ensuring workloads cannot escape their isolation tier
2. **API integrity:** Preventing unauthorized sandbox creation/modification
3. **Data confidentiality:** Sandbox data not accessible across tenants
4. **System availability:** Preventing denial-of-service via resource exhaustion

### Trust Boundaries

```
┌─────────────────────────────────────────────┐
│  Host OS                                    │
│  ┌───────────────────────────────────────┐  │
│  │  NanoVMS API Server                   │  │
│  │  (authenticated, rate-limited)        │  │
│  └───────────────┬───────────────────────┘  │
│                  │                           │
│  ┌───────────────▼───────────────────────┐  │
│  │  Orchestration Engine                 │  │
│  │  (tier selection, lifecycle mgmt)     │  │
│  └───────────────┬───────────────────────┘  │
│                  │                           │
│  ┌───────────────▼───────────────────────┐  │
│  │  Isolation Tier                       │  │
│  │  ┌─────┐ ┌───────┐ ┌─────────────┐  │  │
│  │  │WASM │ │gVisor │ │Firecracker  │  │  │
│  │  └─────┘ └───────┘ └─────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Known Limitations

- WASM tier requires trusted code (no sandbox escape protection for malicious WASM)
- gVisor tier relies on Linux kernel syscall filtering (not a full VM)
- Firecracker tier requires KVM support (not available on macOS/Windows)
- Rate limiting is per-server, not distributed

## CVE Process

1. **Discovery:** Internal audit or external report
2. **Triage:** Assess severity (Critical/High/Medium/Low)
3. **Fix:** Develop and test patch
4. **Disclosure:** Coordinate with reporter, prepare advisory
5. **Release:** Patched version with security fix
6. **Post-mortem:** Document lessons learned

## Security Hardening Checklist

- [x] Non-root container user
- [x] Read-only filesystem in production
- [x] No new privileges
- [x] Bearer token authentication
- [x] Input validation on all API endpoints
- [x] Shell injection prevention
- [x] Environment variable isolation
- [ ] TLS certificate management (production deployment responsibility)
- [ ] Distributed rate limiting (future enhancement)
