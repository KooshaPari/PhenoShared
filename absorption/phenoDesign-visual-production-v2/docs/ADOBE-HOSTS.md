# Illustrator and Photoshop: use the installed applications, qualify the host

The user reports both applications on device. This package treats them as available candidates, not substitutes for its own unavailable native session. Local authoring can remain on-device; hosted Adobe APIs/connectors are a separate option with different permissions and data movement.

## Illustrator

Official Illustrator scripting supports native automation; do not assume Photoshop UXP APIs apply. `worker-recipes/adobe/illustrator/author.jsx.in` is a bounded native authoring template. Compile the included data job into the *owned workspace*:

```sh
python scripts/compile_illustrator.py examples/illustrator.job.json --workspace /owned/existing/output-folder --out /owned/job.jsx
```

Invoke the compiled JSX through the qualified installed application/native adapter. It creates its own RGB document, named layers, editable paths, .ai source and SVG/PNG derivatives, then closes only that document. It refuses existing named outputs. It is a geometry canary, not a finished illustration generator. Extend it with reviewed operations for real product art, text, gradients, masks and complex paths, retaining the actual editable master.

Required receiving-agent checks: artboard coordinate orientation, SVG external content safety, native .ai reopen, layer/path inventory, font behavior if added, native-size exports and actual browser placement. ExtendScript File operations do not constitute a sandbox; use an owned work directory and OS-level session restrictions.

## Photoshop

The included command-only UXP plugin prototype has two commands: authorize a dedicated workspace and process bounded local composition jobs. Workspace access is granted through UXP and retained as a persistent token. Jobs are flat local `.job.json` files; inputs are local raster files. The plugin places them as editable image layers, sets names/opacity, saves PSD and PNG, and writes an `EXPORTED_UNVERIFIED` receipt. It serializes jobs and auto-closes only the document it created.

Load the local plugin with the qualified UXP development/deployment path in a dedicated Photoshop session. Native packaging/signing requirements, the actual installed version and API behaviors must be tested. A command can be triggered by the existing native journey/automation adapter after the one-time permission grant; this pack does not supply a universal cross-OS native-input driver.

The canary expects matching-size input images staged by the worker. It does not implement arbitrary pixel editing, full layer/mask authoring, a long-lived daemon, network service or all Photoshop features. Extend it with reviewed DOM/batchPlay operations and independent verification; do not turn it into an unauthenticated execute-code socket.

`executeAsModal` is awaited, cancellable app-state mutation—not proof of invisible background execution. Keep one worker per qualified app session. Cancellation can occur while modal state is active; preserve failure receipts, source inputs and diagnostic frames. Workspace token revocation is an auth/host issue, not an excuse to use unrestricted filesystem access.

## Host canary and integration gate

Create → save native → export → close → cold launch/reopen → inspect structure → compare export → test consumer. Then intentionally fail a file permission, lock modal state and remove a source dependency. Verify that failures remain visible and operator documents/focus/audio are untouched. Only after this gate may the adapter be advertised as autonomous in its proven scope. Do not mark the entire Adobe suite qualified after one PSD export.

Official sources: A01–A06 in the catalog. No app binaries, third-party paid plugins or fonts are redistributed.
