# Apply to every current agent — ecosystem-first reuse and evolution

This strengthens the existing assignment; it does not restart it or grant new writes.

**Prefer modifying, adapting or narrowly wrapping suitable existing work over handrolling. Apply this equally to external dependencies AND our own packages, products, schemas, tests, prompts, documentation, build/release and operational tooling.**

Your assigned repository is a write boundary, not the boundary of reasoning. Continually develop/refactor with supported current consumers, committed near-term consumers and plausible future uses in view. Optimize the OVERALL polyrepo ecosystem, not just your local diff, percentage, repo size or release convenience.

Before a substantive implementation, search our actual capabilities and suitable external solutions. Prefer improving the authoritative capability rather than adding another copy. Do not preserve a weak owned implementation out of loyalty; do not wrap an entire external API without a real policy/stability need.

Current consumers need preserved contracts and actual verification. Committed consumers need explicit requirements and useful contract tests/spikes. Plausible consumers need economical extension seams and recorded assumptions, NOT a speculative universal framework. Unknown consumers are not zero consumers. Independent products must not become dependent on the entire platform.

Record preserved behavior, performance, recovery, security, data/API/versioning and operational constraints before changing shared code. Include consumer migration, dependency coupling, build/runtime cost, patch/upstream burden and coordination in the decision. A local improvement that offloads greater cost or regressions to other repos is not an ecosystem improvement.

For every material change, attach a proportional consumer-impact/reuse record to the existing task/PR/ADR: capability and owner; considered owned/external alternatives; current/planned/speculative consumers; preserved constraints; expected and measured effects distinguished; actual tests/unknowns; migration and rollback; decision/review references. Small internal changes may use a concise no-contract-impact attestation with supporting scope evidence. Do not create a second registry or demand a complete portfolio audit for a small repair.

Preserve exclusive worktrees and repository/path leases. Cross-repo opportunities become linked tasks with named source, target, consumer and integration owners. Do not edit another agent's repo without its authorized scope. Do not count a local PR as closure while the accepted parent still requires consumer adoption or duplicate retirement.

Reassess during real work when another consumer appears, workarounds repeat, upstream changes, or architecture/quality constraints shift. Keep beneficial increments bounded; do not endlessly rewrite working software or hide accepted behavior removal under 'cleanup'. Tests and current viable product delivery continue under existing gates.

Detailed policy: [ecosystem-first evolution](../architecture/ECOSYSTEM-FIRST-EVOLUTION.md). The impact schema checks structure only; it cannot approve changes, discover all consumers, or establish semantic parity.
