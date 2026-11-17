// Commit message policy for the PhenoShared root PR check
// "Validate conventional commit title" (.github/workflows/pr-lint.yml).
//
// Human commits keep the full @commitlint/config-conventional discipline,
// including body-max-line-length at 100 characters.
//
// Dependabot commits are exempted, because Dependabot writes the body itself
// and its mandatory compare/changelog links cannot be wrapped without breaking
// the markdown link. Measured across 188 Dependabot commits in this repository
// the longest body line is 286 characters, so no single numeric cap both admits
// Dependabot and constrains human prose. The exemption is keyed on Dependabot's
// own machine-written markers, so a human commit cannot reach it by accident.

const DEPENDABOT_MARKERS = [
  /^- dependency-name: \S+$/m,
  /^Signed-off-by: dependabot\[bot\] <support@github\.com>$/m,
];

const isDependabotCommit = (message) =>
  DEPENDABOT_MARKERS.every((pattern) => pattern.test(message));

module.exports = {
  extends: ["@commitlint/config-conventional"],
  ignores: [isDependabotCommit],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "revert",
      ],
    ],
    "type-case": [2, "always", "lower-case"],
    "subject-empty": [2, "never"],
    "subject-full-stop": [2, "never", "."],
    "subject-case": [2, "always", "lower-case"],
    "header-max-length": [2, "always", 100],
    "body-max-line-length": [2, "always", 100],
  },
};
