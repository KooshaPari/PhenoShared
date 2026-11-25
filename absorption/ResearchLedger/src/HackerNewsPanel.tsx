import { invoke } from "@tauri-apps/api/core";
import { useState } from "react";

type ImportResult = { created: number; updated: number; unchanged: number; failed: number };
type CaptureState = "needs-auth" | "ready" | "capturing";
type HackerNewsPanelProps = {
  vaultPath: string;
  setMessage: (value: string) => void;
  hackernewsProfile: string;
  setHackernewsProfile: (value: string) => void;
};

export function HackerNewsPanel({
  vaultPath,
  setMessage,
  hackernewsProfile,
  setHackernewsProfile,
}: HackerNewsPanelProps) {
  const [hackernewsPath, setHackernewsPath] = useState("");
  const [hackernewsUsername, setHackernewsUsername] = useState("");
  const [hnState, setHnState] = useState<CaptureState>("needs-auth");

  const requireVault = () => {
    if (vaultPath) return true;
    setMessage("Select a vault before running a source action.");
    return false;
  };

  const captureHackerNews = async () => {
    if (!requireVault()) return;
    const username = hackernewsUsername.trim();
    if (!username) {
      setHnState("needs-auth");
      setMessage("Sign in to news.ycombinator.com first, then enter your HN username.");
      return;
    }
    setHnState("capturing");
    const url = `https://news.ycombinator.com/saved?id=${encodeURIComponent(username)}`;
    try {
      const value = await invoke<ImportResult>("capture_hackernews_browser", {
        vaultPath,
        activityUrl: url,
        profilePath: hackernewsProfile || null,
      });
      setMessage(`Captured ${value.created + value.updated} Hacker News stories; ${value.unchanged} unchanged.`);
    } catch (error) {
      setMessage(`Could not run capture_hackernews_browser: ${String(error)}`);
    }
    setHnState("ready");
  };

  return (
    <section className="capture-panel" aria-label="Hacker News capture">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">HACKER NEWS CONNECTION</p>
          <h3>{hnState === "needs-auth" ? "Sign in once, capture locally" : "Browser profile connected"}</h3>
       </div>
        <span className={`state-pill ${hnState}`}>
          {hnState === "needs-auth" ? "AUTH REQUIRED" : hnState === "capturing" ? "CAPTURING" : "READY"}
       </span>
     </div>
      <p className="muted">
        Use a dedicated persistent Chrome profile. ResearchLedger opens Hacker News in that profile and
        scrolls your saved-stories queue; cookies and MFA stay in your browser, never on disk.
     </p>
      <div className="profile-row">
        <input
          aria-label="Hacker News browser profile"
          placeholder="Default profile or /Users/you/Library/Application Support/ResearchLedger/hackernews-profile"
          value={hackernewsProfile}
          onChange={(event) => setHackernewsProfile(event.target.value)}
        />
        <button
          className="button secondary"
          type="button"
          onClick={() => void captureHackerNews()}
          disabled={hnState === "capturing"}
        >
          Open Hacker News sign-in
       </button>
     </div>
      <div className="capture-actions">
        <input
          aria-label="Hacker News username"
          placeholder="Hacker News username (used to build saved-stories URL)"
          value={hackernewsUsername}
          onChange={(event) => setHackernewsUsername(event.target.value)}
        />
        <button
          className="button primary"
          type="button"
          onClick={() => void captureHackerNews()}
          disabled={hnState === "capturing"}
        >
          Capture saved stories in browser
      </button>
        <input
          aria-label="Hacker News capture path"
          placeholder="Optional capture JSON path"
          value={hackernewsPath}
          onChange={(event) => setHackernewsPath(event.target.value)}
        />
        <button
          className="button secondary"
          type="button"
          onClick={async () => {
            if (!requireVault()) return;
            try {
              const value = await invoke<ImportResult>("import_hackernews_capture", {
                vaultPath,
                capturePath: hackernewsPath,
              });
              setMessage(`Imported ${value.created + value.updated} Hacker News stories.`);
            } catch (error) {
              setMessage(`Could not run import_hackernews_capture: ${String(error)}`);
            }
          }}
        >
          Import capture
       </button>
     </div>
      <p className="import-message">
        Hacker News does not offer a public saved-stories API, so the browser-based capture is the
        supported path. Sign in once and your saved-stories queue is mirrored locally.
     </p>
   </section>
  );
}
