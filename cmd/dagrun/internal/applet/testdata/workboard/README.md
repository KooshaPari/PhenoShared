# workboard consumer fixture

Bytes captured from a live `dagrun serve` on 2026-11-24T09:08:21Z (dagrun 1.2.0), kept in-tree so the
reader's behaviour toward a read-only consumer is a tested property rather than a discussion.

This is a **consumer** fixture. Nothing here is written by dagrun, and nothing here is a schema: the
records are inputs, `expected.json` is the measured outcome for each of them, and `consumer_fixture_test.go`
in the parent directory replays every one against `ReadInstances`.

| Path | What it is |
|---|---|
| `live/127.0.0.1_52391.json` | a genuine advertisement, copied out of the registry of a running server |
| `mixed/` | four records a consumer must handle (dead origin, duplicated id, invalid id) and four it must report as errors (foreign contract, unknown field, `read_only: false`, truncated JSON), plus one non-JSON file |
| `manifest/manifest.json` | the real `/.well-known/applet.json`, 16 required fields |
| `manifest/discovery.json` | the real `/api/applet` document: host, mount, auth, authority, routes |
| `expected.json` | per-file input state, trap, and the measured outcome |

The `dir` inside `live/127.0.0.1_52391.json` is a path from the capture host and its origin is dead.
That is intentional: it is the state a killed server leaves behind, which is what a consumer meets
most often.

## What the fixture pins

1. **Rows and errors are separate channels.** A record that fails validation is returned in `errors[]`
   with its filename and never as a row, so a consumer reading only rows cannot see it at all.
2. **Missing, empty and all-unreadable are indistinguishable from the row count alone.** All three
   return zero rows; only the directory's existence and `errors[]` separate them. A read does not create
   the directory.
3. **No dedupe and no id-vs-origin check.** `duplicate_of_live.json` is a byte copy under another name and
   is listed a second time, and a record whose id is `not a valid id` is accepted because `Validate`
   checks that the id is non-empty, not that it names the origin it advertises.
4. **A non-JSON file is silently ignored** and does not appear even in `errors[]`, so globbing `*.json`
   is not the same as reading the registry.
5. **The manifest a consumer fetches validates under this package's own rules**, and every advertised
   route is `GET` and `read_only`.

Replay commands and the consumer contract these pin down live outside the repository:
`~/CodeProjects/temp/dagrun-adapter-fixture/README.md` and `~/CodeProjects/temp/dagrun-workboard-adapter.md`.

To regenerate the fixture, capture a live record and re-measure each case rather than editing
`expected.json` by hand: an expectation that was reasoned about is exactly what this fixture exists to
replace.
