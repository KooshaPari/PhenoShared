# Scheduling, WBS and estimates

The package has a dependency DAG and bounded proposed work packages, not a fabricated calendar. Estimates are intentionally unset until actual source scope, environments and acceptance are bound. An estimation helper calculates PERT only when all required three-point estimates exist; otherwise it reports the exact missing estimates and declines to print a critical-path duration.

Use effort hours and calendar capacity separately. PERT expected effort is (optimistic + 4 × most_likely + pessimistic) / 6 under the declared heuristic model. It is not a statistical delivery guarantee. Dependency longest path and slack assume the stated precedence model; resource-constrained scheduling additionally needs owner/CPU/GPU/CI/native-session/review capacities and release windows. Do not claim the first calculation solves the second.

Hard prerequisite means required artifact, contract or acceptance data. Priority means value/order preference. Exclusion means shared resource/write conflict. WIP admission means a deliberate limit on unfinished slices. These must not be represented as an arbitrary single serial chain across unrelated products.

Start small: bind subject and actual current state; qualify one useful path; map only the scope needed to safely improve it while continuing broader mechanical inventory. Discovery spikes must end with a decision/evidence boundary, not endlessly expanded plans. An inherited defect can be a separate repair package but remains part of the parent's accepted outcome.

Tasks emitted here carry path targets as logical scopes to resolve, never pretend the generator inspected all current file paths. Before claim, materialize the actual write lease, tests, environment and permission. Do not create unqualified tasks to hit a count.
