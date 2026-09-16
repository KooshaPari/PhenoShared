# Tracera PR851 Second-Cloud Preservation Gap

**Recorded:** 2026-08-21
**Status:** First-cloud Git preservation verified; independent second-cloud restore remains unproven.

## Verified source identity

| Item | Evidence |
|------|----------|
| Preserved commit | `d99a2524802d7b5a41361a62e3874657c628ed76` |
| Local preservation ref | `refs/preserve/20260816/pr851-final-d99a2524802d7b5a41361a62e3874657c628ed76` |
| Hosted preservation evidence | `refs/tags/preserve/tracera/20260816/pr851-final-api-errors-d99a2524` resolves to the preserved commit |
| Rebuilt complete bundle | SHA-256 `33913d2b027191e5503bfbf06c68df3d05b8fd9c250c6a6903007255deb5ff6`; 362,563,546 bytes |
| Bundle verification | `git bundle verify` reports the preserved ref and a complete history |

## Attempted second-cloud transfer

The authenticated Wrangler R2 path targeted a new content-addressed key in the existing
`phenotype-preservation` bucket. Wrangler 4.120.1 rejected the transfer before any object write:

```text
Wrangler only supports uploading files up to 300 MiB in size.
bundle is 346 MiB in size.
```

No remote object was created, overwritten, or deleted. The local temporary bundle is only a
rebuildable staging artifact and is **not** second-cloud evidence.

## Required next gate

Use a multipart-capable R2 S3 client with a short-lived, least-privilege credential supplied at
execution time. The client must upload one new content-addressed object, record part/complete
metadata, download it onto an independent host, verify the SHA-256 above, and run
`git bundle verify`. Do not split the bundle into independently incomplete fragments, and do not
mark PR851 retired, archived, or fully preserved until this restore evidence exists.
