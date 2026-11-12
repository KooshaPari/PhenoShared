# Deploy / Terminate Authorization and Validation Fix

**Fixes:** the route-8 finding in [FLOW.md](FLOW.md) — `POST /deploy` accepted a body it
should have rejected and proxied it to the sandbox service.
**Handler:** `backend/byteport/routes/deployment.go`
**Scope:** canonical backend `backend/byteport` only. The unused `/api/v1` module in
`backend/` is untouched.

## What was wrong

`DeployProject` bound the request straight into `models.Project`. Every field on that
model is `json:"...,omitempty"` with no `binding:"required"`, so _any_ JSON body bound
successfully, and the handler then read its identity fields from the body:

| Line (pre-fix) | Expression | Problem |
|---|---|---|
| `deployment.go:50` | `c.ShouldBindJSON(&newProject)` | no required fields, so `{}` was accepted |
| `deployment.go:126` | `Owner: newProject.User.UUID` | owner taken from the request body |
| `deployment.go:135` | `ID: newProject.UUID` | project key taken from the request body |
| `deployment.go:123` | `newProject.SetDeploy(...)` | written to `newProject`, then discarded |
| `deployment.go:170` | `project.User = user` then `sandboxID := project.UUID` | stop/delete keyed on a body value with no ownership check |

Three consequences:

1. **No request validation.** `{}`, `{"description":"x"}`, or even a JSON array were
   accepted and proxied to `NVMS_URL` (`http://localhost:8443/v1/deploy`), which is where
   the observed 500 came from.
2. **Client-controlled ownership.** The web client never sends `user`, so real
   deployments were stored with `owner = ""` — invisible to `GET /projects`, which
   filters `owner = <session user>`. A caller that _did_ send `user.uuid` could attribute
   a deployment to any account and choose its identifiers.
3. **Cross-tenant terminate.** `TerminateInstance` forwarded the body's `uuid` to
   NanoVMS `/v1/stop` and to a database delete without checking that the caller owned it,
   so any authenticated user could stop and delete any project by identifier.

A fourth defect rode along: `SetDeploy` was applied to `newProject` while the row
actually written was a freshly built `finalProject` that never received the deployment
map, so the sandbox association was silently dropped.

## What changed

- `deployRequest` / `terminateRequest` DTOs replace the entity as the bind target.
  `deployRequest.Name` and `terminateRequest.UUID` carry `binding:"required"`, so an
  incomplete body is answered with 400 **before** any database write or outbound call.
- Ownership, `UUID` and `ID` are derived from the session. The body has no way to
  influence them.
- `currentUser` (`routes/auth.go`) resolves the authenticated user and writes the 401/500
  itself. `DeployProject`, `TerminateInstance`, `GetProjects` and `GetInstances` all use
  it, replacing three copies of the same context-lookup.
- `TerminateInstance` loads the project with `uuid = ? AND owner = ?`. A project owned by
  somebody else is reported as `404 Project not found` so its existence is not leaked,
  and neither the stop call nor the delete happens.
- The sandbox mapping is persisted on the row that is written.
- Debug `fmt.Println` calls that dumped whole project structs were replaced with
  `log.Printf` lines carrying the project id only.

## Evidence

### Falsification — the new tests fail on the pre-fix handler

`backend/byteport/routes/deployment_authorization_test.go` was run against
`HEAD:backend/byteport/routes/deployment.go` with the rest of the change in place:

```
=== RUN   TestDeployProjectRejectsInvalidBody/{}
BeforeSave
Generating UUID
Deploying project:  {{0 …} 28024ab7-6a7e-4120-8001-289813d3b7a9   {  …}}
Deployed sandbox:  {sandbox-1 sandbox running  }
BeforeSave
Adding project to db:  {{0 …} 28024ab7-… 28024ab7-…  …}
--- FAIL: TestDeployProjectRejectsInvalidBody/{}
panic: runtime error: invalid memory address or nil pointer dereference
  gorm.io/gorm.(*DB).Create
  byteport/routes.addNewProject
  byteport/routes.DeployProject
```

`{}` was accepted, a UUID was generated, **NanoVMS was called and answered**, and the
handler proceeded to the database. That is the defect the tests lock down.

