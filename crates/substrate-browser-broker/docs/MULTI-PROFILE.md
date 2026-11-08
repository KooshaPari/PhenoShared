# Multi-profile isolation

How the broker gives N independent cookie jars today, and what that costs.

## The isolation model

A **profile** is a named, per-principal browser *user-data directory*. One
profile equals one browser data directory, which equals one cookie jar, one local
storage area, and one set of authenticated sessions.

```
<root>/profiles/<principal>/<profile>/manifest.json
<root>/profiles/<principal>/<profile>/gen-<n>/      <- the data directory
```

The `gen-<n>` directory is the value handed to the browser as its data
directory (`--user-data-dir=<dir>` for Chrome/Chromium/Edge/Brave via
`substrate-browser-cdp`; `-profile <dir>` for a Firefox adapter). Because the
directory is per-profile, two profiles never share a cookie jar: the browser
cannot read a jar that is not under the directory it was started with.

A profile is made of **generations**: immutable snapshots with exactly one
`active` generation. Rotating a profile creates a new generation, and forking a
sealed generation copies the tree instead of merging two browser databases. See
`substrate_browser::ProfileStore`.

Two profiles are *different jar identities*. Two generations of the same profile
are *successive states of one identity*, and only one of them is live at a time.

## Concurrency

| Situation | Behaviour |
| --- | --- |
| Two different profiles, same principal | Both lease and run **concurrently**, one browser process each |
| Same profile, two sessions | Second lease is **refused**; exclusivity is per `principal/profile` |
| Same profile, two processes | Refused through the shared on-disk lease store, not just in-process state |
| Same profile, expired holder | Reaped, then the profile is free again |

Exclusivity is the point: a browser profile is one storage jar, so two holders on
the same profile would share cookies no matter which window they drove. A window
is a view, not an isolation boundary.

Each lease carries a monotonic **fencing token per profile**. Fences are counted
per profile, so `alice/work` and `alice/personal` each start at 1 and advance
independently. A token from a superseded lease is rejected even if the holder
still has a stale copy of the lease record.

## Picking a profile

A caller names the profile in its scope; the broker resolves the rest.

```rust
use std::time::Duration;
use substrate_browser_broker::{Broker, Scope};

let broker = Broker::new("/var/lib/agent-browser")?;

// Agent A works as alice at work.
let work = Scope::new("alice", "work", "session-a")?;
let a = broker.acquire(&work, "agent-a", Duration::from_secs(900)).await?;

// Agent B works as the same person, personally, at the same time.
let personal = Scope::new("alice", "personal", "session-b")?;
let b = broker.acquire(&personal, "agent-b", Duration::from_secs(900)).await?;

// Released independently; each seals only its own generation.
broker.release(a).await?;
broker.release(b).await?;
```

`acquire` ensures the profile's generation, grants the exclusive lease, launches
a browser whose data directory is that generation, and publishes the live
session under the lease id. Nothing about the caller's identity decides the jar;
the profile name does.

Pick profile names by *login identity or purpose* (`work`, `personal`,
`tenant-acme`, `shopping-test`), never by task name: a new name is a new empty
jar, and an authenticated session has to be established from scratch in it.

## Operational cost

Every profile is a real browser:

- **One browser process per profile**, not per tab or per agent session.
- **RAM per profile** is a full browser baseline (roughly hundreds of MB for a
  headless Chromium, more when a page is loaded), times N profiles.
- **Startup latency per profile**: the browser must boot before the first action.
- **Disk per profile**: one data directory per generation. Forking a profile
  copies its tree.
- **No sharing wins**: cookies, caches and logins are not shared between
  profiles. That is the feature, and it is also why N profiles cost N times the
  login setup.

A practical ceiling is therefore set by RAM, not by the broker: the state layer
will happily lease twenty profiles, but twenty browsers is twenty processes.
Reuse one profile for sequential work and add a profile only when you need a
*genuinely different* jar.

## When you actually need containers instead

Profiles give isolation *between* browser processes. They do not give you many
independent jars *inside one browser process*.

If you need many isolated contexts in a single browser with no extra process per
context, that is Firefox **containers** (`userContextId` on tabs). That path
requires patching a third-party XPI to expose container ids to the automation
surface, so it is **out of scope for this crate** and tracked separately as the
KCode fork-patch item. Reach for it only when the process cost above is
the actual blocker, and note that it changes the isolation boundary from
"separate process" to "separate container inside one process", which is a weaker
guarantee.

Decision rule:

| Need | Use |
| --- | --- |
| Separate logins, separate jars, strong boundary | One profile per identity (shipped today) |
| Many lightweight contexts, low RAM, weaker boundary | Containers (tracked separately, not shipped here) |
| A snapshot you can roll back or fork | Generations inside a profile |

## Verified vs not verified

**Verified** by `crates/substrate-browser-broker/tests/multi_profile_isolation.rs`:

- two different profiles of one principal hold leases **simultaneously**, and
  revoking one does not disturb the other;
- the same profile **cannot** be leased twice, from a second session or from a
  second broker over the same root, while a sibling profile still can;
- each profile resolves to its **own generation directory** under
  `profiles/<principal>/<profile>/gen-<n>/`, with its own `manifest.json`, and a
  marker written into one profile's directory is not visible from the other;
- **fencing tokens are per profile**: both profiles start at fence 1 and
  advance independently.

That is **filesystem-level profile isolation**: the directories are separate and
the authority is separate.

**Not verified here** (out of scope for this test, needs a real browser):

- that a running browser actually refuses to read the other profile's cookie
  database;
- that two live browser processes hold genuinely disjoint in-memory cookie jars
  and network state across navigations, redirects and service workers;
- anything about Firefox containers, which this crate does not implement.

Claim profile isolation as "separate user-data directories enforced by the
broker, therefore separate jars by browser contract", and do not claim more than
that without a live-browser test.
