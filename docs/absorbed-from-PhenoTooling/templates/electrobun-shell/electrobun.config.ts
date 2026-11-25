/**
 * phenotype-desktop Electrobun shell template
 *
 * USAGE: Copy this directory alongside your web app, then edit the three
 * CONFIGURE sections below. Run `bun install && bun dev` on macOS.
 *
 * Template variables (find-replace before use):
 *   __APP_NAME__         e.g. "MyApp"
 *   __APP_ID__           e.g. "com.example.myapp"
 *   __APP_VERSION__      e.g. "0.1.0"
 *   __DEFAULT_DEV_URL__  e.g. "http://localhost:3000"
 *   __VIEWS_ENTRYPOINT__ e.g. "../web/dist/index.html"  (relative from this dir)
 */
import type { ElectrobunConfig } from "electrobun";

// ── CONFIGURE 1: App identity ─────────────────────────────────────────────────
const APP_NAME = "__APP_NAME__";
const APP_ID = "__APP_ID__";
const APP_VERSION = "__APP_VERSION__";

// ── CONFIGURE 2: Renderer (dev server URL or bundled views path) ──────────────
const DEFAULT_DEV_URL = "__DEFAULT_DEV_URL__";

// ── CONFIGURE 3: Bundled views entrypoint (production) ───────────────────────
const VIEWS_ENTRYPOINT = "__VIEWS_ENTRYPOINT__";

export default {
  app: {
    name: APP_NAME,
    identifier: APP_ID,
    version: APP_VERSION,
  },
  runtime: {
    exitOnLastWindowClosed: true,
    // Passed through to main.ts via BuildConfig at runtime
    devRendererUrl: process.env.RENDERER_URL ?? DEFAULT_DEV_URL,
  },
  build: {
    bun: {
      entrypoint: "src/main.ts",
    },
    views: [
      {
        name: "app",
        entrypoint: VIEWS_ENTRYPOINT,
      },
    ],
  },
} satisfies ElectrobunConfig;
