#!/usr/bin/env node
// Build-time fetch of GitHub snapshots for Benchora landing page.
// Uses the GitHub API (not gh CLI). Set GITHUB_TOKEN env for higher rate limits.

import { writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = "KooshaPari/Benchora";
const DATA_DIR = resolve(__dirname, "..", "src", "data");

const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
const headers = {
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "benchora-landing-build",
};
if (token) headers.Authorization = `Bearer ${token}`;

async function fetchAll() {
  await mkdir(DATA_DIR, { recursive: true });

  const endpoints = [
    ["readme.html", `https://api.github.com/repos/${REPO}/readme`, "application/vnd.github.html+json"],
    ["repo.json", `https://api.github.com/repos/${REPO}`, "application/vnd.github+json"],
    ["releases.json", `https://api.github.com/repos/${REPO}/releases?per_page=5`, "application/vnd.github+json"],
  ];

  for (const [filename, url, accept] of endpoints) {
    const res = await fetch(url, { headers: { ...headers, Accept: accept } });
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

fetchAll().catch(err => {
  console.error(err);
  process.exit(1);
});
