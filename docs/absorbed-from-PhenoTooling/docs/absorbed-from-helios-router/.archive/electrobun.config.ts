import type { ElectrobunConfig } from "electrobun";

export default {
  app: {
    name: "Helios Router",
    identifier: "sh.phenotype.helios-router",
    version: "0.1.0",
  },
  build: {
    bun: {
      entrypoint: "src/main/index.ts",
      external: [],
    },
    views: {
      dashboard: {
        entrypoint: "src/renderer/index.ts",
      },
    },
    icon: "assets/brand/app.ico",
    watch: ["src/main/**", "src/renderer/**"],
    watchIgnore: [],
  },
} satisfies ElectrobunConfig;
