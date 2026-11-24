# Explanatory atlas extraction

## Acquisition stages

Start with Git identity, accepted scope, supported build roots and existing evidence. Enumerate the full relevant artifact set with language-native manifests and Git/file inventories. Include native shells, tests, scripts, docs, raw prompt collections, asset sources, generated artifacts and package/deployment inputs. Explicitly list exclusions, inaccessible submodules/LFS objects, ignored build outputs and authorized untracked overlays.

Use deterministic extraction for facts: compiler indexes/SCIP/LSP where available, Tree-sitter syntax, package manifests, schema parsers, native coverage reports and actual runtime traces. Regex can locate candidates but cannot establish complete control/data flow. Do not build a bespoke universal parser simply because an LLM can write one quickly.

## Meaningful granularity

A semantic unit may be a public function, state machine, database migration, render pass, security policy, configuration key, UI state, asset family or entire generated module. Choose units that can own a reason, consumer and verification. Attach source spans to them; the mapping can overlap where a line serves several obligations. Boilerplate inherits the producer/contract rationale and does not need a new handcrafted FR for every accessor.

Every unit receives purpose source, constraints to preserve, current implementation facts, consumers, tests/evidence, uncertainty and disposition candidates. Separate historical rationale from reconstruction and newly accepted decisions. Never invent a past design intent because the current implementation looks clever.

## Reachability and usage

Trace public commands/UI/routes into real build targets, runtime adapters and state. Inspect feature flags, optional modules, dynamic registration, FFI, plugins, external consumer usage, command discovery and packaging inclusion. Static zero-reference results are only evidence of an extraction boundary until these alternatives are considered. Test-only, fixture-only, disabled, inaccessible and supported-but-unexercised states differ.

## Duplicate classification

Exact blob identity proves exact bytes for that blob only. AST/normalized similarity proposes duplication. Public contract and consumer tests establish semantic equivalence over a declared scope. Distinguish vendor source, intended platform variants, compatibility paths, generated repetition, historical snapshots and accidental clones. Preserve source lineage, licenses, consumer pins and current behavior before removal.

## Query acceptance

A new maintainer should answer: What does this capability do? Where does it start? Which artifact ships it? What state does it own? Which constraints prevent a simpler implementation? What breaks if it changes? What evidence is stale? Which assumptions are unresolved? Test these queries against adjudicated examples and score correctness, unsupported claims, time and context burden—not only index size or token reduction.
