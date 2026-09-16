#!/usr/bin/env node
// Build-time fetch of GitHub snapshots for Phenokits landing page.
// Uses the GitHub API (not gh CLI). Set GITHUB_TOKEN env for higher rate limits.

import { writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const __filename = fileURLToPath(import.meta.url);
const __isMain = resolve(process.argv[1] || "") === __filename;
const REPO = "KooshaPari/Phenokits";
const DATA_DIR = resolve(__dirname, "..", "src", "data");

// Retry constants
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 500;
const REQUEST_TIMEOUT_MS = 15_000;

const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
const headers = {
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "phenokits-landing-build",
};
if (token) headers.Authorization = `Bearer ${token}`;

/**
 * Fetch with bounded retry, exponential backoff + jitter, and AbortSignal timeout.
 * Exported for testability.
 */
export async function fetchWithRetry(url, fetchOpts = {}, retries = MAX_RETRIES) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ac = new AbortController();
    const timeoutId = setTimeout(() => ac.abort(), REQUEST_TIMEOUT_MS);
    try {
      const res = await fetch(url, { ...fetchOpts, signal: ac.signal });
      return res;
    } catch (err) {
      lastErr = err;
      if (attempt < retries) {
        const delay = Math.min(BASE_DELAY_MS * 2 ** attempt + Math.random() * 200, 4000);
        console.warn(`[retry] ${url} attempt ${attempt + 1} failed: ${err.message}, retrying in ${delay}ms`);
        await new Promise((r) => setTimeout(r, delay));
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }
  throw lastErr;
}

async function fetchAll() {
  await mkdir(DATA_DIR, { recursive: true });

  const endpoints = [
    ["readme.html", `https://api.github.com/repos/${REPO}/readme`, "application/vnd.github.html+json"],
    ["repo.json", `https://api.github.com/repos/${REPO}`, "application/vnd.github+json"],
    ["releases.json", `https://api.github.com/repos/${REPO}/releases?per_page=5`, "application/vnd.github+json"],
  ];

  for (const [filename, url, accept] of endpoints) {
    const res = await fetchWithRetry(url, { headers: { ...headers, Accept: accept } });
    if (res.ok) {
      const text = await res.text();
      await writeFile(resolve(DATA_DIR, filename), text);
      console.log(`[fetch] ${filename} OK`);
    } else {
      console.error(`[fetch] ${filename} FAILED: ${res.status} ${res.statusText}`);
    }
  }

  console.log(`[fetch] refreshed snapshots in ${DATA_DIR}`);
}

if (__isMain) {
  fetchAll().catch(err => {
    console.error(err);
    process.exit(1);
  });
}
