import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(__dirname, "..");
const read = (path: string) => readFileSync(join(root, path), "utf8");
const spec = read("SPEC.md");

describe("functional requirement traceability", () => {
  test("FR-PH-001 pattern library has executable source evidence", () => {
    for (const path of [
      "docs/patterns/auth/oauth-pkce.md",
      "docs/patterns/caching/cache-aside.md",
      "docs/patterns/architecture/cqrs.md",
      "docs/patterns/async/event-driven.md",
      "docs/patterns/observability/health-checks.md",
    ]) {
      expect(existsSync(join(root, path)), path).toBe(true);
    }
  });

  test("FR-PH-002 anti-pattern catalog covers core risk classes", () => {
    expect(spec).toContain("### Security Anti-Patterns");
    expect(spec).toContain("### Performance Anti-Patterns");
    expect(spec).toContain("ANTI-PATTERN-SEC-001");
  });

  test("FR-PH-003 methodology and workflow guidance is indexed", () => {
    expect(spec).toContain("METHODOLOGY-001: TDD");
    expect(spec).toContain("METHODOLOGY-002: BDD");
    expect(spec).toContain("CHECKLIST-001: Pre-Deployment");
  });

  test("FR-PH-004 domain practices cover key subsystem boundaries", () => {
    for (const heading of [
      "### Authentication Patterns",
      "### Caching Patterns",
      "### Observability Patterns",
      "### Database Patterns",
    ]) {
      expect(spec).toContain(heading);
    }
  });

  test("FR-PH-005 technology guidance includes all declared languages", () => {
    for (const language of ["```rust", "```go", "```typescript", "```python"]) {
      expect(spec).toContain(language);
    }
  });

  test("FR-PH-006 site navigation and local search are configured", () => {
    const config = read("docs/.vitepress/config.mts");
    expect(config).toContain('provider: "local"');
    expect(config).toContain("sidebar:");
    expect(config).toContain('{ text: "Patterns", link: "/patterns/" }');
  });

  test("FR-PH-007 implementation checklist is actionable", () => {
    for (const section of [
      "## Code Quality",
      "## Security",
      "## Performance",
      "## Deployment",
    ]) {
      expect(spec).toContain(section);
    }
  });

  test("FR-PH-008 version history and migration evidence exist", () => {
    expect(JSON.parse(read("package.json")).version).toMatch(/^\d+\.\d+\.\d+$/);
    expect(existsSync(join(root, "CHANGELOG.md"))).toBe(true);
    expect(existsSync(join(root, "adrs"))).toBe(true);
    expect(spec).toContain("## Migration Guide");
  });
});
