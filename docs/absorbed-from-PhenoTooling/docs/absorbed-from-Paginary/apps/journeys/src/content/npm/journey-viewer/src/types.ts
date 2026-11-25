// Types generated/derived from schema/manifest.schema.json. Keep in sync with
// phenotype-journey-core's serde types.

export interface Annotation {
  /** `[x, y, width, height]` in source image pixels. */
  bbox: [number, number, number, number];
  label: string;
  color?: string | null;
  style?: "solid" | "dashed";
  note?: string | null;
  kind?: "region" | "pointer" | "highlight";
}

export interface Step {
  index: number;
  slug: string;
  intent: string;
  screenshot_path: string;
  description?: string | null;
  /** Blind-describe (no-intent) observation rendered alongside `intent` in the viewer. */
  blind_description?: string | null;
  judge_score?: number | null;
  annotations?: Annotation[] | null;
  /**
   * Tier 0 structural-capture sibling path relative to `screenshot_path`.
   * Emitted by the Swift (macOS), Playwright (streamlit), and Rust (cli-ansi)
   * walkers. Shape is family-discriminated by the top-level `family` field.
   */
  structural_path?: string | null;
}

/** Per-family payload written to `<frame>.structural.json`. */
export interface StructuralMacos {
  family: "macos";
  role: string;
  label: string;
  value?: string | null;
  identifier: string;
  frame: { x: number; y: number; w: number; h: number };
  children: StructuralMacos[];
}

export interface StructuralStreamlit {
  family: "streamlit";
  url: string;
  title: string;
  viewport: { width: number; height: number } | null;
  aria: string;
  html: string;
}

export interface StructuralCli {
  family: "cli";
  rows: number;
  cols: number;
  terminal_title?: string | null;
  cursor: { row: number; col: number; visible: boolean };
  cells: Array<{
    row: number;
    col: number;
    ch: string;
    fg?: string | null;
    bg?: string | null;
    bold: boolean;
    italic: boolean;
    underline: boolean;
    inverse: boolean;
  }>;
}

export type StructuralSnapshot = StructuralMacos | StructuralStreamlit | StructuralCli;

export interface Verification {
  overall_score: number;
  describe_confidence: number;
  judge_confidence: number;
  all_intents_passed: boolean;
  mode: "mock" | "api";
  timestamp: string;
}

export interface Manifest {
  id: string;
  intent: string;
  recording?: string | null;
  recording_gif?: string | null;
  keyframe_count?: number;
  passed?: boolean;
  steps?: Step[];
  verification?: Verification | null;
  // Legacy field names used by hwLedger's original JourneyViewer:
  title?: string;
  pass?: boolean;
  keyframes?: Array<{ path: string; caption: string }>;
  error?: string;
}
