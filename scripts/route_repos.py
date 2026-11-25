#!/usr/bin/env python3
"""Propose an absorption route for a repository: app, library, or private data.

The rule from the operator: a full application goes to PhenoShared/apps/, a
library goes to PhenoShared/libs/, and private data or data-only content goes to
PhenoRegistry/repos/<name>/tree/.

That is a judgement, so this does not guess silently. It collects concrete
signals from the repository tree and prints them beside the proposal, so a wrong
route is visible before anything is moved.

Signals used:
  app     src-tauri/, electron/main, apps/, .svelte-kit, next.config, index.html,
          a Cargo [[bin]], a Go main package at root, Dockerfile with a server
  lib     src/lib.rs, [lib] in Cargo.toml, index.ts without a bin, no runtime entry
  data    no source files at all - only markdown, json, yaml, csv, images

Usage:
    python route_repos.py <repo> [repo ...]
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"

APP_PATHS = ("src-tauri/", "apps/", ".svelte-kit/", "next.config",
             "electron", "index.html", "tauri.conf.json")
LIB_PATHS = ("src/lib.rs", "lib/", "index.ts", "mod.ts")
DATA_EXT = (".md", ".json", ".yaml", ".yml", ".csv", ".txt", ".png", ".jpg",
            ".svg", ".toml", ".lock")
CODE_EXT = (".rs", ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".c", ".cpp",
            ".cs", ".java", ".kt", ".swift", ".rb", ".php", ".sh")


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


def api(path):
    code, out, err = sh(["gh", "api", path])
    if code != 0:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def inspect(repo):
    d = api("repos/%s/%s" % (OWNER, repo))
    if not d:
        return None
    ref = d["default_branch"]
    t = api("repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref))
    if not t or t.get("truncated"):
        return None
    paths = [e["path"] for e in t["tree"] if e.get("type") == "blob"]
    return {
        "repo": repo,
        # The raw API says "private"; "isPrivate" is the `gh repo list --json`
        # field name. Reading the wrong one made every repository report as
        # public, which matters because routing decides whether code is
        # published into PhenoShared.
        "private": bool(d.get("private")),
        "ref": ref,
        "files": len(paths),
        "paths": paths,
    }


def classify(info):
    paths = info["paths"]
    lower = [p.lower() for p in paths]
    code = [p for p in lower if p.endswith(CODE_EXT)]
    data = [p for p in lower if p.endswith(DATA_EXT)]

    app_hits = [p for p in lower if any(s in p for s in APP_PATHS)]
    lib_hits = [p for p in lower if any(p.endswith(s) or p == s for s in LIB_PATHS)]

    has_cargo = any(p.endswith("cargo.toml") for p in lower)
    has_pkg = any(p.endswith("package.json") for p in lower)
    has_pyproject = any(p.endswith("pyproject.toml") for p in lower)
    root_go = any(p.count("/") == 0 and p.endswith(".go") for p in lower)
    has_main = any(p.endswith("/main.rs") or p == "main.rs" for p in lower)

    # Framework signals are stronger than a manifest. Next.js, SvelteKit and a
    # root-level Python entry point all mean something is meant to be served or
    # run, even though each also ships a library manifest - which is why a
    # manifest-only test filed a 13,989-file Next.js app under libs/.
    next_app = any(("src/app/" in p or p.startswith("app/"))
                   and (p.endswith("page.tsx") or p.endswith("route.ts")
                        or p.endswith("layout.tsx"))
                   for p in lower)
    svelte_routes = any(p.endswith("+page.svelte") for p in lower)
    vite_app = any(p.endswith("vite.config.ts") or p.endswith("vite.config.js")
                   for p in lower)
    py_entry = any(p in ("main.py", "app.py", "server.py", "manage.py")
                   or p.endswith("/main.py") for p in lower)
    cli_name = any(w in info["repo"].lower()
                   for w in ("cli", "-app", "-server", "-monitor", "ops"))

    # A repository with no source at all is data.
    if not code:
        return ("data", "no source files: %d files, all documentation or data"
                % len(paths), (app_hits, lib_hits, code, data))

    # An application framework is decisive, not a score to be outvoted. Counting
    # library-ish paths let a 13,989-file Next.js app be filed as a library
    # because shadcn ships hundreds of index.ts files; a route directory cannot
    # mean anything except a served application.
    if next_app or svelte_routes:
        marks = []
        if next_app:
            marks.append("next app routes")
        if svelte_routes:
            marks.append("sveltekit routes")
        if py_entry:
            marks.append("python entry point")
        if root_go:
            marks.append("go main")
        if has_main:
            marks.append("main.rs")
        return ("app", "%s; %d code files" % (", ".join(marks), len(code)),
                (app_hits, lib_hits, code, data))

    # A clear runtime entry point makes it an application.
    app_score = (len(app_hits) + (4 if root_go else 0) + (2 if has_main else 0)
                 + (3 if vite_app else 0) + (4 if py_entry else 0)
                 + (1 if cli_name else 0))
    # Capped: a single library-ish filename convention should not outweigh a
    # runtime entry point just because the repository has many of them.
    lib_score = min(len(lib_hits), 5) + (2 if has_cargo else 0) + (1 if has_pkg else 0)

    if app_score >= 3 and app_score >= lib_score:
        marks = []
        if next_app:
            marks.append("next app routes")
        if svelte_routes:
            marks.append("sveltekit routes")
        if py_entry:
            marks.append("python entry point")
        if vite_app:
            marks.append("vite app")
        if root_go:
            marks.append("go main")
        if has_main:
            marks.append("main.rs")
        if not marks:
            marks = app_hits[:3] or ["root entry"]
        return ("app", "%s; %d code files" % (", ".join(marks), len(code)),
                (app_hits, lib_hits, code, data))

    if has_cargo or has_pkg or has_pyproject or lib_hits:
        return ("lib", "library manifest with no dominant runtime entry, "
                "%d code files" % len(code), (app_hits, lib_hits, code, data))

    return ("app", "code with no library manifest: %d code files" % len(code),
            (app_hits, lib_hits, code, data))


def route(kind, private):
    if kind == "data":
        return "PhenoRegistry/repos/%s/tree/"
    # Private code does not go to the public tree by accident. A private
    # repository whose content is code still lands in the registry tree unless
    # it is explicitly published, because publishing cannot be undone.
    if private:
        return "PhenoRegistry/repos/%s/tree/  (PRIVATE CODE - needs a publish decision)"
    if kind == "app":
        return "PhenoShared/apps/%s/"
    return "PhenoShared/libs/%s/"


def main():
    repos = sys.argv[1:]
    if not repos:
        print(__doc__)
        return 2

    rows = []
    for repo in repos:
        info = inspect(repo)
        if info is None:
            print("%-42s UNREADABLE (missing or truncated tree)" % repo)
            continue
        kind, why, _ = classify(info)
        dest = route(kind, info["private"]) % repo
        rows.append((repo, "priv" if info["private"] else "pub", info["files"],
                     kind, dest, why))

    print("%-42s %-5s %6s %-5s %-44s %s"
          % ("repo", "vis", "files", "kind", "destination", "why"))
    print("-" * 165)
    for r in rows:
        print("%-42s %-5s %6d %-5s %-44s %s"
              % (r[0][:42], r[1], r[2], r[3], r[4], r[5][:46]))
    print()
    counts = {}
    for r in rows:
        counts[r[3]] = counts.get(r[3], 0) + 1
    print("app %d, lib %d, data %d" % (counts.get("app", 0), counts.get("lib", 0),
                                       counts.get("data", 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
