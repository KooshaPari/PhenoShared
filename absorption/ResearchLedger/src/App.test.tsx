/** @vitest-environment jsdom */

import "@testing-library/jest-dom";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const { invokeMock, openMock } = vi.hoisted(() => ({
  invokeMock: vi.fn(),
  openMock: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: openMock }));

function resetTauriMocks() {
  invokeMock.mockReset().mockResolvedValue({ selected: false, path: null, documentCount: 0 });
  openMock.mockReset().mockResolvedValue(null);
}

async function renderApp() {
  render(<App />);
  await waitFor(() =>
    expect(invokeMock).toHaveBeenCalledWith("get_vault_status", { vaultPath: null }),
  );
}

beforeEach(() => {
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: vi.fn(() => null), setItem: vi.fn(), removeItem: vi.fn() },
  });
});

describe("ResearchLedger shell", () => {
  it("loads persisted filesystem preferences through the native command, never browser storage", async () => {
    resetTauriMocks();
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      get() {
        throw new Error("browser storage must not receive local filesystem paths");
      },
    });
    invokeMock.mockImplementation((command: string) => {
      if (command === "load_local_preferences") {
        return Promise.resolve({
          vaultPath: "/tmp/research-vault",
          hackernewsProfile: "/tmp/hn-profile",
          redditProfile: "/tmp/reddit-profile",
          xProfile: "/tmp/x-profile",
        });
      }
      if (command === "get_vault_status") {
        return Promise.resolve({ selected: true, path: "/tmp/research-vault", documentCount: 0 });
      }
      return Promise.resolve([]);
    });

    render(<App />);

    await waitFor(() =>
      expect(invokeMock).toHaveBeenCalledWith("load_local_preferences"),
    );
    expect(await screen.findByRole("textbox", { name: "Vault path" })).toHaveValue(
      "/tmp/research-vault",
    );
    expect(screen.getByRole("textbox", { name: "Hacker News browser profile" })).toHaveValue(
      "/tmp/hn-profile",
    );
    expect(screen.getByRole("textbox", { name: "Reddit browser profile" })).toHaveValue(
      "/tmp/reddit-profile",
    );
    expect(screen.getByRole("textbox", { name: "X browser profile" })).toHaveValue(
      "/tmp/x-profile",
    );
  });

  it("debounces preference writes and never rewrites hydrated values", async () => {
    resetTauriMocks();
    invokeMock.mockImplementation((command: string) => {
      if (command === "load_local_preferences") {
        return Promise.resolve({
          vaultPath: "/tmp/research-vault",
          hackernewsProfile: "/tmp/hn-profile",
          redditProfile: "/tmp/reddit-profile",
          xProfile: "/tmp/x-profile",
        });
      }
      return Promise.resolve({ selected: false, path: null, documentCount: 0 });
    });

    render(<App />);
    await screen.findByRole("textbox", { name: "Vault path" });
    await waitFor(() => expect(invokeMock).toHaveBeenCalledWith("load_local_preferences"));
    expect(invokeMock).not.toHaveBeenCalledWith("save_local_preferences", expect.anything());
    const callCountBeforeTyping = invokeMock.mock.calls.length;

    vi.useFakeTimers();
    try {
      const profile = screen.getByRole("textbox", { name: "Hacker News browser profile" });
      fireEvent.change(profile, { target: { value: "/tmp/hn-a" } });
      fireEvent.change(profile, { target: { value: "/tmp/hn-final" } });
      expect(invokeMock).not.toHaveBeenCalledWith("save_local_preferences", expect.anything());

      await act(async () => {
        vi.advanceTimersByTime(300);
      });
      expect(invokeMock).toHaveBeenCalledTimes(callCountBeforeTyping + 1);
      expect(invokeMock).toHaveBeenLastCalledWith("save_local_preferences", {
        preferences: {
          vaultPath: "/tmp/research-vault",
          hackernewsProfile: "/tmp/hn-final",
          redditProfile: "/tmp/reddit-profile",
          xProfile: "/tmp/x-profile",
        },
      });
    } finally {
      vi.useRealTimers();
    }
  });

  it("uses one Rust-owned authenticated GitHub import without exposing a token", async () => {
    resetTauriMocks();
    invokeMock.mockImplementation((command: string) => {
      if (command === "import_github_from_gh") {
        return Promise.resolve({ created: 3, updated: 0, unchanged: 0, failed: 0 });
      }
      return Promise.resolve({ selected: false, path: null, documentCount: 0 });
    });
    render(<App />);
    fireEvent.change(screen.getByRole("textbox", { name: "Vault path" }), {
      target: { value: "/tmp/research-vault" },
    });

    expect(screen.queryByRole("textbox", { name: "GitHub token" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use authenticated gh token" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Import starred repos" }));

    await waitFor(() =>
      expect(invokeMock).toHaveBeenCalledWith("import_github_from_gh", {
        vaultPath: "/tmp/research-vault",
      }),
    );
    expect(invokeMock).not.toHaveBeenCalledWith("github_token_from_gh");
    expect(invokeMock).not.toHaveBeenCalledWith("github_device_poll", expect.anything());
  });

  it("offers only manual LinkedIn permalink/content ingestion", async () => {
    resetTauriMocks();
    await renderApp();

    expect(screen.getByText("LINKEDIN IMPORT")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "LinkedIn permalink" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "LinkedIn content" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import manual LinkedIn source" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Capture reactions in browser" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open LinkedIn sign-in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "LinkedIn browser profile" })).not.toBeInTheDocument();
  });


  it("uses a directory picker before exporting Markdown", async () => {
    resetTauriMocks();
    openMock.mockResolvedValue("/tmp/researchledger-export");
    render(<App />);
    fireEvent.change(screen.getByRole("textbox", { name: "Vault path" }), { target: { value: "/tmp/research-vault" } });
    fireEvent.click(screen.getByRole("button", { name: "Export Markdown" }));
    await waitFor(() => expect(invokeMock).toHaveBeenCalledWith("export_obsidian", { vaultPath: "/tmp/research-vault", destination: "/tmp/researchledger-export" }));
    expect(openMock).toHaveBeenCalledWith(expect.objectContaining({ directory: true, title: "Choose Markdown export folder" }));
  });

  it("shows the local-first vault setup", async () => {
    await renderApp();
    expect(screen.getByRole("heading", { name: "ResearchLedger" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose vault" })).toBeInTheDocument();
  });

  it("switches accessible primary workspaces", async () => {
    await renderApp();
    fireEvent.click(screen.getByRole("tab", { name: /Library/ }));
    expect(screen.getByRole("tab", { name: /Library/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Your indexed corpus");
    expect(screen.queryByRole("button", { name: "Import GitHub stars" })).not.toBeInTheDocument();
  });


  it("exposes a Hacker News saved-stories capture pathway", async () => {
    await renderApp();
    expect(screen.getByText("HACKER NEWS CONNECTION")).toBeInTheDocument();
    expect(screen.queryByText("Hacker News")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Hacker News sign-in" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Capture saved stories in browser" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Hacker News username/ })).toBeInTheDocument();
  });

  it("requires a vault before starting a browser capture", async () => {
    resetTauriMocks();
    await renderApp();

    fireEvent.click(screen.getByRole("button", { name: "Capture saved stories in browser" }));

    await waitFor(() =>
      expect(screen.getByText("Select a vault before running a source action.")).toBeInTheDocument(),
    );
    expect(invokeMock).not.toHaveBeenCalledWith(
      "capture_hackernews_browser",
      expect.anything(),
    );
  });

  it("renders the consent-safe source actions", async () => {
    await renderApp();
    const connectButtons = screen.getAllByRole("button", { name: "Connect browser" });
    expect(connectButtons.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: "Import starred repos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fetch linked sources" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Distill pending notes" })).toBeInTheDocument();
  });

  it("starts a bounded reference crawl with explicit depth and budget", async () => {
    resetTauriMocks();
    invokeMock.mockImplementation((command: string) => {
      if (command === "start_reference_crawl") {
        return Promise.resolve({ runId: "crawl:test", queued: 2 });
      }
      return Promise.resolve({ selected: false, path: null, documentCount: 0 });
    });
    await renderApp();
    fireEvent.change(screen.getByRole("textbox", { name: "Vault path" }), {
      target: { value: "/tmp/research-vault" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Crawl root document ID" }), {
      target: { value: "github:octo/repo" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Crawl maximum depth" }), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Crawl document budget" }), {
      target: { value: "20" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start bounded crawl" }));
    await waitFor(() =>
      expect(invokeMock).toHaveBeenCalledWith(
        "start_reference_crawl",
        expect.objectContaining({
          vaultPath: "/tmp/research-vault",
          sourceDocumentId: "github:octo/repo",
          maxDepth: 3,
          maxDocuments: 20,
        }),
      ),
    );
  });

  it("renders search snippets as readable plain text with mark emphasis", async () => {
    resetTauriMocks();
    invokeMock.mockImplementation((command: string) => {
      if (command === "search_documents") {
        return Promise.resolve([
          {
            documentId: "doc-1",
            title: "LinkedIn sample",
            snippet: "Alpha <mark>beta</mark> gamma",
            sourceUri: null,
          },
        ]);
      }
      return Promise.resolve({ selected: false, path: null, documentCount: 0 });
    });
    render(<App />);
    fireEvent.change(screen.getByRole("textbox", { name: "Vault path" }), {
      target: { value: "/tmp/research-vault" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Search research" }), {
      target: { value: "alpha" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      const results = document.querySelector(".results");
      expect(results).not.toBeNull();
      expect(results?.textContent).toContain("Alpha beta gamma");
      expect(results?.querySelectorAll("article mark").length).toBeGreaterThanOrEqual(1);
      expect(results?.querySelector("article mark")?.textContent).toBe("beta");
    });
  });

  it("builds a persisted cited context with coverage metadata", async () => {
    resetTauriMocks();
    invokeMock.mockImplementation((command: string) => {
      if (command === "retrieve_context") {
        return Promise.resolve({
          query: "local vault",
          context: "[1] Local vault\nA local vault remains reviewable.",
          citations: [
            {
              citationId: "1",
              documentId: "doc-1",
              title: "Local vault",
              sourceUri: "https://example.com/vault",
              snippet: "A local vault remains reviewable.",
            },
          ],
          coverage: {
            retrieved: 1,
            cited: 1,
            withSourceUri: 1,
            sourceUriRatio: 1,
          },
          confidence: {
            score: 0.5,
            label: "limited",
            rationale: "1/1 cited results retain source URIs.",
          },
        });
      }
      return Promise.resolve({ selected: false, path: null, documentCount: 0 });
    });
    render(<App />);
    fireEvent.change(screen.getByRole("textbox", { name: "Vault path" }), {
      target: { value: "/tmp/research-vault" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Search research" }), {
      target: { value: "local vault" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Build cited context" }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: "Cited retrieval context" })).toBeInTheDocument();
    });
    expect(screen.getByText("1 cited of 1 retrieved · 100% source-linked")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /\[1\] Local vault/ })).toHaveAttribute(
      "href",
      "https://example.com/vault",
    );
    expect(invokeMock).toHaveBeenCalledWith("retrieve_context", {
      vaultPath: "/tmp/research-vault",
      query: "local vault",
      limit: 8,
    });
  });
});
