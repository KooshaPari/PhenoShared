# Recipe family: meaningful active props

## Hinged headphones or foldable device

Model hinge pivots explicitly; keep shell, hinge and pad/screen separate. Drive open/closed from a button with a visible state. Reveal explanatory content in HTML. Test interrupted/reversed movement and collision/intersection at both ends. Do not use mesh-center rotation as a fake hinge.

## Material specimen tray

One shared scene with several bounded specimens, a material selector and a light-angle control. Keep camera/color pipeline fixed when comparing. Distinguish actual shader response from display/UI glass. Avoid one GPU canvas and one copy of the environment per specimen.

## Interactive vector character

SVG or Rive state machine for hover/focus, loading and completed states. Tie state to real application state, but never let a decorative smile substitute for error text or successful completion evidence. An autonomous agent may author SVG directly; Rive authoring depends on available editor/runtime automation and must be probed.

## Spatial background that responds to pointer

Use a small parallax range and transform a single group. Keep content readable, disable under reduced motion and stop when hidden. Compare a plain background; remove the effect if it is only distraction.

## Physics object

Use physics only when grab/drop/collision is the actual interaction. Clamp impulses, bound the play space and provide reset. Separate controlled storyboard state from dynamic simulation; do not let two systems own the same transform. Deactivate when offscreen.
