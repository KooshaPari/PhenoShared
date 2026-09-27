# Local Blender execution and iterative asset creation

## Reliable baseline

The baseline is a normal Blender executable receiving a reviewed Python script in a fresh background process. The agent needs a shell/file tool and the ability to inspect resulting PNGs; it does not need to drive the operator's mouse. The included `scripts/run_blender.py` constructs the process arguments, uses a private temporary configuration/home, limits threads and waits with a timeout. It defaults to a printed dry-run. This is hygiene, **not OS containment**: Python can still access files/network allowed to that OS user.

A suitable production worker has a dedicated low-privilege user or VM, an owned workspace, no production/personal credentials, restricted outbound network and a measured resource lease. Do not expose the Blender socket through a tunnel or public address simply for convenience. A VM is optional architecture, not a requirement of the file format; choose the lightest isolation that actually meets the threat model.

## Reproducible job

Inputs: asset brief + generator + mesh/parameter JSON + permitted dependencies. Outputs: native project, GLB, three consistent renders and receipt. A job directory is created fresh; the runner refuses existing output/log paths. Preview settings default to bounded CPU Cycles rendering. Raise quality only after the low-cost pass is useful.

The bundled Blender script rebuilds the provided concept mesh, adds semantic custom properties and native procedural micro-bump, sets a studio, saves `.blend`, exports the model selection and optionally renders three views. It is syntactically checked but was not executed here because Blender is absent. Its exporter flags and native shading need a real local run before acceptance. Procedural micro-bump is explicitly **not baked into the GLB**.

## Autonomous iteration protocol

Pass A: clay silhouette in profile/three-quarter/rear; measure proportions and inspect openings. Pass B: construction, intersections, pivots and named parts. Pass C: material family under fixed neutral lighting. Pass D: browser export parity. Pass E: story poses and smallest-viewport composition. Each pass has one short defect list, a parameter/source diff, identical comparison views and an explicit keep/reject decision.

A bad shape cannot be fixed by increasing samples, adding an HDRI or making a camera orbit faster. Recognizable geometry and readable materials precede spectacle. A reference photograph is evidence for visible form, not a license or a full dimensional specification.

## Optional MCPs: do not confuse them

**Blender Lab (R28):** official Blender Lab experimental direction. The primary page was indexed but could not be fully fetched here, so this kit does not invent an installation command, transport endpoint or tested version compatibility.

**ahujasid/blender-mcp (R07):** community add-on plus Python MCP server. The reviewed README discloses arbitrary Python execution and telemetry enabled by default. Disable telemetry with `DISABLE_TELEMETRY=true` and disable add-on consent as documented in the exact version. The reviewed project also has a safe-mode option, but script validation is not equivalent to process/OS isolation. Scope credentials and permitted network at the worker boundary.

Features that fetch Poly Haven/Sketchfab assets or call Hyper3D/Hunyuan services need separate rights/network/privacy review. "Runs in Blender" does not mean "all computation is on this device". Pin and inspect actual packages instead of leaving an unversioned `uvx` command to change underneath the agent.

## Geometry Nodes / scripts

Use node groups for meaningful parameterized variation; use Python for repeatable construction/export and batch rendering. Save both source form and evaluated delivery mesh. Probe the installed API because group interfaces and render settings evolve. The kit includes a Geometry Nodes workflow skill, not a falsely claimed tested node graph.

Sources: R05/R06/R07/R28/R36.
