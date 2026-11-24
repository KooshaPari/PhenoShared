# Recipe: retain the idea without live 3D

A premium layout and a carefully lit source render can carry most of the identity. Use live 3D only where the extra viewpoint or input teaches something useful.

## Static + small DOM motion

Render the strongest product frame, reserve its dimensions and use semantic HTML for every claim and action. Add limited CSS perspective/layer movement to separate the surface from surrounding UI. Do not label a warped flat image as a true volumetric object.

## Bounded pre-rendered sequence

Render a short controlled camera/product path from the editable scene. Encode an appropriate video or a constrained image sequence. Supply a poster and reduced-motion end state. Preload only necessary frames/segments and measure decoded memory. Make seeking resilient; native video seeking is not inherently frame-perfect or smooth on every device.

## SVG/Rive active version

For a control, mascot or diagram, a 2D state machine can be more legible and substantially easier to test than a physical simulation. Preserve editable vector/state source and a semantic DOM equivalent.

## Gate

Do not ship a hundred megabytes of pre-rendered frames merely to avoid a small GLB. Conversely, do not force GPU rendering for an object nobody can meaningfully inspect. Measure both candidates. Keep artwork rights and authored renders separate from actual application-evidence screenshots.
