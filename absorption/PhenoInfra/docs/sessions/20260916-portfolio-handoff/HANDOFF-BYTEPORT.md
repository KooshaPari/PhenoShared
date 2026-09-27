# HANDOFF: BytePort Scope

**Date:** 2026-09-16
**Scope:** BytePort (Tauri desktop app + Go backend)

---

## Current State

### Release: v1.0.0 (LATEST)
- **URL:** https://github.com/KooshaPari/BytePort/releases/tag/v1.0.0
- **Assets:** 7 binaries (universal macOS DMG, .app.tar.gz, .deb, .rpm, .AppImage, .exe, .msi)
- **Built by:** GitHub Actions CI (Tauri action)
- **Local dir:** `~/CodeProjects/Phenotype/repos/wt-byteport-tauri-20260911`

### Landing Page
- Deployed at `byteport-landing` on Vercel ✓
- **BLOCKED:** CNAME record `byteport.phenotype.space → cname.vercel-dns.com` needed

### Shared Dependencies
- **None wired yet.** BytePort does NOT consume PhenoInfra shared crates
- Could benefit from: `phenotype-crypto`, `phenotype-health`, `phenotype-observability`

### Repo Hygiene Issues
- ~100+ `.profraw` files in repo root (coverage artifacts, not in .gitignore)
- `crt.pem` committed (check if sensitive)
- `_log_bp.txt`, `_logs_32465547013` committed

### Architecture
- **Backend:** Go (in `backend/` and `src/`)
- **Frontend:** Svelte (in `frontend/web/`)
- **Desktop:** Tauri v2 (in `frontend/web/src-tauri/`)
- **CI:** GitHub Actions with Tauri build action

### Recent Commits (last 5)
```
0b4a23b fix: remove tracing_subscriber that conflicts with tauri_plugin_log
c0aff200 fix: remove duplicate tauri_plugin_log initialization
82555b5e fix(ci): checkout main for install script update (fix detached HEAD)
952bce26 fix(ci): simplify release - let tauri-action handle uploads
c9f9c780 fix(ci): fix macOS brew install syntax
```

---

## Related Repos in Scope

### PhenoShared (formerly phenoAI → pheno → PhenoShared)
- **URL:** https://github.com/KooshaPari/PhenoShared
- **Local dir:** `~/CodeProjects/Phenotype/repos/PhenoAI` (remote updated to PhenoShared.git)
- Has PhenoInfra shared crate deps on main ✓

---

## Blockers
1. CNAME DNS for byteport.phenotype.space (need CF API token with DNS:Edit for phenotype.space)
2. Cloudflare MCP server setup (token auth issue)

## Next Steps
1. Clean up .profraw files from repo + add to .gitignore
2. Wire PhenoInfra shared crates (phenotype-crypto, phenotype-health, phenotype-observability)
3. CVP evidence generation for BytePort
4. v1.1.0 planning