### Package tests, post-fix

```
$ go vet ./...            # no output
$ go build ./...          # no output
$ go test ./...
ok  byteport                    ok  byteport/internal/auth    ok  byteport/internal/crypto
ok  byteport/internal/routes    ok  byteport/lib             ok  byteport/models
ok  byteport/routes
```

### Live probes — real binary, real HTTP, real sqlite

Server built from `backend/byteport` and run on scratch port 8099 against a scratch
sqlite database, with a recording NanoVMS stand-in on :9443 so every verdict includes
whether the sandbox service was reached.

| # | Probe | Status | Sandbox-service calls |
|---|---|---|---|
| P1 | `POST /deploy` body `{}` | **400** `Field validation for 'Name' failed on the 'required' tag` | 0 before → 0 after |
| P2 | `POST /deploy` blank `name` | **400** same | 0 before → 0 after |
| P3 | `POST /deploy` no session cookie | **401** `Authorization header missing` | 0 before → 0 after |
| P4 | `POST /deploy` with `owner`/`uuid`/`id`/`user` all set to `victim-*` | **200** | deploy call for project `803fbdd5-…` |
| P5 | `GET /projects` as the caller | **200** | — |
| P6 | `POST /deploy` as a second user | **200** | deploy call for project `0aab9599-…` |
| P7 | user A terminates user B's project | **404** `Project not found` | stop calls 0 → 0 |
| P8 | `POST /terminate` body `{}` | **400** `Field validation for 'UUID' failed on the 'required' tag` | — |
| P9 | user B terminates its own project | **200** | stop call for `0aab9599-…` |

P4/P5 disprove the spoofing path: the body asked for owner `victim-uuid` and id
`victim-id`, and the stored row is

```json
{"uuid":"803fbdd5-030b-4bce-bfa1-3720a65b2e53",
 "id":"803fbdd5-030b-4bce-bfa1-3720a65b2e53",
 "owner":"9b811c3e-f2c9-4f4f-9c12-fd2cb04c9666",
 "DeploymentsJSON":"{\"default\":{\"UUID\":\"sandbox-live-1\",\"Owner\":\"9b811c3e-…\",\"ResUUID\":\"803fbdd5-…\"}}"}
```

`owner` and both identifiers are server values, and the deployment map is now present.

The stub log for the whole run contains exactly three calls — two `/v1/deploy` bodies
(both carrying a server-generated `byteport-project-id`) and one `/v1/stop` for the
caller's own project:

```
{"method":"POST","path":"/v1/deploy","body":"{\"name\":\"alice-app\",…\"labels\":{\"byteport-project-id\":\"803fbdd5-…\"}}"}
{"method":"POST","path":"/v1/deploy","body":"{\"name\":\"bob-app\",…\"labels\":{\"byteport-project-id\":\"0aab9599-…\"}}"}
{"method":"POST","path":"/v1/stop?id=0aab9599-…","body":""}
```

Nothing that was rejected reached the sandbox service.

## Known issues left in place

- **Sandbox id semantics.** `TerminateInstance` still sends the _project_ UUID to
  NanoVMS `/v1/stop`, while the deploy path records the NanoVMS sandbox id under
  `Instance.UUID` / `ResUUID`. If the two ever differ, stop targets the wrong id. The web
  client sends `project.uuid`, so changing this is a contract change and was left alone.
- **Legacy rows.** Projects written before this change have `owner = ""` and are
  therefore invisible to `GET /projects` and untouchable by `POST /terminate`. They need
  a data migration, not a code change.
- **`GET /projects` response shape.** Each project still carries a zero-valued `user`
  object, because `json:"user,omitempty"` has no effect on a struct. Pre-existing.

## Status

- Visual state: UNKNOWN (no screenshots taken; none permitted).
- Scratch server and stub stopped after evidence collection; artifacts under
  `$JCODE_SCRATCH_DIR/byteport-live-20260919-021435/`.

tx-agent: jcode
tx-task: BytePort deploy validation gap (FLOW.md route 8)
tx-validated: gofmt,go-vet,go-build,go-test,live-curl-e2e
