# Research

- ci.rs and generated ci.yml originally ran coverage/build and benchmarks unconditionally. Baseline subscribed to labeled, but not unlabeled.
- Optional PR release jobs checked only current label membership, so unrelated edits reran the matrix when opt-in was present.
- Main draft job already runs only on main pushes. No change needed.
- workflows/mod.rs supports CI=true read-only parity checks. Existing snapshots are parsed YAML comparisons, not insta library snapshots.
- GitHub event reference: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows. PR label changes use labeled/unlabeled activities and github.event.label.name identifies the changed label.
