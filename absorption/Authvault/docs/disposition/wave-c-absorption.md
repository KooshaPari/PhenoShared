# Wave C absorption — Authvault

**Date:** 2026-06-17  
**Wave:** C  
**Disposition ids:** 2, 15, 34  
**Source (HexaKit):** `crates/cipher`, `crates/phenotype-crypto`, `crates/phenotype-casbin-wrapper`

## Target layout

| Crate | Canonical path (when landed) |
|-------|------------------------------|
| cipher | `rust/cipher` or workspace member |
| phenotype-crypto | `rust/phenotype-crypto` |
| phenotype-casbin-wrapper | `rust/phenotype-casbin-wrapper` |

## Status

**cipher / phenotype-cipher:** merged — `rust/phenotype-cipher` (Authvault #84).

**phenotype-crypto (id 15), phenotype-casbin-wrapper (id 6):** relocated to `rust/phenotype-crypto` and `rust/phenotype-casbin-wrapper`; HexaKit exclude + git pin.

**phenotype-security-aggregator (id 34):** pending batch 3.

## References

- [DOMAIN_ROLES — secrets](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/DOMAIN_ROLES.md)
- [disposition-index id 2, 15](https://github.com/KooshaPari/phenotype-registry/blob/main/registry/disposition-index.json)
