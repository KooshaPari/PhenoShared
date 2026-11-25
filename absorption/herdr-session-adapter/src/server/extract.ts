// Untrusted output: strip control sequences, never execute. Heuristic only.
const ANSI = /\u001b\[[0-9;?]*[ -\/]*[@-~]|\u001b\][^\u0007]*\u0007|[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g;

export function extractResult(raw: string, promptEcho: string, maxChars = 8000): { text: string; method: "heuristic" } {
  const clean = raw.replace(ANSI, "");
  const first = promptEcho.split("\n")[0].trim().slice(0, 80);
  const idx = first ? clean.lastIndexOf(first) : -1;
  let body = idx >= 0 ? clean.slice(idx + first.length) : clean;
  body = body.replace(/^[^\n]*\n/, "").trimEnd(); // drop rest of echoed line
  return { text: body.slice(-maxChars).trim(), method: "heuristic" };
}
