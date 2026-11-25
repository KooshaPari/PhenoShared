# Task Runner: Justfile primary, Taskfile mirror

**Status:** adopted · **Applies to:** every repo with more than a trivial build/test loop.

## Convention

- A `Justfile` is the **primary** task entrypoint. Common recipes: `build`, `test`, `lint`, `fmt`, `dev`, `ci`.
- A `Taskfile.yml` runs **in parallel** as a mirror of the same recipes, for environments/agents that prefer `task`. Keep the two in sync — neither is allowed to drift into being the only source of a recipe.
- Any script longer than **20 lines** lives in `Tools/*.ps1` (this is a Windows-first org) and is *invoked* by the Justfile/Taskfile recipe, not inlined. Short one-liners may stay inline.

## Why

One memorable verb per task (`just test`) beats a README full of copy-paste incantations, and keeps CI and local runs identical. The Tools/ threshold stops recipes from silently becoming unreadable shell programs.

## Do / Don't

```text
# DO — recipe delegates to a checked-in script
test:
    pwsh Tools/Run-Tests.ps1

# DON'T — a 40-line shell pipeline crammed into the recipe body
```

A recipe that needs flow control, loops, or error handling is past 20 lines in spirit — move it to `Tools/`.
