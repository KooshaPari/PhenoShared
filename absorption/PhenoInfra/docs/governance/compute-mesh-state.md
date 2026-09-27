# Compute Mesh State

Live status of the Phenotype compute mesh. The OCI section below is auto-managed
by `oci-post-acquire` on lottery success. Other providers are hand-edited.

| Provider | Status | Notes |
|----------|--------|-------|
| Hetzner CAX11 | ✅ | primary control plane |
| Fly.io | ✅ | edge workers |
| Cloudflare Workers | ✅ | router |
| Vercel | ✅ | UI hosting |
| Supabase | ✅ | managed PG |
| OCI Always-Free | ⏳ | pending lottery acquisition |

<!-- The `oci-post-acquire` orchestrator will append/replace an
"## OCI Status: ✅ ACQUIRED" block below this line on success. Do not
hand-edit between the AUTO-INSERTED markers; the next run will overwrite. -->
