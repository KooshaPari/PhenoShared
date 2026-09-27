# Recipe: a live glass-and-metal dial

**Purpose:** a volume/parameter/material control whose physical object reinforces its value. Keep a normal range input as the state owner. It remains usable if 3D fails.

**Editable asset:** beveled/lathed metal body, separate annular grip, glass lens with actual thickness, inner indicator and a base. Set the pivot on the dial axis. Use Geometry Nodes for bounded knurl repetition and preserve its parameter interface; bake/realize only in the delivery derivative.

**Material variants:** clear lens, smoked lens and frosted lens share geometry but differ in transmittance/roughness intent. A satin body contrasts with the lens. Use an environment that creates readable highlights; fully uniform surroundings make glass almost invisible. Do not approximate physical frosted volume with an unexplained CSS blur and call it the same effect.

**Interaction:** range value 0..1 drives an absolute -120°..120° dial angle. Pointer drag and arrow keys update the DOM value; decorative spring settling does not change the actual numeric value. Provide reset, focus, disabled/loading state and a plain 2D control. Optional hover light responds subtly, only when the input system supports hover.

**Gate:** a user can operate it without seeing the 3D object. It does not start playing sound, steal scrolling or require a mouse. Test the translucent object's overdraw/cost and shipping fallback on the target browser. This recipe is an implementation guide, not a bundled/tested glass shader or native dial scene.
