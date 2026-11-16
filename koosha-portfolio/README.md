# koosha-portfolio

Personal landing page for `<REDACTED>.com`.

This repo replaces the old Adobe Portfolio surface with a cleaner, route-based
site that keeps the legacy entry points alive while presenting current work
more clearly.

## Stack

- Astro 6
- Bun
- Static deployment on Vercel

## Local development

```bash
bun install
bun run dev
```

## Build

```bash
bun run build
bun run preview
```

## Content

- Home: personal intro, featured projects, and legacy forwards
- `/projects`: project index
- `/projects/<slug>`: project detail pages
- `/about`: bio and working style
- `/resume`: public resume summary
- `/contact`: social and email routes

## Legacy forwards

The site preserves common old portfolio entry points such as `/portfolio`,
`/work`, `/cv`, and project shortcuts like `/byteport` and `/thegent`.

Update those mappings in `vercel.json` and `src/data/site.ts`.
