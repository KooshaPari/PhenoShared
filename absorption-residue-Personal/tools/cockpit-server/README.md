# cockpit-server

The local HTTP server behind the cockpit, and the guard that keeps it alive.

| File | Installed as | Role |
|---|---|---|
| `cockpit-server.py` | `~/bin/cockpit-server.py` | Serves `~/.local/share/resume-all/dashboards` on `127.0.0.1:8791` |
| `cockpit-guard` | `~/bin/cockpit-guard` | Cron, every minute: restart the server if `/health` does not answer |

## Supervision: cron, not launchd

`com.example.cockpit-server` does not reliably start under launchd on this
host. Observed repeatedly on 2026-11-08: the job sits at `state = xpcproxy` with
a pid assigned and `last exit code = (never exited)`, and no listener is ever
created, while the identical command run from a shell binds in under a second.
The stall moves between attempts -- sometimes the python exec completes and then
never binds the port, sometimes `/bin/zsh` is left spinning with no python child
at all. `KeepAlive` makes it worse rather than better, because launchd waits on
a child that never exits and so never restarts it.

So a per-minute cron guard supervises it instead. It checks the actual HTTP
response, not the presence of a process, because a cockpit that serves nothing
while reporting "running" is worse than a cockpit that is visibly down. On this
host that is not a hypothetical: the server served nothing for 26 hours while
launchd reported it running, and the last log line was 26 hours old.

The launchd plists are disabled and renamed `*.disabled-20261108`. Re-enabling
them without solving the spawn stall gives you two processes fighting for port
8791.

## `/health` must not do real work

`/health` and `/api/health` answer directly, without touching the dashboards
directory. A health endpoint that does real work cannot distinguish a live
server from a wedged one, because both time out.

## `server_bind` skips reverse DNS

`Server.server_bind` calls `socketserver.TCPServer.server_bind` directly instead
of the stdlib `http.server` one, which calls `socket.getfqdn()`. That reverse
lookup can stall, and when it stalls the listening socket is never created, so
the process lives on while never accepting a connection.
