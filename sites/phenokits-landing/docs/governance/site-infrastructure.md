# Site Infrastructure

PhenoKits landing is served from Vercel at `https://phenokits.kooshapari.com` and
mirrored to GitHub Pages at `https://kooshapari.github.io/phenokits-landing/`.

The Pages workflow builds with `GITHUB_PAGES=true`, which makes Astro emit links
under `/phenokits-landing/`. The custom-domain build keeps `/` as the base path.

The shared visual base is GMK Arch teal, rooted at `#7ebab5`.
