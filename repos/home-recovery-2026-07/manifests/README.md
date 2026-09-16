# Recovery Manifests

`home_entries.tsv` is the baseline first-level inventory. Additional per-item manifests must
use stable ledger identifiers and must not contain credential values.

Required evidence before a disposition can become `REDUNDANT_VERIFIED`:

1. source identity and content checksum or Git tree;
2. canonical destination;
3. backup target and remote reference;
4. independent remote reachability check;
5. restored-content verification;
6. rollback location and cleanup approval.

