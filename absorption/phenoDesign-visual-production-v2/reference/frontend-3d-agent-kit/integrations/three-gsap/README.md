# Three.js + GSAP integration reference

**Status: JavaScript syntax checked; dependencies/build/GPU runtime NOT_RUN here.** This is an implementation reference, not a fabricated tested production starter. The kit build environment could not install remote npm packages and did not expose WebGL.

The adapter loads the real kit GLB, uses an environment-lit Three.js scene and a single ScrollTrigger progress owner, separates semantic nodes with rest transforms, provides manual controls, respects reduced motion and stops scheduling frames when inactive. It is deliberately separate from the no-dependency offline demo.

## Explicit local setup

Review the source and current license of Three.js/GSAP/Vite before approving installation. In this folder:

```bash
npm install --save-exact three gsap
npm install --save-dev --save-exact vite
npm run dev
```

These commands require network access and execute the package manager; they are **not run automatically by this kit**. They resolve the approved installation's current packages, save exact versions and produce a real lockfile. Record that lock and test this adapter against it. No invented lockfile or assumed "latest" version is included. A deliberate known-version matrix can be substituted after qualification.

`prepare.mjs` copies only the kit-owned GLB and poster into `public/`. The dev server binds to loopback. Check its printed local address. For a build, run `npm run build`, then test the built output with `npm run preview`. Do not deploy as part of setup.

## Before integrating into a product

Test the actual GLTFLoader output names/custom properties and material semantics; shader/decoder compatibility; startup and cold-cache failure; mobile camera framing; keyboard/touch interaction; reverse/seek and reduced motion; resource disposal during route lifecycle and browser history restoration. Adapt the module to the application's actual component lifecycle rather than copying pagehide cleanup verbatim into an SPA.

The reference retains an explicit GPU-context-loss poster and expects reload for restoration. It does not implement a full automatic context restoration lifecycle, production accessibility audit, asset streaming or adaptive quality engine. Code completion is not acceptance.

See catalog R08/R10/R34 for primary documentation and GSAP's custom license. GSAP is not MIT merely because the runtime may be free to use under its terms.
