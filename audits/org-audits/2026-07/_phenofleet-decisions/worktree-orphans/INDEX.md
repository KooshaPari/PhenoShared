# Worktree-Orphan Tarballs — Index

**Generated**: 2026-07-15
**Total tarballs**: 14
**Action**: all TARBALL_ORPHAN
**Location**: `_phenofleet-decisions/worktree-orphans/`
**SHA256 manifest**: `_phenofleet-decisions/worktree-orphans/SHA256SUMS.txt`

All 14 broken worktree pointers identified in Section 4.3 of `.research-repos-gitification-2026-07-15.md` have been tarballed. Each source directory has been **left in place** (per policy: conservative on deletion) and now contains a `WORKTREE_ORPHAN_SENTINEL.md` explaining what happened.

## Tarball summary

| # | Source dir | Intended parent | Tarball | SHA256 (short) | Size |
|---|------------|-----------------|---------|----------------|------|
| 1 | `Grapheon/.claude/worktrees/l101-motion` | `Tracera` | `Grapheon-l101-motion.tar.zst` | `d6168c2e12e7…` | 17.7 KB |
| 2 | `Grapheon/.claude/worktrees/l104-readme-tracera` | `Tracera` | `Grapheon-l104-readme-tracera.tar.zst` | `4951aa8bb1bc…` | 17.7 KB |
| 3 | `Grapheon/.claude/worktrees/l105-docs-assets` | `Tracera` | `Grapheon-l105-docs-assets.tar.zst` | `237b6d588be2…` | 17.7 KB |
| 4 | `Grapheon/.claude/worktrees/tracera-splash` | `Tracera` | `Grapheon-tracera-splash.tar.zst` | `657acc33292a…` | 17.7 KB |
| 5 | `Grapheon/.claude/worktrees/tracera-tokens` | `Tracera` | `Grapheon-tracera-tokens.tar.zst` | `e4635091f117…` | 17.7 KB |
| 6 | `Grapheon/.claude/worktrees/v38-scorecards` | `Tracera` | `Grapheon-v38-scorecards.tar.zst` | `d517137077b5…` | 17.7 KB |
| 7 | `OmniRoute/.claude/worktrees/docs-substrate-http-url` | `OmniRoute` | `OmniRoute-docs-substrate-http-url.tar.zst` | `09bbcce115c5…` | 1.8 MB |
| 8 | `OmniRoute/.claude/worktrees/feat-sveltekit-v2` | `OmniRoute` | `OmniRoute-feat-sveltekit-v2.tar.zst` | `7ce5e0364a5e…` | 23.0 MB |
| 9 | `OmniRoute/.worktrees/rtk-pr6774` | `omniroute-upstream-work` | `OmniRoute-rtk-pr6774.tar.zst` | `fb742e6357eb…` | 24.1 MB |
| 10 | `OmniRoute/.worktrees/rtk-pr6774/.build/next/standalone` | `omniroute-upstream-work` | `OmniRoute-rtk-pr6774-build-next-standalone.tar.zst` | `bac80e44133d…` | 23.8 MB |
| 11 | `phenotype-org-audits-wtrees/home-recovery-2026-07` | `poa-fresh (does not exist)` | `poa-wtrees-home-recovery-2026-07.tar.zst` | `73154d0d3fee…` | 1.3 MB |
| 12 | `phenotype-org-audits-wtrees/home-recovery-2026-07-v2` | `phenotype-org-audits (not in repos/)` | `poa-wtrees-home-recovery-2026-07-v2.tar.zst` | `da3c166f7f6c…` | 1.3 MB |
| 13 | `sharecli/.claude/worktrees/sharecli-l141-util` | `sharecli` | `sharecli-sharecli-l141-util.tar.zst` | `426a74d102b1…` | 4.2 MB |
| 14 | `worktrees/PhenoCompose-audit-followups` | `PhenoCompose (lives outside repos/)` | `worktrees-PhenoCompose-audit-followups.tar.zst` | `5e30ee77c1ca…` | 310.4 KB |

## Restore commands

For any tarball, the generic restore sequence is:

