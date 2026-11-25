import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}", "scripts/**/*.test.{ts,mjs}", "tests/**/*.test.ts"],
    exclude: ["**/node_modules/**", "**/target/**", "worktrees/**", "dist/**"],
  },
});
