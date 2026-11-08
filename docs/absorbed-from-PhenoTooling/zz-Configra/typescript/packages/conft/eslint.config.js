// Minimal ESLint flat config (ESLint 8.57+).
// Uses @typescript-eslint/parser so .ts files parse. No rules enabled yet
// beyond what tsc already enforces; add project-specific rules here later.
const tsParser = require('@typescript-eslint/parser');

module.exports = [
  {
    ignores: ['dist/**', 'node_modules/**', 'docs/.vitepress/**'],
  },
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: 'module',
    },
    rules: {},
  },
];