```bash
# 1. Verify integrity
cd ~/CodeProjects/Phenotype/repos
sha256sum -c _phenofleet-decisions/worktree-orphans/SHA256SUMS.txt

# 2. Extract to a scratch dir (the tarballs preserve the original dir name as the top entry)
mkdir -p /tmp/restore-orphans
tar --zstd -xf _phenofleet-decisions/worktree-orphans/<tarball-name>.tar.zst \
    -C /tmp/restore-orphans

# 3. Decide: re-attach as a real worktree (requires parent repo to exist),
#    or just keep the extracted copy as a snapshot.
```

## Per-tarball restore details

### 1. `Grapheon/.claude/worktrees/l101-motion`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/Grapheon-l101-motion.tar.zst`
- **SHA256**: `d6168c2e12e752fe1078094138ac39107489fb6a72463b475ea68c9ef8cd89e3`
- **Source size**: 80K (2 files)
- **Intended parent repo**: `Tracera`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/l101-motion`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/Grapheon-l101-motion.tar.zst -C /tmp/restore-orphans
```

### 2. `Grapheon/.claude/worktrees/l104-readme-tracera`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/Grapheon-l104-readme-tracera.tar.zst`
- **SHA256**: `4951aa8bb1bc00b70623d6059578258ccaa09592f940330ab62d41f34e606d8a`
- **Source size**: 80K (2 files)
- **Intended parent repo**: `Tracera`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/l104-readme-tracera`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/Grapheon-l104-readme-tracera.tar.zst -C /tmp/restore-orphans
```

### 3. `Grapheon/.claude/worktrees/l105-docs-assets`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/Grapheon-l105-docs-assets.tar.zst`
- **SHA256**: `237b6d588be2b125b7fde08736e8605a0d19618a672d57945729a6b82355a27c`
- **Source size**: 80K (2 files)
- **Intended parent repo**: `Tracera`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/l105-docs-assets`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/Grapheon-l105-docs-assets.tar.zst -C /tmp/restore-orphans
```

### 4. `Grapheon/.claude/worktrees/tracera-splash`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/Grapheon-tracera-splash.tar.zst`
- **SHA256**: `657acc33292a363e662caa421c4a78035690f28f8a6b64c0761ff0a2965a89ea`
- **Source size**: 80K (2 files)
- **Intended parent repo**: `Tracera`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/tracera-splash`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/Grapheon-tracera-splash.tar.zst -C /tmp/restore-orphans
```

### 5. `Grapheon/.claude/worktrees/tracera-tokens`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/Grapheon-tracera-tokens.tar.zst`
- **SHA256**: `e4635091f1170c26b4b0896a550d6dbc92966afb761123b695c91ccb4190b6a6`
- **Source size**: 80K (2 files)
- **Intended parent repo**: `Tracera`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/tracera-tokens`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/Grapheon-tracera-tokens.tar.zst -C /tmp/restore-orphans
```

### 6. `Grapheon/.claude/worktrees/v38-scorecards`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/Grapheon-v38-scorecards.tar.zst`
- **SHA256**: `d517137077b5ac3543f261120b4bd12cabe11162a4421481d1003ecbb4bf12cf`
- **Source size**: 80K (2 files)
- **Intended parent repo**: `Tracera`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/v38-scorecards`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/Grapheon-v38-scorecards.tar.zst -C /tmp/restore-orphans
```

### 7. `OmniRoute/.claude/worktrees/docs-substrate-http-url`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/OmniRoute-docs-substrate-http-url.tar.zst`
- **SHA256**: `09bbcce115c5b30576168b2aa61a5a3104027ee056b9de25e70b5528b5232c68`
- **Source size**: 9.3M (552 files)
- **Intended parent repo**: `OmniRoute`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/OmniRoute/.git/worktrees/docs-substrate-http-url`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/OmniRoute-docs-substrate-http-url.tar.zst -C /tmp/restore-orphans
```

### 8. `OmniRoute/.claude/worktrees/feat-sveltekit-v2`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/OmniRoute-feat-sveltekit-v2.tar.zst`
- **SHA256**: `7ce5e0364a5e206eeead6c1250cfbab4e817e497faa6024457debde0a88b8c50`
- **Source size**: 96M (2922 files)
- **Intended parent repo**: `OmniRoute`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/OmniRoute/.git/worktrees/feat-sveltekit-v2`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/OmniRoute-feat-sveltekit-v2.tar.zst -C /tmp/restore-orphans
```

