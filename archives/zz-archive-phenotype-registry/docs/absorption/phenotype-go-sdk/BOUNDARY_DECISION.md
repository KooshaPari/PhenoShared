# phenotype-go-sdk boundary decision

Date: 2026-06-20
Decision: `PRESERVE_ACTIVE_NARROWED`

`phenotype-go-sdk` remains active as the Go SDK/package aggregation target. It absorbed PhenoKits Go libs through `phenotype-go-sdk#21` and retains Go package surfaces such as `devhex`, `pheno-core-cgo`, `phenotype-go-auth`, `phenotype-go-cli`, `phenotype-go-config`, `phenotype-go-kit`, `phenotype-go-middleware`, and `phenotype-id`.

This repo is broad by design, but its boundary is Go SDK packaging. Keep active; do not delete.
