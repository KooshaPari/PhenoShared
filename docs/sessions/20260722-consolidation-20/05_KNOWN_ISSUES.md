# Known Issues

| Issue | Impact | Required resolution |
|---|---|---|
| Eight sources use non-`main` defaults | Old scripts may compare the wrong branch | Resolve and record each actual default branch |
| Batch A placement errors | Prior disposition evidence may be attached incorrectly | Reconcile repository-to-destination placement |
| Disk is 98% full, about 22 GiB free | Full clones risk exhaustion | Use partial bare clones only |
| Recovery evidence is unique | Deletion would destroy preservation evidence | Keep `AgilePlus-recovery-evidence-20260714` on HOLD and never delete it |
| `Stashly` contradiction | Disposition is unsafe | Keep on HOLD until contradiction closes |
| `phenotype-teamcomm` contradiction | Disposition is unsafe | Keep on HOLD until contradiction closes |
| Ecosystem validator baseline fails | Global validation is not currently green | Track baseline: 18 reachable, 2 unreachable, 17 drift, 47 items |
| Docs build baseline fails | Full docs gate cannot pass in this session | Fix Vue missing end tag at `docs/specs/pheno-specs/specs/platform/build-system/PRD.md:65:60` |
| Preservation manifest sets `archive=false` | Harmonizer parity is proven but execution authority conflicts | Keep POLICY-HOLD pending sponsor resolution |
| Five tranche-2 archives lack complete ref/parent proof | Archival could strand unique history | Preserve sources and import missing refs before reconsideration |
| Five tranche-3 archives have missing refs | 26 commit objects are absent; additional reachable objects lack complete namespaced refs | Import exact namespaced refs and re-run commit/tree checks |
| Registry archive has 23 heads | Fourteen objects are reachable but the full source ref namespace is absent | Import all 23 heads, including nine missing objects |
| Recovery evidence contains raw Git artifacts | Historical secrets or deleted material may be retained | Keep private; require dedicated secret scan before any extraction/publication |
| Quillr has 25 live heads after remote restoration | Prior absorption/deletion records no longer prove current parity | Build an exact 25-ref destination map |
| Router and template sources are not preserved in designated parents | Absorption claims would strand source history | Design sponsor-approved additive imports; keep sources live |
| Stashly and teamcomm registry records conflict | Forced absorption could erase canonical product boundaries | Reconcile registry roles as KEEP-STANDALONE |

## Resolved During This Session

The docket #1 drift risk was closed by immediate preflight and postverification. The source is now
`zz-archive-AgilePlus-recovery-20260714`, `ARCHIVED-PRESERVED / complete`, with exact source and
canonical ref/commit/tree identity retained and no deletion.

No remaining issue authorizes bypassing SHA/content parity or preservation controls. All other 19
repositories remain HOLD or VERIFY-ONLY.
