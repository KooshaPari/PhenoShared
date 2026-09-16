# skills/global (broken symlink in source)

In the original local source tree, this was a symlink:

```
skills/global -> /Users/kooshapari/CodeProjects/Phenotype/skills
```

The symlink target was a local-machine-only path pointing to the developer's
Phenotype skills directory. On the GitHub repo, only the symlink would be
present, and it would dangle. This file replaces the symlink to preserve
the metadata.
