# Testing Strategy

## Validation Plan

For this docs change, validation is documentary rather than code-level:

- verify the new governance doc renders as Markdown
- verify the shared parity doc links to the new standard
- verify the repo governance doc points readers to the same source of truth
- verify the session docs exist and are complete

## Checks

- search for the new standard name in `docs/governance/`
- inspect the hwLedger reference pattern to ensure the examples match
- keep the docs concise enough that repo owners can actually adopt them

## Future Testing

When repos start adopting the standard, validate that their docs pages contain:

- a `ShotGallery`
- at least one `RecordingEmbed`
- traceability metadata
- a visible link to the source work item
