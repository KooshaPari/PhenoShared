# BytePort — PLAN.md

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

| Task | Description | Deliverable |
|------|-------------|-------------|
| P1.1 | Go project setup | Module structure, build scripts |
| P1.2 | NVMS parser | Manifest validation, transformation |
| P1.3 | AWS SDK setup | Credentials, base client |
| P1.4 | Frontend shell | UI framework, routing |

### Phase 2: NanoVMS Core (Weeks 3-4)

| Task | Description | Deliverable |
|------|-------------|-------------|
| P2.1 | SpinCLI integration | VM creation, management |
| P2.2 | MicroVM images | Build pipeline, base images |
| P2.3 | Networking | VPC, security groups |
| P2.4 | VM lifecycle | Start, stop, health checks |

### Phase 3: Deploy Engine (Weeks 5-6)

| Task | Description | Deliverable |
|------|-------------|-------------|
| P3.1 | Git integration | Repo clone, branch checkout |
| P3.2 | Service discovery | Multi-service apps |
| P3.3 | Environment config | Env var injection |
| P3.4 | Deploy pipeline | End-to-end flow |

### Phase 4: Portfolio Generation (Weeks 7-8)

| Task | Description | Deliverable |
|------|-------------|-------------|
| P4.1 | LLM integration | OpenAI + LLaMA backends |
| P4.2 | Screenshot capture | Puppeteer/Playwright |
| P4.3 | Template system | Page generation |
| P4.4 | Portfolio hosting | S3 + CloudFront |

### Phase 5: Polish (Weeks 9-10)

| Task | Description | Deliverable |
|------|-------------|-------------|
| P5.1 | UI completion | Dashboard, deploy wizard |
| P5.2 | Error handling | Retry, rollback, alerts |
| P5.3 | Testing | Unit, integration tests |
| P5.4 | Documentation | User guide, API docs |

---

## Resources

| Role | Allocation |
|------|------------|
| Backend Engineer | 2 FTE |
| Frontend Engineer | 1 FTE |
| DevOps Engineer | 0.5 FTE |

---

## Success Criteria

- [ ] Deploy from GitHub in <5 minutes
- [ ] Multi-service app support
- [ ] Auto-generated portfolio pages
- [ ] 99.9% deployed app uptime
- [ ] Zero-downtime redeploys
