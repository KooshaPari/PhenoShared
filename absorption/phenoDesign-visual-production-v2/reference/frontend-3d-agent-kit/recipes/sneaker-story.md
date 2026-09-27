# Recipe: a scroll-driven sneaker construction story

**Input:** original/rights-cleared trainer, intended audience and three useful product claims. The bundled model is a fictional design study, so its page describes construction rather than inventing retail specifications.

**Scene:** `Upper`, `Midsole`, `Outsole` plus collar/tongue/laces/support nodes. Keep a root for the story pose and independent user-orbit offset. Rest transforms are immutable.

**Beat 1, progress 0–0.28:** show the whole silhouette in a quiet studio composition. Initial view must work as a poster. No long camera fly-in before the user sees the product.

**Beat 2, progress 0.28–0.76:** rotate deliberately toward a construction view; separate the outsole downward, midsole slightly down and upper slightly up. Group laces/tongue with the appropriate upper movement. Keep offsets bounded and local to the shoe. Text explains the same structure outside the canvas.

**Beat 3, progress 0.76–1:** reassemble and reveal finish. Material swatches affect the accent family only, not the studio or sole. Direct controls can separate/rejoin regardless of story position and reset orbit without clearing the selected material.

**Input:** native vertical scrolling; horizontal drag and focused arrow keys for orientation; real material buttons; separate/rejoin and pause buttons. Test touch cancel and free page scroll. Motion preference removes scroll coupling by default, not product information.

**Autonomous asset pass:** use `scripts/build_asset.py`, inspect clay silhouettes, rebuild in Blender, repair constructive overlaps, add UVs/bake maps where needed, export and inspect again. The seed is an editable starter, not the artistic acceptance target.

**Test:** 0→0.5→1→0, rapid swatch changes, pause during scroll, rotate then reset, mobile resize mid-sequence, no-JS and renderer failure. Keep each motion state's outputs observable in diagnostics during testing without exposing private system data.
