/**
 * Electrobun build configuration for AgilePlus desktop (step-1).
 */

import type { ElectrobunConfig } from "electrobun";

export default {
  app: {
    name: "AgilePlus",
    identifier: "dev.agileplus.desktop",
    version: "0.1.0",
  },
  build: {
    bun: {
      entrypoint: "src/index.ts",
    },
    views: {
      main: {
        entrypoint: "src/views/main.ts",
      },
    },
    copy: {
      "src/views/main.html": "views/main/index.html",
      "src/views/main.css": "views/main/main.css",
    },
    mac: {
      bundleCEF: false,
    },
    linux: {
      bundleCEF: false,
    },
    win: {
      bundleCEF: false,
    },
  },
} satisfies ElectrobunConfig;
