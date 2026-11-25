# Reference interchange schemas

Dialect: JSON Schema 2020-12. These schemas are authored for the proposed atlas interchange; they are not claims of current native AgilePlus, SROC/CDP or deployed Tracera conformance. Additional properties are rejected so accidental schema drift is visible. Future extensibility requires versioned accepted changes or adapters, not silent field loss.

Schema validity is necessary but insufficient. A state string cannot authenticate an approval; an evidence ID cannot prove a test ran. The reference checker additionally tests a subset of measurement consistency. Production implementations need actual native adapter qualification, access control, source/receipt authenticity, payload verification, timing/freshness and domain oracles.

Examples are deliberately synthetic. Their fields and cross-links illustrate structure and do not become portfolio evidence. IDs in a standalone example may refer to separately described illustrative objects; global object-resolution is an actual model-ingestion obligation, not claimed for a single-file teaching fixture.

## Consumer-impact attachment

`ecosystem-impact.schema.json` supplies a strict planning shape for existing task/PR/ADR attachments. It separates supported current, committed planned, plausible future and unknown consumers; reuse options; constraints; effects; and coordination. `lifecycle_approval` must remain false. An evidence reference is not an authenticated receipt and nonempty fields can still contain wrong claims. The schema is not a production authorization or consumer-discovery system.
