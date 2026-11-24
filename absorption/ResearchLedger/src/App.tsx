import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { HackerNewsPanel } from "./HackerNewsPanel";

function formatCommandError(command: string, error: unknown): string {
  const raw = String(error ?? "");
  const stripped = raw.replace(/\x1b\[[0-9;]*m/g, "");
  const safe = stripped
    .replace(/\/Users\/[^\s'"]+/g, "[path]")
    .replace(/\/home\/[^\s'"]+/g, "[path]");
  if (
    /Executable doesn'?t exist|ERR_MODULE_NOT_FOUND|Cannot find package ['"]?playwright|chromium.*not installed/i.test(
      safe,
    )
  ) {
    return `Could not run ${command}: Playwright Chromium is not installed. Install the bundled browser runtime, then retry.`;
  }
  if (
    /AUTH[_ ]REQUIRED|not authenticated|sign(?:ed)? in|login required|login page/i.test(
      safe,
    )
  ) {
    return `Could not run ${command}: this provider needs an authenticated browser profile. Sign in, then retry.`;
  }
  if (/timed? ?out|timeout|deadline/i.test(safe)) {
    return `Could not run ${command}: the provider timed out. Check your connection and retry.`;
  }
  if (/rate limit|too many requests/i.test(safe)) {
    return `Could not run ${command}: the provider rate-limited this request. Wait a moment and retry.`;
  }
  if (/ENOENT|no such file|cannot find the path/i.test(safe)) {
    return `Could not run ${command}: the selected capture file or profile path could not be found.`;
  }
  return `Could not run ${command}: ${safe || "unknown provider error"}`;
}

type VaultStatus = {
  selected: boolean;
  path: string | null;
  documentCount: number;
};
type PrimaryView = "inbox" | "library" | "collections" | "graph";
type Result = {
  documentId: string;
  title: string;
  snippet: string;
  sourceUri: string | null;
};
type RetrievalContext = {
  query: string;
  context: string;
  citations: Array<{
    citationId: string;
    documentId: string;
    title: string;
    sourceUri: string | null;
    snippet: string;
  }>;
  coverage: {
    retrieved: number;
    cited: number;
    withSourceUri: number;
    sourceUriRatio: number;
  };
  confidence: {
    score: number;
    label: string;
    rationale: string;
  };
};
type ImportResult = {
  created: number;
  updated: number;
  unchanged: number;
  failed: number;
};
type LocalPreferences = {
  vaultPath: string | null;
  hackernewsProfile: string | null;
  redditProfile: string | null;
  xProfile: string | null;
};
const views: Array<{ id: PrimaryView; label: string; hint: string }> = [
  {
    id: "inbox",
    label: "Inbox",
    hint: "Capture, review, and move sources forward",
  },
  {
    id: "library",
    label: "Library",
    hint: "Browse the indexed research corpus",
  },
  {
    id: "collections",
    label: "Collections",
    hint: "Group sources into working sets",
  },
  { id: "graph", label: "Graph", hint: "See how ideas and sources connect" },
];

export function App() {
  const [activeView, setActiveView] = useState<PrimaryView>("inbox");
  const [vaultPath, setVaultPath] = useState("");
  const [hackernewsProfile, setHackernewsProfile] = useState("");
  const [redditProfile, setRedditProfile] = useState("");
  const [xProfile, setXProfile] = useState("");
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const preferencesHydrated = useRef(false);
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    invoke<LocalPreferences>("load_local_preferences")
      .then((preferences) => {
        setVaultPath(preferences.vaultPath ?? "");
        setHackernewsProfile(preferences.hackernewsProfile ?? "");
        setRedditProfile(preferences.redditProfile ?? "");
        setXProfile(preferences.xProfile ?? "");
      })
      .catch(() => undefined)
      .finally(() => setPreferencesLoaded(true));
  }, []);
  useEffect(() => {
    if (!preferencesLoaded) return;
    if (!preferencesHydrated.current) {
      preferencesHydrated.current = true;
      return;
    }
    const preferences = {
      vaultPath: vaultPath || null,
      hackernewsProfile: hackernewsProfile || null,
      redditProfile: redditProfile || null,
      xProfile: xProfile || null,
    };
    const timer = window.setTimeout(() => {
      void invoke("save_local_preferences", { preferences });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [preferencesLoaded, vaultPath, hackernewsProfile, redditProfile, xProfile]);
  useEffect(() => {
    invoke<VaultStatus>("get_vault_status", { vaultPath: vaultPath || null })
      .then(setStatus)
      .catch(() => setStatus(null));
  }, [vaultPath]);
  const chooseVault = async () => {
    const selected = await open({
      directory: true,
      multiple: false,
      title: "Choose ResearchLedger vault",
    });
    if (typeof selected === "string") setVaultPath(selected);
  };
  const requireVault = () => {
    if (vaultPath) return true;
    setMessage("Select a vault before running a source action.");
    return false;
  };
  const run = async (
    command: string,
    args: Record<string, unknown>,
    success: (value: any) => string,
  ) => {
    if (!requireVault()) return;
    try {
      setMessage(success(await invoke(command, args)));
    } catch (error) {
      setMessage(formatCommandError(command, error));
    }
  };
  const index = views.findIndex((view) => view.id === activeView);
  return (
    <main className="shell">
      <aside className="sidebar">
        <p className="eyebrow">LOCAL RESEARCH SYSTEM</p>
        <h1>ResearchLedger</h1>
        <nav
          aria-label="Primary navigation"
          role="tablist"
          onKeyDown={(event) => {
            const next =
              event.key === "ArrowRight"
                ? (index + 1) % views.length
                : event.key === "ArrowLeft"
                  ? (index + views.length - 1) % views.length
                  : event.key === "Home"
                    ? 0
                    : event.key === "End"
                      ? views.length - 1
                      : -1;
            if (next >= 0) {
              event.preventDefault();
              setActiveView(views[next].id);
              document.getElementById(`tab-${views[next].id}`)?.focus();
            }
          }}
        >
          {views.map((view) => (
            <button
              key={view.id}
              id={`tab-${view.id}`}
              className={`nav-item${activeView === view.id ? " active" : ""}`}
              role="tab"
              aria-selected={activeView === view.id}
              aria-controls={`panel-${view.id}`}
              tabIndex={activeView === view.id ? 0 : -1}
              type="button"
              onClick={() => setActiveView(view.id)}
            >
              <span>{view.label}</span>
              <small>{view.hint}</small>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" /> Local-first · browser capture needs
          Playwright + Chromium
        </div>
      </aside>
      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">{activeView.toUpperCase()}</p>
            <h2>{views[index].hint}</h2>
          </div>
          <button
            className="button secondary"
            type="button"
            onClick={() => void chooseVault()}
          >
            Select vault
          </button>
        </header>
        <section
          id="panel-inbox"
          role="tabpanel"
          aria-labelledby="tab-inbox"
          className="view-panel"
          hidden={activeView !== "inbox"}
        >
          <Inbox
            vaultPath={vaultPath}
            status={status}
            setVaultPath={setVaultPath}
            chooseVault={chooseVault}
            requireVault={requireVault}
            run={run}
            message={message}
            setMessage={setMessage}
            hackernewsProfile={hackernewsProfile}
            setHackernewsProfile={setHackernewsProfile}
            redditProfile={redditProfile}
            setRedditProfile={setRedditProfile}
            xProfile={xProfile}
            setXProfile={setXProfile}
          />
        </section>
        <section
          id="panel-library"
          role="tabpanel"
          aria-labelledby="tab-library"
          className="view-panel"
          hidden={activeView !== "library"}
        >
          <Library vaultPath={vaultPath} />
        </section>
        <section
          id="panel-collections"
          role="tabpanel"
          aria-labelledby="tab-collections"
          className="view-panel"
          hidden={activeView !== "collections"}
        >
          <Collections vaultPath={vaultPath} />
        </section>
        <section
          id="panel-graph"
          role="tabpanel"
          aria-labelledby="tab-graph"
          className="view-panel"
          hidden={activeView !== "graph"}
        >
          <Graph vaultPath={vaultPath} />
        </section>
      </section>
    </main>
  );
}

function Inbox({
  vaultPath,
  status,
  setVaultPath,
  chooseVault,
  requireVault,
  run,
  message,
  setMessage,
  hackernewsProfile,
  setHackernewsProfile,
  redditProfile,
  setRedditProfile,
  xProfile,
  setXProfile,
}: {
  vaultPath: string;
  status: VaultStatus | null;
  setVaultPath: (path: string) => void;
  chooseVault: () => Promise<void>;
  requireVault: () => boolean;
  run: (
    command: string,
    args: Record<string, unknown>,
    success: (value: any) => string,
  ) => Promise<void>;
  message: string;
  setMessage: (value: string) => void;
  hackernewsProfile: string;
  setHackernewsProfile: (value: string) => void;
  redditProfile: string;
  setRedditProfile: (value: string) => void;
  xProfile: string;
  setXProfile: (value: string) => void;
}) {
  const [linkedinPermalink, setLinkedinPermalink] = useState("");
  const [linkedinContent, setLinkedinContent] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [retrievalContext, setRetrievalContext] =
    useState<RetrievalContext | null>(null);
  const [retrieving, setRetrieving] = useState(false);
  const [redditState, setRedditState] = useState<
    "needs-auth" | "ready" | "capturing"
  >("needs-auth");
  const [xState, setXState] = useState<"needs-auth" | "ready" | "capturing">(
    "needs-auth",
  );
  const [redditPath, setRedditPath] = useState("");
  const [redditUsername, setRedditUsername] = useState("");
  const [xPath, setXPath] = useState("");
  const [crawlRootId, setCrawlRootId] = useState("");
  const [crawlDepth, setCrawlDepth] = useState("2");
  const [crawlBudget, setCrawlBudget] = useState("10");
  const importGithubStars = async () => {
    if (!vaultPath) {
      setMessage("Select a vault before running a source action.");
      return;
    }
    await run(
      "import_github_from_gh",
      { vaultPath },
      (value: ImportResult) =>
        `Imported ${value.created + value.updated} repositories; ${value.unchanged} unchanged.`,
    );
  };
  const captureReddit = async () => {
    if (!requireVault()) return;
    const username = redditUsername.trim();
    if (!username) {
      setRedditState("needs-auth");
      setMessage("Enter your Reddit username first.");
      return;
    }
    setRedditState("capturing");
    try {
      const value = await invoke("capture_reddit_browser", {
        vaultPath,
        activityUrl: `https://www.reddit.com/user/${encodeURIComponent(username)}/saved`,
        profilePath: redditProfile || null,
      } as any);
      setMessage(
        "Captured " +
          ((value as any).created + (value as any).updated) +
          " Reddit posts; " +
          (value as any).unchanged +
          " unchanged.",
      );
    } catch (error) {
      setMessage(formatCommandError("capture_reddit_browser", error));
    }
    setRedditState("ready");
  };
  const captureX = async () => {
    if (!requireVault()) return;
    setXState("capturing");
    try {
      const value = await invoke("capture_x_browser", {
        vaultPath,
        activityUrl: "https://x.com/i/bookmarks",
        profilePath: xProfile || null,
      } as any);
      setMessage(
        "Captured " +
          ((value as any).created + (value as any).updated) +
          " X bookmarks; " +
          (value as any).unchanged +
          " unchanged.",
      );
    } catch (error) {
      setMessage(formatCommandError("capture_x_browser", error));
    }
    setXState("ready");
  };
  const search = async () => {
    if (!vaultPath || !query) return;
    try {
      setRetrievalContext(null);
      setResults(
        await invoke<Result[]>("search_documents", {
          vaultPath,
          query,
          limit: 20,
        }),
      );
    } catch {
      setResults([]);
    }
  };
  const retrieve = async () => {
    if (!vaultPath || !query.trim() || retrieving) return;
    setRetrieving(true);
    try {
      setRetrievalContext(
        await invoke<RetrievalContext>("retrieve_context", {
          vaultPath,
          query: query.trim(),
          limit: 8,
        }),
      );
    } catch (error) {
      setMessage(formatCommandError("retrieve_context", error));
      setRetrievalContext(null);
    } finally {
      setRetrieving(false);
    }
  };
  return (
    <>
      <section className="inbox-grid">
        <div className="source-rail">
          <p className="eyebrow">SOURCE CONTROL</p>
          <h3>Move research from raw to useful.</h3>
          <p className="muted">
            Every action stays visible: capture, fetch references, distill, and
            export from one local queue.
          </p>
          <div className="queue-stats">
            <span>
              <strong>{status?.documentCount ?? 0}</strong> indexed
            </span>
            <span>
              <strong>25</strong> enrichment batch
            </span>
          </div>
        </div>
        <div className="action-stack">
          <Action
            title="Reddit"
            label={
              redditState === "needs-auth"
                ? "Connect browser"
                : redditState === "capturing"
                  ? "Capturing..."
                  : "Connected"
            }
            state={
              redditState === "needs-auth"
                ? "Needs username"
                : redditState === "capturing"
                  ? "Capture in progress"
                  : "Ready to capture"
            }
            onClick={() => void captureReddit()}
            disabled={redditState === "capturing"}
          />
          <Action
            title="X"
            label={
              xState === "needs-auth"
                ? "Connect browser"
                : xState === "capturing"
                  ? "Capturing..."
                  : "Connected"
            }
            state={
              xState === "needs-auth"
                ? "Needs authentication"
                : xState === "capturing"
                  ? "Capture in progress"
                  : "Ready to capture"
            }
            onClick={() => void captureX()}
            disabled={xState === "capturing"}
          />
          <Action
            title="GitHub"
            label="Import starred repos"
            state="Uses authenticated gh when token is empty"
            onClick={() => void importGithubStars()}
          />
          <Action
            title="References"
            label="Fetch linked sources"
            state="Run only after an explicit bounded crawl"
            onClick={() =>
              void run(
                "fetch_pending_references",
                { vaultPath, limit: 10 },
                (value: ImportResult) =>
                  `Fetched ${value.updated} linked sources; ${value.failed} failed.`,
              )
            }
          />
          <Action
            title="Enrichment"
            label="Distill pending notes"
            state="Up to 25 sources"
            onClick={() =>
              void run(
                "process_pending_enrichment",
                { vaultPath, limit: 25 },
                (value: ImportResult) =>
                  `Created ${value.created + value.updated} distilled notes.`,
              )
            }
          />
        </div>
      </section>
      <section className="capture-panel" aria-label="Bounded reference crawl">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">REFERENCE TRAVERSAL</p>
            <h3>Follow links with a visible budget</h3>
          </div>
          <span className="state-pill ready">CONSENT CHECKED PER URL</span>
        </div>
        <p className="muted">
          Start a persisted crawl from one indexed document. Depth is capped at
          5 and the document budget at 100; revoked consent stops pending work.
        </p>
        <div className="profile-row">
          <input
            aria-label="Crawl root document ID"
            placeholder="Root document ID (for example github:owner/repo)"
            value={crawlRootId}
            onChange={(event) => setCrawlRootId(event.target.value)}
          />
          <label>
            Depth
            <input
              aria-label="Crawl maximum depth"
              type="number"
              min="1"
              max="5"
              value={crawlDepth}
              onChange={(event) => setCrawlDepth(event.target.value)}
            />
          </label>
          <label>
            Documents
            <input
              aria-label="Crawl document budget"
              type="number"
              min="1"
              max="100"
              value={crawlBudget}
              onChange={(event) => setCrawlBudget(event.target.value)}
            />
          </label>
        </div>
        <button
          className="button primary"
          type="button"
          disabled={!crawlRootId.trim()}
          onClick={() =>
            void run(
              "start_reference_crawl",
              {
                vaultPath,
                sourceDocumentId: crawlRootId.trim(),
                maxDepth: Number(crawlDepth),
                maxDocuments: Number(crawlBudget),
                requestedAt: new Date().toISOString(),
              },
              (value: { queued: number; runId: string }) =>
                `Started crawl ${value.runId}; queued ${value.queued} consented links.`,
            )
          }
        >
          Start bounded crawl
        </button>
      </section>
      <section className="capture-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">LINKEDIN IMPORT</p>
            <h3>Bring your own export or permalink</h3>
          </div>
          <span className="state-pill needs-auth">API / EXPORT ONLY</span>
        </div>
        <p className="muted">
          Paste a permalink and the content you want to retain. ResearchLedger
          never opens, signs in to, or reads a LinkedIn browser session.
        </p>
        <div className="capture-actions">
          <input
            aria-label="LinkedIn permalink"
            placeholder="https://www.linkedin.com/posts/..."
            value={linkedinPermalink}
            onChange={(event) => setLinkedinPermalink(event.target.value)}
          />
          <textarea
            aria-label="LinkedIn content"
            placeholder="Paste the post content you want to keep"
            value={linkedinContent}
            onChange={(event) => setLinkedinContent(event.target.value)}
          />
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              void run(
                "import_linkedin_manual",
                { vaultPath, permalink: linkedinPermalink, content: linkedinContent },
                (value: ImportResult) =>
                  `Imported ${value.created + value.updated} LinkedIn posts.`,
              )
            }
          >
            Import manual LinkedIn source
          </button>
        </div>
      </section>
      <section className="capture-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">REDDIT SAVED POSTS</p>
            <h3>
              {redditState === "needs-auth"
                ? "Sign in once, capture locally"
                : "Reddit saved-posts connected"}
            </h3>
          </div>
          <span className={`state-pill ${redditState}`}>
            {redditState === "needs-auth"
              ? "USERNAME REQUIRED"
              : redditState === "capturing"
                ? "CAPTURING"
                : "READY"}
          </span>
        </div>
        <p className="muted">
          Persistent Chrome profile opens your saved-posts page. Profile path
          keeps the Reddit session in your browser so cookies never touch
          ResearchLedger.
        </p>
        <div className="profile-row">
          <input
            aria-label="Reddit username"
            placeholder="Your Reddit username (no /u/)"
            value={redditUsername}
            onChange={(event) => setRedditUsername(event.target.value)}
          />
          <input
            aria-label="Reddit browser profile"
            title={redditProfile || "Default profile"}
            placeholder="Browser profile path (optional)"
            value={redditProfile}
            onChange={(event) => setRedditProfile(event.target.value)}
          />
        </div>
        <div className="capture-actions">
          <button
            className="button primary"
            type="button"
            onClick={() => void captureReddit()}
            disabled={redditState === "capturing"}
          >
            Capture Reddit saved posts
          </button>
          <input
            aria-label="Reddit capture path"
            placeholder="/Users/you/captures/reddit.json"
            value={redditPath}
            onChange={(event) => setRedditPath(event.target.value)}
          />
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              void run(
                "import_reddit_capture",
                { vaultPath, capturePath: redditPath },
                (value: ImportResult) =>
                  `Imported ${value.created + value.updated} Reddit posts.`,
              )
            }
          >
            Import capture
          </button>
        </div>
      </section>
      <section className="capture-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">X BOOKMARKS</p>
            <h3>
              {xState === "needs-auth"
                ? "Sign in once, capture locally"
                : "X bookmarks connected"}
            </h3>
          </div>
          <span className={`state-pill ${xState}`}>
            {xState === "needs-auth"
              ? "AUTH REQUIRED"
              : xState === "capturing"
                ? "CAPTURING"
                : "READY"}
          </span>
        </div>
        <p className="muted">
          Persistent Chrome profile opens x.com/i/bookmarks. Profile path keeps
          the X session in your browser so MFA never touches ResearchLedger.
        </p>
        <div className="profile-row">
          <input
            aria-label="X browser profile"
            title={xProfile || "Default profile"}
            placeholder="Browser profile path (optional)"
            value={xProfile}
            onChange={(event) => setXProfile(event.target.value)}
          />
        </div>
        <div className="capture-actions">
          <button
            className="button primary"
            type="button"
            onClick={() => void captureX()}
            disabled={xState === "capturing"}
          >
            Capture X bookmarks
          </button>
          <input
            aria-label="X capture path"
            placeholder="/Users/you/captures/x.json"
            value={xPath}
            onChange={(event) => setXPath(event.target.value)}
          />
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              void run(
                "import_x_capture",
                { vaultPath, capturePath: xPath },
                (value: ImportResult) =>
                  `Imported ${value.created + value.updated} X bookmarks.`,
              )
            }
          >
            Import capture
          </button>
        </div>
      </section>
      <HackerNewsPanel
        vaultPath={vaultPath}
        setMessage={setMessage}
        hackernewsProfile={hackernewsProfile}
        setHackernewsProfile={setHackernewsProfile}
      />
      <section className="vault-strip">
        <div>
          <p className="eyebrow">VAULT</p>
          <strong>{vaultPath || "No local vault selected"}</strong>
          <span>
            {status
              ? `${status.documentCount} documents indexed`
              : "Choose a Markdown vault to begin"}
          </span>
        </div>
        <button
          className="button secondary"
          type="button"
          onClick={() => void chooseVault()}
        >
          Choose vault
        </button>
        <input
          aria-label="Vault path"
          placeholder="/Users/you/ResearchVault"
          title={vaultPath || "No vault selected"}
          value={vaultPath}
          onChange={(event) => setVaultPath(event.target.value)}
        />
      </section>
      <section className="search-panel" aria-label="Search">
        <input
          aria-label="Search research"
          placeholder="Search your ledger…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void search();
          }}
        />
        <button
          className="button secondary"
          type="button"
          onClick={() => void search()}
        >
          Search
        </button>
        <button
          className="button primary"
          type="button"
          onClick={() => void retrieve()}
          disabled={!vaultPath || !query.trim() || retrieving}
        >
          {retrieving ? "Building context…" : "Build cited context"}
        </button>
        {results.length > 0 && (
          <div className="results">
            {results.map((result) => (
              <article className="result" key={result.documentId}>
                <strong>{result.title}</strong>
                <p>
                  <HighlightedSnippet value={result.snippet} />
                </p>
              </article>
            ))}
          </div>
        )}
      </section>
      {retrievalContext && (
        <section className="retrieval-panel" aria-label="Cited retrieval context">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">RETRIEVAL CONTEXT</p>
              <h3>Evidence for “{retrievalContext.query}”</h3>
            </div>
            <span className={`state-pill ${retrievalContext.confidence.label}`}>
              {retrievalContext.confidence.label.toUpperCase()}
            </span>
          </div>
          <p className="retrieval-meta">
            {retrievalContext.coverage.cited} cited of {retrievalContext.coverage.retrieved} retrieved · {Math.round(retrievalContext.coverage.sourceUriRatio * 100)}% source-linked
          </p>
          <pre className="retrieval-context">{retrievalContext.context || "No evidence matched this query."}</pre>
          <div className="retrieval-citations">
            {retrievalContext.citations.map((citation) => (
              <a
                className="retrieval-citation"
                href={citation.sourceUri ?? undefined}
                key={citation.citationId}
                target={citation.sourceUri ? "_blank" : undefined}
                rel={citation.sourceUri ? "noreferrer" : undefined}
              >
                <strong>[{citation.citationId}] {citation.title}</strong>
                <span>{citation.sourceUri || "Local vault source"}</span>
              </a>
            ))}
          </div>
          <p className="retrieval-rationale">{retrievalContext.confidence.rationale}</p>
        </section>
      )}
      <section className="export-row">
        <span className="muted">GitHub imports use your authenticated local GitHub CLI.</span>
        <button
          className="button secondary"
          type="button"
          onClick={async () => {
            const destination = await open({
              directory: true,
              multiple: false,
              title: "Choose Markdown export folder",
              defaultPath: vaultPath || undefined,
            });
            if (typeof destination !== "string") {
              setMessage(
                "Markdown export canceled; no destination was selected.",
              );
              return;
            }
            await run(
              "export_obsidian",
              { vaultPath, destination },
              (count: number) =>
                `Exported ${count} Markdown documents to ${destination}.`,
            );
          }}
        >
          Export Markdown
        </button>
      </section>
      {message && (
        <p className="import-message" role="status">
          {message}
        </p>
      )}
    </>
  );
}

function Action({
  title,
  label,
  state,
  onClick,
  disabled,
}: {
  title: string;
  label: string;
  state: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <article className="action-card">
      <div>
        <strong>{title}</strong>
        <span>{state}</span>
      </div>
      <button
        className="button secondary"
        type="button"
        onClick={onClick}
        disabled={disabled}
      >
        {label}
      </button>
    </article>
  );
}
function WorkspaceView({
  title,
  eyebrow,
  description,
  command,
  vaultPath,
  render,
}: {
  title: string;
  eyebrow: string;
  description: string;
  command: string;
  vaultPath: string;
  render?: (data: any[]) => ReactNode;
}) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const load = async () => {
    if (!vaultPath) return;
    setLoading(true);
    try {
      setData(await invoke<any[]>(command, { vaultPath }));
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    if (vaultPath) void load();
  }, [vaultPath]);
  return (
    <section className="workspace-view">
      <div className="workspace-intro">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        <p className="muted">{description}</p>
        <button
          className="button secondary"
          type="button"
          onClick={() => void load()}
          disabled={!vaultPath || loading}
        >
          {loading ? "Refreshing…" : "Refresh view"}
        </button>
      </div>
      {render ? (
        render(data)
      ) : (
        <div className="data-surface">
          {data.length ? (
            data.map((item, index) => (
              <div className="data-row" key={item.id ?? index}>
                <strong>
                  {item.title ?? item.name ?? `Research item ${index + 1}`}
                </strong>
                <span>
                  {item.description ??
                    item.kind ??
                    item.sourceKind ??
                    "Indexed locally"}
                </span>
              </div>
            ))
          ) : (
            <EmptyState vaultPath={vaultPath} />
          )}
        </div>
      )}
    </section>
  );
}
function Library({ vaultPath }: { vaultPath: string }) {
  return <DetailedLibrary vaultPath={vaultPath} />;
}
function DetailedLibrary({ vaultPath }: { vaultPath: string }) {
  const [documents, setDocuments] = useState<
    Array<{
      id: string;
      title: string;
      sourceKind: string;
      sourceUri: string | null;
      tags: string[];
    }>
  >([]);
  const [selectedId, setSelectedId] = useState("");
  const [claims, setClaims] = useState<
    Array<{ claim: string; sourceUri: string | null; citationId: string }>
  >([]);
  const [loading, setLoading] = useState(false);
  const load = async () => {
    if (!vaultPath) return;
    setLoading(true);
    try {
      setDocuments(await invoke("list_document_summaries", { vaultPath }));
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, [vaultPath]);
  useEffect(() => {
    if (!vaultPath || !selectedId) {
      setClaims([]);
      return;
    }
    void invoke<
      Array<{ claim: string; sourceUri: string | null; citationId: string }>
    >("list_document_claims", { vaultPath, documentId: selectedId })
      .then(setClaims)
      .catch(() => setClaims([]));
  }, [vaultPath, selectedId]);
  return (
    <section className="workspace-view">
      <div className="workspace-intro">
        <p className="eyebrow">LIBRARY</p>
        <h3>Your indexed corpus</h3>
        <p className="muted">
          Select a document to inspect its persisted claims and source
          citations.
        </p>
        <button
          className="button secondary"
          type="button"
          onClick={() => void load()}
          disabled={!vaultPath || loading}
        >
          {loading ? "Refreshing…" : "Refresh view"}
        </button>
      </div>
      <div className="data-surface">
        {documents.length ? (
          documents.map((document) => (
            <button
              className={`data-row${selectedId === document.id ? " selected" : ""}`}
              key={document.id}
              type="button"
              onClick={() => setSelectedId(document.id)}
            >
              <strong>{document.title}</strong>
              <span>
                {document.sourceKind} · {document.tags.join(", ") || "untagged"}
              </span>
            </button>
          ))
        ) : (
          <EmptyState vaultPath={vaultPath} />
        )}
      </div>
      {selectedId && (
        <aside className="data-surface">
          <p className="eyebrow">CLAIMS / PROVENANCE</p>
          {claims.length ? (
            claims.map((claim, index) => (
              <div className="data-row" key={`${claim.citationId}-${index}`}>
                <strong>
                  [{claim.citationId}] {claim.claim}
                </strong>
                <span>{claim.sourceUri || "Local source"}</span>
              </div>
            ))
          ) : (
            <p className="muted">
              No claim records yet. Distill this source from Inbox.
            </p>
          )}
        </aside>
      )}
    </section>
  );
}
function Collections({ vaultPath }: { vaultPath: string }) {
  return (
    <WorkspaceView
      title="Working sets for active questions"
      eyebrow="COLLECTIONS"
      description="Collections are deliberate slices of the corpus. The view is ready for collection commands as they land."
      command="list_collections"
      vaultPath={vaultPath}
    />
  );
}
function Graph({ vaultPath }: { vaultPath: string }) {
  return (
    <WorkspaceView
      title="Connections worth following"
      eyebrow="GRAPH"
      description="A relationship surface for sources, distilled notes, and recurring themes."
      command="list_document_links"
      vaultPath={vaultPath}
      render={(data) => (
        <div className="graph-surface">
          {data.length ? (
            data.map((link, index) => (
              <div
                className="data-row"
                key={`${link.sourceDocumentId}-${link.targetUrl}-${index}`}
              >
                <strong>{link.sourceTitle}</strong>
                <span>
                  {link.relation} → {link.targetUrl}
                </span>
              </div>
            ))
          ) : (
            <EmptyState vaultPath={vaultPath} />
          )}
        </div>
      )}
    />
  );
}
function EmptyState({ vaultPath }: { vaultPath: string }) {
  return (
    <div className="empty-state">
      <span className="empty-orbit">+</span>
      <strong>
        {vaultPath ? "Nothing surfaced yet" : "Choose a vault to begin"}
      </strong>
      <p>
        {vaultPath
          ? "Run an import or distill pending sources in Inbox, then refresh this view."
          : "Your local vault is the source of truth for every workspace."}
      </p>
    </div>
  );
}
function HighlightedSnippet({ value }: { value: string }) {
  return value.split(/(<mark>|<\/mark>)/g).map((part, index) =>
    part === "<mark>" || part === "</mark>" || !part ? null : (
      (value
        .split(/(<mark>|<\/mark>)/g)
        .slice(0, index)
        .filter((item) => item === "<mark>").length %
        2 ===
        1) ? (
        <mark key={index}>{part}</mark>
      ) : (
        <span key={index}>{part}</span>
      )
    ),
  );
}
