# QC2-001 Session Overview

- Goal: add automated semver release management and crates.io publishing with release-plz.
- Success criteria: release workflow exists, publish scope is constrained to publishable crates, contributor docs describe the new flow.
- Key decision: use release-plz release PRs from main, then publish only after a merged release-plz PR closes into main.
