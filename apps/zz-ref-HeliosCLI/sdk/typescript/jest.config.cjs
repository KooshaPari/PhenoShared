/** @type {import('jest').Config} */
const { pathToFileURL } = require("node:url");

// `src/exec.ts` calls createRequire(import.meta.url), so the mocked value has to
// be a file URL that Node will actually accept. The previous
// "file://" + __dirname built a malformed URL on Windows:
//   file://C:\Users\...\dist\index.js
// and createRequire rejects it with "The argument 'filename' must be a file URL
// object, file URL string, or absolute path string". pathToFileURL emits the
// correct form on every platform:
//   file:///C:/Users/.../dist/index.js   (Windows)
//   file:///home/.../dist/index.js       (POSIX)
const distIndexUrl = pathToFileURL(__dirname + "/dist/index.js").href;

module.exports = {
  preset: "ts-jest/presets/default-esm",
  testEnvironment: "node",
  extensionsToTreatAsEsm: [".ts"],
  setupFilesAfterEnv: ["<rootDir>/tests/setupCodexHome.ts"],
  moduleNameMapper: {
    "^(\\.{1,2}/.*)\\.js$": "$1",
  },
  testMatch: ["**/tests/**/*.test.ts"],
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        useESM: true,
        tsconfig: "tsconfig.json",
        diagnostics: {
          ignoreCodes: [1343],
        },
        astTransformers: {
          before: [
            {
              path: "ts-jest-mock-import-meta",
              // Workaround for meta.url not working in jest
              options: { metaObjectReplacement: { url: distIndexUrl } },
            },
          ],
        },
      },
    ],
  },
};
