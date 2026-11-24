---
name: fd3d-asset-provenance
description: "Track editable sources, asset rights, dependencies and output hashes for frontend media; use before importing resources or distributing generated 3D assets."
license: MIT
metadata:
  version: "1.0"
  origin: "original-kit-skill"
---

# Source custody is part of delivery

Create a manifest for each authored asset, not a replacement global registry. Integrate it with the project's existing asset owner and evidence system.

Record creator, original URL when applicable, retrieved revision/date, license text/location, modifications, input rights, generator/recipe, exact dependent textures/HDRIs, units/axes, source/export paths and byte hashes. Distinguish software licenses from model-weight and output/input rights. Public download access is not a redistribution grant.

Keep editable source and optimized derivative linked. Do not include proprietary fonts, branded product scans or paid course material in a generic shareable ZIP. Poly Haven's asset license is not automatically the license of every website/code resource or every unrelated model on the internet.

Maintain separate authored presentation assets and real validation captures. Never use a generated screen mockup as proof that an implementation works. A hash proves byte identity relative to a recorded hash; it does not authenticate the producer or prove permission.

## Gate
Missing required license/source/dependency is a blocked publication, not a footnote hidden after export. This kit contains one licensed upstream skill snapshot, original instructions/code/geometry, and external links. It does not claim to redistribute every linked resource.

Sources: R01, R19, R20. See `THIRD-PARTY-NOTICES.md`, `assets/asset-manifest.json` and `resources/catalog.json`.

## Kit location
Kit root: `{{KIT_ROOT}}`. The sync script expands this token. In the canonical ZIP, resolve the root two directories above this skill folder. Paths mentioned above are relative to that root. Read only the referenced files needed for the task.
