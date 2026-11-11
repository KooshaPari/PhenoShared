import { defineConfig } from "vitest/config";

// Local vitest config — phenoResearchEngine ports tree only.
// The project root has no top-level vitest config; vitest would otherwise
// walk up the directory tree and pick up a sibling repo's include globs.
// Scoping to ports/tests keeps this package self-contained.
export default defineConfig({
  test: {
    include: ["ports/tests/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["ports/retriever.ts"],
      reporter: ["text", "json-summary"],
    },
  },
});
