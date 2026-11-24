# Wave C — phenotype-cipher relocation (2026-06-17)

**Disposition id:** 2 (`crates/cipher` / `phenotype-cipher`)  
**Source:** HexaKit `crates/cipher`  
**Target:** `rust/phenotype-cipher` (Authvault workspace member)

## Procedure

1. Copy implementation tree from HexaKit (src only; prune nested CI junk).
2. Add workspace member + standalone `Cargo.toml` deps.
3. `cargo check -p phenotype-cipher` and `cargo check -p authvault`.
4. Follow-up: HexaKit exclude + stub prune + registry FSM `done`.

## PR

Authvault `feat/wave-c-cipher-reloc`
