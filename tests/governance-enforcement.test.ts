// Traceability: FUNCTIONAL_REQUIREMENTS.md FR-PH-007;
// governance outcomes: docs/governance/happy-path-checklist.md.
import { mkdtempSync, writeFileSync, rmSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { test, expect } from "vitest";

const guard = resolve("governance/happy-path-precommit.sh");
for (const [text, expected] of [["feature fixed", 1], ["ordinary change", 0], ["[fixed]", 1], ["`verified`", 1], ["workspace uses RetryStrategy.FIXED", 0], ["✅", 1], ["feature fixed\nEvidence: user-confirmed", 0]] as const) {
  test(`production guard exit ${expected}: ${text}`, () => {
    const dir = mkdtempSync(join(tmpdir(), "handbook-guard-"));
    try {
      expect(spawnSync("git", ["init", "--quiet", dir]).status).toBe(0);
      writeFileSync(join(dir, "change.txt"), `${text}\n`);
      expect(spawnSync("git", ["add", "change.txt"], { cwd: dir }).status).toBe(0);
      const result = spawnSync("sh", [guard], { cwd: dir, encoding: "utf8", env: { ...process.env, HAPPY_PATH_FAIL_ON: "block", HAPPY_PATH_DISABLE: "", HAPPY_PATH_POLICY_SKIP: "", HAPPY_PATH_BASE: "", HAPPY_PATH_HEAD: "" } });
      expect(result.status, result.stdout + result.stderr).toBe(expected);
      if (expected) expect(result.stdout).toContain("FAIL [R1]");
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
}

for (const [content, expected] of [["feature fixed\n", 1], ["feature fixed\nEvidence: user-confirmed\n", 0]] as const) {
  test(`clean checkout commit range exit ${expected}`, () => {
    const dir = mkdtempSync(join(tmpdir(), "handbook-range-"));
    const git = (...args: string[]) => spawnSync("git", ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", ...args], { cwd: dir, encoding: "utf8" });
    try {
      expect(git("init", "--quiet").status).toBe(0);
      expect(git("commit", "--allow-empty", "-m", "base").status).toBe(0);
      const base = git("rev-parse", "HEAD").stdout.trim();
      writeFileSync(join(dir, "change.txt"), content);
      expect(git("add", "change.txt").status).toBe(0);
      expect(git("commit", "-m", "change").status).toBe(0);
      expect(git("diff", "--cached").stdout).toBe("");
      const result = spawnSync("sh", [guard], { cwd: dir, encoding: "utf8", env: { ...process.env, HAPPY_PATH_FAIL_ON: "block", HAPPY_PATH_DISABLE: "", HAPPY_PATH_POLICY_SKIP: "", HAPPY_PATH_BASE: base, HAPPY_PATH_HEAD: "HEAD" } });
      expect(result.status, result.stdout + result.stderr).toBe(expected);
      if (expected) expect(result.stdout).toContain("FAIL [R1]");
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
}


for (const destination of ["report.txt", "report with spaces.txt", "report\tname.txt"]) {
  test(`moving exempt policy content into ${JSON.stringify(destination)} enforces claims`, () => {
    const dir = mkdtempSync(join(tmpdir(), "handbook-rename-"));
    const git = (...args: string[]) => spawnSync("git", ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", ...args], { cwd: dir, encoding: "utf8" });
    try {
      expect(git("init", "--quiet").status).toBe(0);
      mkdirSync(join(dir, "governance"));
      writeFileSync(join(dir, "governance", "example.txt"), "ordinary text\n".repeat(30) + "feature fixed\n");
      expect(git("add", ".").status).toBe(0);
      expect(git("commit", "-m", "base").status).toBe(0);
      expect(git("mv", "governance/example.txt", destination).status).toBe(0);
      const result = spawnSync("sh", [guard], { cwd: dir, encoding: "utf8", env: { ...process.env, HAPPY_PATH_FAIL_ON: "block", HAPPY_PATH_DISABLE: "", HAPPY_PATH_POLICY_SKIP: "", HAPPY_PATH_BASE: "", HAPPY_PATH_HEAD: "" } });
      expect(result.status, result.stdout + result.stderr).toBe(1);
      expect(result.stdout).toContain("FAIL [R1]");
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
}

for (const revisions of [{ HAPPY_PATH_BASE: "missing-revision", HAPPY_PATH_HEAD: "HEAD" }, { HAPPY_PATH_BASE: "", HAPPY_PATH_HEAD: "HEAD" }]) {
  test(`invalid range does not fall back to empty staging: ${JSON.stringify(revisions)}`, () => {
    const dir = mkdtempSync(join(tmpdir(), "handbook-invalid-range-"));
    try {
      expect(spawnSync("git", ["init", "--quiet", dir]).status).toBe(0);
      const result = spawnSync("sh", [guard], { cwd: dir, encoding: "utf8", env: { ...process.env, HAPPY_PATH_FAIL_ON: "block", ...revisions } });
      expect(result.status).not.toBe(0);
      expect(result.stderr).not.toBe("");
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
}


test("created main push scans the complete committed tree", () => {
  const dir = mkdtempSync(join(tmpdir(), "handbook-created-ref-"));
  const git = (...args: string[]) => spawnSync("git", ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", ...args], { cwd: dir, encoding: "utf8" });
  try {
    expect(git("init", "--quiet", "--initial-branch=main").status).toBe(0);
    writeFileSync(join(dir, "change.txt"), "ordinary change\n");
    expect(git("add", ".").status).toBe(0);
    expect(git("commit", "-m", "initial").status).toBe(0);
    const env = { ...process.env, HAPPY_PATH_FAIL_ON: "block", HAPPY_PATH_BASE: "0".repeat(40), HAPPY_PATH_HEAD: "HEAD" };
    const clean = spawnSync("sh", [guard], { cwd: dir, encoding: "utf8", env });
    expect(clean.status, clean.stdout + clean.stderr).toBe(0);
    writeFileSync(join(dir, "change.txt"), "feature fixed\n");
    expect(git("add", ".").status).toBe(0);
    expect(git("commit", "-m", "claim").status).toBe(0);
    const violation = spawnSync("sh", [guard], { cwd: dir, encoding: "utf8", env });
    expect(violation.status, violation.stdout + violation.stderr).toBe(1);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
