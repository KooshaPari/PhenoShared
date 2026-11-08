/**
 * Parse and validate `@user-story` JSDoc frontmatter embedded in a
 * Playwright spec file.
 *
 * The frontmatter is a JSDoc block of the form:
 *
 *   /**
 *    * @user-story
 *    * ---
 *    * journey_id: streamlit-hf-search
 *    * title: HuggingFace search journey
 *    * ... (YAML body) ...
 *    * ---
 *    * ... (free-form prose, ignored) ...
 *    *\/
 *
 * Each YAML line is prefixed with ` * ` inside the JSDoc block; we
 * strip that prefix before handing the body to the YAML parser.
 */
import { parse as parseYaml } from "yaml";

export interface UserStoryFrontmatter {
  journey_id: string;
  title: string;
  persona: string;
  given: string;
  when: string[];
  then: string[];
  traces_to: string[];
  record: boolean;
  blind_judge: "auto" | "manual" | "off";
  family: string;
}

export class FrontmatterError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FrontmatterError";
  }
}

const JSDOC_BLOCK_RE = /\/\*\*([\s\S]*?)\*\//g;
const YAML_DELIM_RE = /^\s*---\s*$/;

/**
 * Extract the first `@user-story` JSDoc block from a source string
 * and return the raw YAML body (still line-prefixed).
 */
export function extractUserStoryBlock(source: string): string | null {
  JSDOC_BLOCK_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = JSDOC_BLOCK_RE.exec(source)) !== null) {
    const body = match[1];
    if (body.includes("@user-story")) {
      return body;
    }
  }
  return null;
}

/**
 * Strip the JSDoc `\n * ` prefix from each line and return the
 * content bounded by the `---` fences.
 */
export function unwrapYamlBody(block: string): string {
  const lines = block
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*\*\s?/, ""));

  // Find fences.
  let startIdx = -1;
  let endIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (YAML_DELIM_RE.test(lines[i])) {
      if (startIdx === -1) {
        startIdx = i;
      } else {
        endIdx = i;
        break;
      }
    }
  }
  if (startIdx === -1 || endIdx === -1) {
    throw new FrontmatterError(
      "@user-story block is missing `---` YAML fences",
    );
  }
  return lines.slice(startIdx + 1, endIdx).join("\n");
}

function requireString(obj: Record<string, unknown>, key: string): string {
  const v = obj[key];
  if (typeof v !== "string" || v.length === 0) {
    throw new FrontmatterError(
      `@user-story frontmatter: required string \`${key}\` is missing or empty`,
    );
  }
  return v;
}

function requireStringArray(
  obj: Record<string, unknown>,
  key: string,
): string[] {
  const v = obj[key];
  if (!Array.isArray(v) || v.some((x) => typeof x !== "string")) {
    throw new FrontmatterError(
      `@user-story frontmatter: \`${key}\` must be an array of strings`,
    );
  }
  return v as string[];
}

/**
 * Validate the parsed YAML object and return a typed frontmatter.
 */
export function validate(obj: unknown): UserStoryFrontmatter {
  if (typeof obj !== "object" || obj === null) {
    throw new FrontmatterError("@user-story frontmatter must be a mapping");
  }
  const o = obj as Record<string, unknown>;

  const journey_id = requireString(o, "journey_id");
  if (!/^[a-z0-9][a-z0-9-]*$/.test(journey_id)) {
    throw new FrontmatterError(
      `@user-story frontmatter: journey_id \`${journey_id}\` must be kebab-case`,
    );
  }

  const record = o.record;
  if (typeof record !== "boolean") {
    throw new FrontmatterError(
      "@user-story frontmatter: `record` must be a boolean",
    );
  }

  const blind = o.blind_judge ?? "auto";
  if (blind !== "auto" && blind !== "manual" && blind !== "off") {
    throw new FrontmatterError(
      `@user-story frontmatter: blind_judge must be one of auto|manual|off (got ${String(blind)})`,
    );
  }

  return {
    journey_id,
    title: requireString(o, "title"),
    persona: requireString(o, "persona"),
    given: requireString(o, "given"),
    when: requireStringArray(o, "when"),
    then: requireStringArray(o, "then"),
    traces_to: requireStringArray(o, "traces_to"),
    record,
    blind_judge: blind,
    family: requireString(o, "family"),
  };
}

/**
 * Full pipeline: source string -> validated frontmatter.
 */
export function parseUserStoryFrontmatter(
  source: string,
): UserStoryFrontmatter {
  const block = extractUserStoryBlock(source);
  if (block === null) {
    throw new FrontmatterError(
      "spec file has no `@user-story` JSDoc block",
    );
  }
  const yamlBody = unwrapYamlBody(block);
  let parsed: unknown;
  try {
    parsed = parseYaml(yamlBody);
  } catch (e) {
    throw new FrontmatterError(
      `@user-story YAML failed to parse: ${(e as Error).message}`,
    );
  }
  return validate(parsed);
}
