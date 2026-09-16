# WBS and DAG Rules

Use `X.X.X.X` hierarchy with explicit state and dependency.

- Level 1: Capabilities
- Level 2: Work packages
- Level 3: Tasks
- Level 4: Deliverables

Template fields:

- task_id
- title
- state: alpha|beta|canary|rc|release
- depends_on
- parent_task
- pr_name

Example:

- A (alpha): playback engine foundation
- B (beta): offline cache for playback (`depends_on: A`)
- C (rc): web player renderer (`depends_on: A`, stricter channel)

Rule: if B changes API used by C, B must be merged before C.
