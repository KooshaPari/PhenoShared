# Cockpit frontend

Astro builds the shared shell and Jobs/Parent pages. The combined Dispensary app is one React island; its charts use inline SVG and its item tables use reusable React components. Tailwind and shared CSS variables provide the design system. No remote commit or deployment is performed by these scripts.

## Install and validate

Use Node >=22.12. From the repository root:


cd web
npm install
npm test
npm run build
npm run dev

Code

Commit the generated package-lock.json once installed. With a committed lockfile, use npm ci for reproducible installs.

The build must run from web/ (npm --prefix web run build also sets the package working directory). The Parent reader resolves the owner-maintained ../parent/index.html from that directory.

The build emits /, /parent/, /dispensary/, /dispensary/learned/ and the exact /dispensary/learned.html compatibility file. Explicit /index.html, /parent/index.html and /dispensary/index.html files remain in dist. No root legacy HTML source is deleted or rewritten.

Both learned URLs forward to /dispensary/#insights, with a shared-layout fallback link when JavaScript is disabled. Old #base, #deals, #buy and #half fragment links are mapped to the corresponding sections. The hash helper waits for asynchronously rendered React content before scrolling. There are no separate deals or half-value HTML sources in main; no guessed path redirects are introduced.

## Data sources and behavior

- Jobs fetches the exact ./status.json URL with cache: no-store. Existing JSON field names and SMS draft bodies are retained. Approve and Request changes open drafts; they do not send anything. Blocked and unfamiliar statuses now remain visible rather than being omitted from the grouped list.
- Parent reads the existing static D literal from ../parent/index.html at build time. A literal-only TypeScript AST decoder does not execute the legacy script. Missing collections display unavailable; empty arrays display empty. Edits to that existing source require a new frontend build. This is a recorded snapshot, not a live platform monitor.
- Dispensary mounts DispensaryApp with client:load. Fetches, adapters, original JSON and the collector remain unchanged. Live data still comes through the existing DISP Pages Function. The React island is not copied into the compatibility wrapper.
- Root status.json and every allowlisted dispensary JSON asset are copied byte-for-byte. After Astro builds, a guard verifies output data bytes against staged originals and checks all migrated HTML routes exist. The learned.html alias is copied from the compiled shared-layout wrapper without overwriting existing assets.

No data file is reformatted, normalized on disk or moved. No collector, jobs-collector or worker source/config is changed. No new Pages Function or backend endpoint is introduced.

## Existing Cloudflare Pages settings

- Git repository: KooshaPari/job-cockpit
- Root directory: web
- Build command: npm run build
- Output directory: dist
- Node version: 22.12.0 or newer supported Node 22 patch
- Retain the existing DISP KV binding for production and preview.

Keep existing Access protections, custom domain and collector deployment settings. The existing root functions/dispensary/data/[[path]].js is copied unchanged into ignored, generated web/functions/ outside dist. The staging script fails if the Function allowlist changes. Do not point a collector Worker build at the frontend command.

Build watch paths must include web/**, index.html, status.json, parent/**, dispensary/** and functions/**. Legacy data and Parent snapshot updates must trigger frontend builds.

Astro dev/preview serve static fallback data; they do not execute Pages Functions or read live KV. Restart dev after changing static source data. Verify live KV in the existing Pages preview environment before production rollout.

## Public asset boundary

Staging is an explicit allowlist, never a recursive repository copy. It rejects symlinks, unexpected snapshot names and collisions with generated routes. Matching Astro pages stop legacy HTML copies; the existing staging script is unchanged in this batch.

Allowed data: root status.json; dispensary manifest, manual, registry, observations, status, cadence and deal_patterns JSON; dated snapshots. Optional learned JSON can be supplied by live KV. Required root status and manifest must exist; malformed JSON fails the build without rewriting it.

web/public/ contains intentionally public frontend assets only. Generated .staged/, functions/, .astro/ and dist/ remain ignored. Do not commit generated outputs.

## Exit checks

npm test covers missing data, exact URL/SMS behavior, unsafe references, literal-only Parent decoding, preserved source bytes, migrated-route staging, alias collisions and post-build byte validation. npm run build checks TypeScript and builds the actual React island plus all routes.

In Pages preview, check Jobs filters/receipts/SMS drafts, Parent filtering and snapshot time, the Dispensary island, both learned URLs, delayed #insights scrolling, light/dark themes, keyboard focus and a narrow mobile viewport. Confirm /dispensary/data/status.json uses the existing DISP binding when available. Preview and production collector builds remain independent of this frontend batch.
