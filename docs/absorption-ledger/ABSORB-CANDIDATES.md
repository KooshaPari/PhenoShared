# Unlisted active absorb targets

Derived from the live account under the standing instruction that repositories not
named in a given batch, if still active, are valid absorb targets.

Regenerate rather than edit. Totals reconcile exactly: 2 canonical homes + 5 named
in the batch + 4 leave-alone + 25 recovery stores + 50 absorb targets = 86 live
repositories.

Caveat before acting: a few of the 50 are destinations rather than targets.
`PhenoApps` is a read-only sunset shelf that forbids adding source,
`zz-pause-inc-QuadSGM`, `zz-pause-inc-Parpoura` and `zz-pause-Localbase` are the
homes the archives belong in, and `host-ops` was restored by the operator after
being absorbed. Treat the list as scope, not as a work queue.

```
live repos: 86

== absorb targets (unlisted, active, not a recovery store) (50)
  Civis                                    1646.3 MB  pub   Civilization simulation engine: deterministic godgame with m
  OmniRoute                                 991.6 MB  pub   Multi-provider LLM gateway: OpenAI-compatible endpoint with 
  zz-pause-unk-Thegent                      979.9 MB  PRIV  Paused: Python agent runtime with tool registry and LLM abst
  PhenoApps                                 966.6 MB  PRIV  Sunset shelf: retired, paused, and archived app repos
  PhenoMLX                                  901.8 MB  pub   MLX inference engine: Rust performance cores, multi-backend 
  zz-pause-inc-FocalPoint                   808.0 MB  PRIV  Paused: project management UI
  Tracera                                   733.9 MB  pub   Rust traceability infrastructure: audit trails and provenanc
  AgilePlus                                 732.4 MB  pub   Spec-driven development framework: governance, cycles, modul
  Dino                                      642.2 MB  pub   DINOForge: general-purpose mod platform for AI agents in Uni
  zz-archive-grapheon                       416.3 MB  PRIV  Recovered local work - salvaged during the 2026-11-08 worktr
  KCode                                     372.7 MB  pub   Most RAM-efficient coding harness: Rust-native agent executi
  PhenoTooling                              269.5 MB  PRIV  Recovered local work - salvaged during the 2026-11-08 worktr
  ShareCLI                                  215.9 MB  pub   Rust process/resource runtime: high-concurrency agent worklo
  WorldSphereMod                            172.9 MB  pub   3D Worldbox mod: procedural world simulation in Unity
  KooshaPari                                150.0 MB  pub   Engineering profile: portfolio, blog, and project showcase
  zz-pause-Localbase                        101.7 MB  PRIV  Paused: local-first data platform
  zz-archive-AgilePlus-recovery-evidence     98.2 MB  PRIV  Auto-imported from ~/CodeProjects/Phenotype/repos/AgilePlus-
  Khostty                                    91.3 MB  pub   Ghostty terminal fork: GPU-accelerated cross-platform termin
  Portage                                    77.5 MB  pub   Harbor framework: agent evaluations and RL environments
  zz-pause-inc-AgsLag                        74.2 MB  PRIV  Incubating: agslag merge base
  CivicWarfare                               61.9 MB  pub   Cities: Skylines II infrastructure survival mod: docs and ch
  PhenoBot                                   61.4 MB  PRIV  Discord org bot and agent plane for Phenotype: slash command
  Melosviz                                   56.1 MB  pub   Music-to-visual toolkit: FastAPI backend, Tauri desktop, Pyt
  herdr                                      47.5 MB  pub   the runtime your coding agents live on
  PhenoDesign                                44.5 MB  pub   Design system: tokens, components, and UX standards for all 
  zz-pause-ref-AtomsTech                     35.2 MB  PRIV  Determining merge target: AtomsBot merged into AtomsTech
  HeliosLab                                  27.0 MB  pub   Phenotype research lab: experimental AI tooling and evaluati
  PhenoAI                                    21.7 MB  PRIV  Rust agent workspace: router, sidekick, Eidolon runtime, inf
  PhenoLab                                   20.6 MB  PRIV  Compression stack and RLVR harness: eval tooling for quantiz
  PhenoFabric                                17.9 MB  pub   Fabric mesh: capability descriptors, route compiler, failove
  kimaki                                     15.6 MB  pub   all opencode features deeply integrated inside Discord. each
  claude-remember                            14.2 MB  pub   Persistent memory for Claude Code � identity, context, and c
  zz-zz-agentcheck-PhenoInfra                11.0 MB  PRIV  Compute mesh IaC: OCI + CF + GCP + AWS + Vercel, ADRs, specs
  zz-pause-inc-QuadSGM                        9.1 MB  PRIV  Incubating: SGM project
  ratatui                                     8.1 MB  pub   A Rust crate for cooking up terminal user interfaces (TUIs) 
  zz-pause-inc-Parpoura                       6.3 MB  PRIV  Incubating: governance/traceability platform
  shopping-home                               5.8 MB  PRIV  Shopping Home founder-alpha source, protected behavior contr
  heliosApp                                   5.4 MB  PRIV  An internal tool or component for the Phenotype ecosystem.
  zz-archive-4sgm-archive                     4.6 MB  PRIV  Archive of KooshaPari/4sgm (deleted 2026-07-14). Restored 20
  host-ops                                    3.8 MB  PRIV  Host ops runbooks, guards, and the closure ledger (restored 

== canonical homes (2)
  PhenoRegistry                            3360.8 MB  PRIV  Organization registry: master index connecting specs, patter
  PhenoShared                               266.4 MB  pub   Determining merge target: Rust monorepo workspace

== named in the batch (5)
  zz-ref-HeliosCLI                          389.8 MB  pub   Multi-runtime AI CLI: unified interface for agent orchestrat
  zz-ref-HeliosLite                          96.0 MB  pub   AI pair programmer CLI for Claude, GPT, Gemini, Grok, Deepse
  chatta                                     68.4 MB  PRIV  chatta � Svelte-based chat application and UI components
  Personal                                   11.4 MB  PRIV  -
  zz-zz-agentcheck-zz-pause-Agentora          9.3 MB  PRIV  zz-merge -- split: 47 Rust crates into KooshaPari/pheno, Pyt

== leave alone (4)
  cmux                                     1974.4 MB  pub   Open source Ghostty-based macOS terminal with vertical tabs 
  Substrate                                  69.3 MB  PRIV  AI execution substrate: provider routing across HTTP, CLI, M
  argis-extensions                           24.0 MB  PRIV  Recovered local work - salvaged during the 2026-11-08 worktr
  Pine                                        1.0 MB  PRIV  Wine-equivalent for Phenotype: Windows and cross-platform ap

== recovery stores (25, excluded by rule)
  AgilePlus-rb-archive-20261106, Melosviz-rb-archive-20261106, PhenoFastMCP-rb-archive-20261106, PhenoProc-archive-20261106, PhenoVCS-rb-archive-20261106, Pine-rb-archive-20261106, Quillr-rb-archive-20261106, Sidekick-archive-20261106, Sidekick-rb-archive-20261108, Stashly-archive-20261106, Stashly-rb-archive-20261106, Stashly-rb-archive-20261106-exact, Tasken-archive-20261106, Tasken-archive-20261106-exact, Tasken-rb-archive-20261108, Tracera-rb-archive-20261106, exports-temp-archive-20261108, forgecode-rb-archive-20261106, phenotype-archives-20261108, phenotype-registry-rb-archive-20261106, work-archive-20261105, zz-Parpoura-rb-archive-20261106, zz-QuadSGM-rb-archive-20261106, zz-localbase-rb-archive-20261106, zz-rich-cli-kit-archive-20261106
```
