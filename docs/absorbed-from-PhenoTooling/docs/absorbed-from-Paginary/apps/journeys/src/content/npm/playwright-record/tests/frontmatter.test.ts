import { describe, it, expect } from "vitest";
import {
  parseUserStoryFrontmatter,
  extractUserStoryBlock,
  unwrapYamlBody,
  FrontmatterError,
} from "../src/frontmatter";

const VALID_SPEC = `
/**
 * @user-story
 * ---
 * journey_id: demo-journey
 * title: Demo journey
 * persona: Researcher
 * given: server up
 * when:
 *   - do a thing
 *   - do another thing
 * then:
 *   - assertion one
 *   - assertion two
 * traces_to: [FR-001, FR-002]
 * record: true
 * blind_judge: auto
 * family: streamlit
 * ---
 * Some prose after the fences.
 */
import { test } from '@phenotype/playwright-record';
test('demo', async () => {});
`;

describe("extractUserStoryBlock", () => {
  it("finds the @user-story JSDoc block", () => {
    const block = extractUserStoryBlock(VALID_SPEC);
    expect(block).not.toBeNull();
    expect(block!).toContain("journey_id: demo-journey");
  });

  it("returns null when no block present", () => {
    expect(extractUserStoryBlock("/** no story here */")).toBeNull();
  });
});

describe("unwrapYamlBody", () => {
  it("extracts body between --- fences and strips prefixes", () => {
    const block = extractUserStoryBlock(VALID_SPEC)!;
    const body = unwrapYamlBody(block);
    expect(body).toContain("journey_id: demo-journey");
    expect(body).not.toContain("* journey_id");
  });

  it("throws on missing fences", () => {
    expect(() =>
      unwrapYamlBody("\n * @user-story\n * no fences here\n"),
    ).toThrow(FrontmatterError);
  });
});

describe("parseUserStoryFrontmatter", () => {
  it("parses a valid spec", () => {
    const fm = parseUserStoryFrontmatter(VALID_SPEC);
    expect(fm.journey_id).toBe("demo-journey");
    expect(fm.when).toEqual(["do a thing", "do another thing"]);
    expect(fm.then).toEqual(["assertion one", "assertion two"]);
    expect(fm.traces_to).toEqual(["FR-001", "FR-002"]);
    expect(fm.record).toBe(true);
    expect(fm.blind_judge).toBe("auto");
  });

  it("rejects malformed journey_id", () => {
    const bad = VALID_SPEC.replace("demo-journey", "Demo_Journey");
    expect(() => parseUserStoryFrontmatter(bad)).toThrow(/kebab-case/);
  });

  it("rejects missing required field", () => {
    const bad = VALID_SPEC.replace(" * persona: Researcher\n", "");
    expect(() => parseUserStoryFrontmatter(bad)).toThrow(/persona/);
  });

  it("rejects invalid blind_judge value", () => {
    const bad = VALID_SPEC.replace("blind_judge: auto", "blind_judge: yolo");
    expect(() => parseUserStoryFrontmatter(bad)).toThrow(/blind_judge/);
  });

  it("rejects non-array when field", () => {
    const bad = VALID_SPEC.replace(
      " * when:\n *   - do a thing\n *   - do another thing\n",
      " * when: just a string\n",
    );
    expect(() => parseUserStoryFrontmatter(bad)).toThrow(/when/);
  });

  it("rejects non-boolean record", () => {
    const bad = VALID_SPEC.replace("record: true", 'record: "yes"');
    expect(() => parseUserStoryFrontmatter(bad)).toThrow(/record/);
  });

  it("errors when no @user-story block present", () => {
    expect(() => parseUserStoryFrontmatter("const x = 1;")).toThrow(
      /no .?@?user-story/,
    );
  });
});
