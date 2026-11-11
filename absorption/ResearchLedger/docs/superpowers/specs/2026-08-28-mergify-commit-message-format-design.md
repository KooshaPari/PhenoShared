# Mergify Commit Message Format Migration

## Goal

Remove the deprecated `commit_message_template` setting so Mergify can keep
evaluating the repository configuration after its 2026-09-30 deadline, while
preserving the intended squash-merge subject and co-author provenance.

## Current state

Mergify created pull request #57 solely to report two deprecated templates in
`.mergify.yml`. The pull request has no source-tree delta and automatically
reopens while those templates remain on `main`; it must not be merged.

Both affected rules currently render:

```text
<pull-request title> (#<pull-request number>)

Co-authored-by: <pull-request author>
```

The final line omits the e-mail address required by Git's standard trailer
format, so it cannot be represented exactly by Mergify's declarative API.

## Decision

For both affected `actions.merge` blocks, replace the Jinja template with:

```yaml
commit_message_format:
  title: pr-title
  body: empty
  trailers:
    - co-authored-by
```

`title: pr-title` preserves Mergify's documented `<title> (#<number>)` subject
shape. `body: empty` permits trailers. `co-authored-by` emits canonical,
deduplicated `Name <email>` trailers from actual pull-request commit authors,
which is stronger provenance than the prior generic author-only trailer.

## Alternatives considered

1. Omit the format entirely. This delegates all formatting to the GitHub
   repository setting, but changes the established subject format.
2. Use `title: pr-title`, `body: empty` without trailers. This removes invalid
   provenance but loses the existing co-author intent.
3. Recommended: preserve the subject and represent provenance canonically with
   Mergify's supported `co-authored-by` trailer.

## Validation and rollback

Validate YAML syntax locally, validate Mergify's configuration check on the
pull request, and require the normal protected-branch checks and review before
merge. Confirm #57 closes after the default branch no longer contains the
deprecated key. If Mergify rejects the declarative format, revert only this
focused commit; no application code, data, credentials, or user settings are
affected.
