# Cutover Steps — Sidekick Bootstrap

## Current Status

✅ **Bootstrap Complete**
- 3 crates copied: `sidekick-presence`, `sidekick-dispatch`, `sidekick-cheap-llm`
- Workspace: `cargo check --workspace` passes (0 errors)
- Documentation: README, CLAUDE.md, AGENTS.md, consolidation notes
- Git: Sidekick initialized + committed to repos/ parent

## Crates Verified

| Crate | Type | Status |
|-------|------|--------|
| sidekick-dispatch | Rust | ✅ Checked + builds |
| sidekick-presence | Python + launchd | ✅ Copied (pyproject.toml present) |
| sidekick-cheap-llm | Python + FastMCP | ✅ Copied (pyproject.toml present) |
| sidekick-messaging | TBD | ⏸️ agent-imessage not found |

## Cutover Sequence (User-Initiated)

### Phase 1: Verify & Approve
1. User reviews Sidekick workspace structure
2. Confirm crate names, namespace, and organization
3. Approve cutover timeline

### Phase 2: Migrate Imports (Agent Task)
1. Scan Phenotype org for imports of:
   - `agent-user-status` → replace with `sidekick-presence`
   - `thegent-dispatch` → replace with `sidekick-dispatch`
   - `cheap-llm-mcp` → replace with `sidekick-cheap-llm`
2. Update Cargo.toml + pyproject.toml in all consuming repos
3. Run full test suite to verify no breakage

### Phase 3: Archive Originals
1. Move 4 source repos to `.archive/`:
   ```bash
   mv repos/{agent-user-status,thegent-dispatch,cheap-llm-mcp,agent-imessage} repos/.archive/
   ```
2. Update `.gitignore` in repos root if needed
3. Commit: `feat(repos): archive agent-utility sources (migrated to Sidekick)`

### Phase 4: Publish & Release
1. Create `v0.1.0` release (from v0.0.1)
2. Publish sidekick-dispatch to crates.io
3. Publish sidekick-presence + sidekick-cheap-llm to PyPI
4. Update documentation across Phenotype org

## Known Gaps to Resolve

1. **sidekick-messaging**: `agent-imessage` source not located
   - Likely embedded in MCP system or CLI codebase
   - Action: Search `.claude/` or MCP registry for integration point
   - Fallback: Stub interface in Sidekick; defer implementation

2. **Python workspace integration**:
   - Root `pyproject.toml` not yet created
   - Each crate self-contained with own pyproject.toml
   - Action: Create unified workspace config after cutover (optional but recommended)

## Rollback Plan

If issues arise post-cutover:
1. Restore from `.archive/` (originals still present)
2. Revert migration commits
3. Resume using separate repos until resolved

## Timeline Estimate

- Phase 1 (Verification): ~15 min
- Phase 2 (Import migration): ~45 min (parallel agent scan + fix)
- Phase 3 (Archive): ~5 min
- Phase 4 (Publish + release): ~20 min
- **Total**: ~1.5h wall-clock

---

**Ready for user approval.**
