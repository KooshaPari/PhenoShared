# R2 Multipart Preservation and Restore Runbook

**Status:** Prepared, not executed. No credentials, artifact bytes, or remote object are stored
in this document.

## Purpose

Use the `phenotype-preservation` R2 bucket as the second-cloud copy for complete recovery
artifacts that exceed the reliable single-upload path. A Git ref or manifest alone is not a
second-cloud restore proof.

## Preconditions

1. An approved artifact manifest names the exact file, byte length, SHA-256, source commit/ref,
   and destination object key.
2. A short-lived, least-privilege R2 S3 credential is supplied at execution time only. Wrangler
   OAuth authentication is not an S3 credential and must not be copied into files, shell history,
   or a repository.
3. A multipart-capable client is available (`rclone`, an S3 SDK high-level uploader, or an
   approved equivalent). The installed Wrangler object command is single-upload only.
4. The destination key is new and content-addressed; retries resume the same multipart upload or
   create a separately named object. Existing evidence is never overwritten.

## Execution contract

| Step | Required proof | Failure behavior |
|------|----------------|------------------|
| Initiate | bucket/key, source SHA-256, planned size, and operator timestamp | Stop before bytes transfer if identity or source hash differs |
| Multipart upload | uniform parts >= 5 MiB except final part; upload ID and per-part ETags retained outside Git | Resume/retry only failed parts; do not replace a completed object |
| Complete | final object key, byte size, upload completion timestamp, and remote metadata | Abort only the incomplete multipart session if policy authorizes it; never delete a completed evidence object |
| Independent restore | download onto a different host or isolated filesystem; SHA-256 equals manifest | Mark preservation incomplete and retain all prior evidence if hash, size, or bundle verification fails |
| Read-only smoke | `git bundle verify` or the artifact-specific verifier succeeds in the restored location | No promotion, retirement, or cleanup decision follows a failed smoke |

## Acceptance record

Record only the following in a dated provenance packet: artifact SHA-256 and length, object key,
remote ETag/version metadata, uploader identity class (not credentials), restore-host class,
restore SHA-256, verifier command and exit status, and links to the Git preservation ref.

Cloudflare R2 supports S3-compatible multipart upload; use a multipart-capable SDK/tool for
large artifacts and preserve the completed object independently of its multipart ETag.
