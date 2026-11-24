# DAG and work breakdown

```text
P0 resource parity ------> P1 auth/export ------> P1 provenance ------> P2 enrichment
                                      \                               \
                                       -> installed-app smoke ---------> A+ gate
P2 retrieval hardening -----------------------------------------------> A+ gate
```

- P0/P1: complete and verified.
- Provenance: complete in source; installed package smoke remains pending.
- P2 enrichment: implementation complete; authenticated account smoke pending.
- P2 retrieval: chunking/model-versioned embeddings/overlap reranking implemented; local reranker smoke remains a gate.
- A+: blocked by the two P2 lanes and authenticated installed-app evidence.