### 9. `OmniRoute/.worktrees/rtk-pr6774`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/OmniRoute-rtk-pr6774.tar.zst`
- **SHA256**: `fb742e6357eb56c6d01124fdf9237129f3f076f9801ac1e72b6fbaeb80d79a35`
- **Source size**: 5.0G (167693 files)
- **Intended parent repo**: `omniroute-upstream-work`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/omniroute-upstream-work/.git/worktrees/rtk-pr6774`
- **Tarball strategy**: Tarball excludes regenerable build artifacts (node_modules, .build, dist, .next). Reason: node_modules, .build, dist, .next (regenerable build artifacts)

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/OmniRoute-rtk-pr6774.tar.zst -C /tmp/restore-orphans
```

### 10. `OmniRoute/.worktrees/rtk-pr6774/.build/next/standalone`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/OmniRoute-rtk-pr6774-build-next-standalone.tar.zst`
- **SHA256**: `bac80e44133d4b04d2b3961e77c8f9bae231fea8f4e5fd61d861804de435abdc`
- **Source size**: 1.0G (27416 files)
- **Intended parent repo**: `omniroute-upstream-work`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/omniroute-upstream-work/.git/worktrees/rtk-pr6774`
- **Tarball strategy**: Tarball excludes regenerable build artifacts (node_modules, .build, dist, .next). Reason: node_modules, .build, dist, .next (regenerable build artifacts)

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/OmniRoute-rtk-pr6774-build-next-standalone.tar.zst -C /tmp/restore-orphans
```

### 11. `phenotype-org-audits-wtrees/home-recovery-2026-07`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/poa-wtrees-home-recovery-2026-07.tar.zst`
- **SHA256**: `73154d0d3feef49e830d6c18c746e2c2eb198ad60810d72da5cad48aa808b34a`
- **Source size**: 6.5M (440 files)
- **Intended parent repo**: `poa-fresh (does not exist)`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/poa-fresh/.git/worktrees/home-recovery-2026-07`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/poa-wtrees-home-recovery-2026-07.tar.zst -C /tmp/restore-orphans
```

### 12. `phenotype-org-audits-wtrees/home-recovery-2026-07-v2`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/poa-wtrees-home-recovery-2026-07-v2.tar.zst`
- **SHA256**: `da3c166f7f6c5cb14dccc286e2c1fe7712b15a969e26f6ae744c0b2919b0efdf`
- **Source size**: 6.5M (440 files)
- **Intended parent repo**: `phenotype-org-audits (not in repos/)`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-org-audits/.git/worktrees/home-recovery-2026-07-v2`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/poa-wtrees-home-recovery-2026-07-v2.tar.zst -C /tmp/restore-orphans
```

### 13. `sharecli/.claude/worktrees/sharecli-l141-util`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/sharecli-sharecli-l141-util.tar.zst`
- **SHA256**: `426a74d102b1437960a1f8e199dfe25163db8891e6eb0d9d2095fcd18134c7ea`
- **Source size**: 16M (140 files)
- **Intended parent repo**: `sharecli`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/sharecli/.git/worktrees/sharecli-l141-util`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/sharecli-sharecli-l141-util.tar.zst -C /tmp/restore-orphans
```

### 14. `worktrees/PhenoCompose-audit-followups`

- **Tarball**: `_phenofleet-decisions/worktree-orphans/worktrees-PhenoCompose-audit-followups.tar.zst`
- **SHA256**: `5e30ee77c1ca09a5fc5dc63a46c5b32716b0d10175919fec02d62ffddc9049ce`
- **Source size**: 1.8M (254 files)
- **Intended parent repo**: `PhenoCompose (lives outside repos/)`
- **Expected gitdir**: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoCompose/.git/worktrees/PhenoCompose-audit-followups`

```bash
tar --zstd -xf _phenofleet-decisions/worktree-orphans/worktrees-PhenoCompose-audit-followups.tar.zst -C /tmp/restore-orphans
```
