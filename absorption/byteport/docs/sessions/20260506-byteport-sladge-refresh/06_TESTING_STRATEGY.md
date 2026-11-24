# Testing Strategy

## Focused Checks

- `git diff --check`: passed.
- README badge presence with `rg`: passed.
- `git lfs status`: passed with only intended README modification reported.

## Lightweight Repo-Native Checks

- `GOCACHE=/tmp/byteport-go-build-cache go test ./...` from
  `backend/byteport`: blocked by local disk exhaustion while writing Go build
  artifacts.
- Frontend install/build work is deferred because dependencies may be absent
  and the change is README/session-doc only.
