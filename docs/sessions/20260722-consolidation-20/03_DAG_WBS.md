# DAG and Work Breakdown

## Dependency Graph

```text
inventory confirmation
  -> default-branch and fork resolution
  -> Batch A placement correction
  -> partial bare-clone evidence capture
  -> SHA parity + content parity
  -> disposition review
       -> HOLD remains preserved
       -> VERIFY-ONLY remains blocked or gains proof
       -> exactly one completed READY action: AgilePlus-recovery-20260714
            -> immediate preflight [complete]
            -> rename to zz-archive-AgilePlus-recovery-20260714 [complete]
            -> ARCHIVED-PRESERVED, never deleted [complete]
```

## Lane T Work Breakdown

| Work package | Dependency | Exit condition |
|---|---|---|
| T1 inventory | none | Exact 20 reconciled |
| T2 metadata | T1 | Archive, fork, and actual default branch recorded |
| T3 evidence | T2 | Partial bare-clone SHA/content evidence captured |
| T4 correction | T2 | Batch A misplacements corrected |
| T5 disposition | T3, T4 | Complete: one READY action authorized; other 19 HOLD/VERIFY-ONLY |
| T6 READY preflight | T5 | Complete: sole head, exact commit/tree, and canonical exact head revalidated |
| T7 READY archive | T6 | Complete: `zz-archive-AgilePlus-recovery-20260714` is `ARCHIVED-PRESERVED`; never deleted |
| T-P preservation | all | Complete for #1: no deletion, force-push, or history rewrite; other 19 unchanged |
| T8 tranche-2 audit | T-P | Complete: six candidates, 16 heads, one tag audited |
| T9 tranche-2 disposition | T8 | Harmonizer parity-proven/policy-hold; five evidence holds |
| T10 policy resolution | T9 | Sponsor resolves `archive=false` before harmonizer archival |
| T11 tranche-3 audit | T9 | Complete: six candidates and 49 heads audited |
| T12 tranche-3 disposition | T11 | One parity-proven/policy-hold; five missing-ref holds |
| T13 provenance-import design | T12 | Pending sponsor authorization: propose additive namespaced imports; do not execute implicitly |
| T14 tranche-4 audit | T12 | Complete: final seven repository boundaries classified |
| T15 first-20 disposition closure | T14 | Complete: 20/20 classified; execution gates remain explicit |
