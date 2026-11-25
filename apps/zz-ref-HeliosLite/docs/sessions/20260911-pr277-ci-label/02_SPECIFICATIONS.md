# Acceptance criteria

Preserve opened/synchronize/reopened and push behavior. Skip all five jobs for unrelated labeled/unlabeled events even when opt-in is present. Relevant addition allows existing opt-in matrix. Relevant removal allows Linux coverage/benchmark only. Preserve runner matrix, branches, tags, permissions and concurrency.

Risk: current label membership alone does not identify the changed label. Mitigate with shared event guard plus existing opt-in membership for matrix jobs.
