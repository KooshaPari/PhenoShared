"""Preserve a fork's complete ref set in the private registry.

The `zz-*` dependency forks cannot be judged by their default branch. Several
have an inherited `master` that is identical to upstream while the actual work
lives on `main`, so any "diff the default branch" approach either exports an
empty diff or exports the wrong branch's content. Guessing which branch was
meant is not something a tool should do.

So preserve every ref. Identity is the proof: after the push, each ref name and
tip sha in the registry must match the source exactly. That needs no reasoning
about branches at all, and nothing can be missed.

    python scripts/preserve_refs.py zz-aa-dep-UnityDoorstop
"""

from __future__ import annotations

import sys

sys.path.insert(0, r"C:\Users\koosh\PhenoShared\scripts")
import prepare_deletion as pd

OWNER = "KooshaPari"
REGISTRY = "PhenoRegistry"


def source_refs(repo: str) -> dict[str, str]:
    # --refs drops the peeled `^{}` entries that annotated tags also report, so
    # the expected set contains real refs only and can be compared directly.
    code, out, err = pd.sh(["git", "ls-remote", "--refs",
                            "https://github.com/%s/%s.git" % (OWNER, repo)])
    if code != 0:
        raise RuntimeError("ls-remote failed: %s" % err.decode("utf-8", "replace")[:200])
    refs = {}
    for line in out.decode("utf-8", "replace").splitlines():
        sha, _, name = line.partition("\t")
        # Every namespace, not just heads and tags. Preservation pushes the
        # whole ref graph, so filtering the expectation to heads and tags made
        # the comparison report a complete push as a failure: the registry had
        # 1340 refs while the expectation held only the 869 heads and tags, and
        # the difference showed up as 471 unexplained extras.
        if name.startswith("refs/"):
            refs[name] = sha
    return refs


def registry_refs(repo: str) -> dict[str, str]:
    """Refs already preserved for this repository, keyed like source refs."""
    code, out, _ = pd.sh(["git", "ls-remote", "--refs",
                          "https://github.com/%s/%s.git" % (OWNER, REGISTRY),
                          "refs/preserved/%s/*" % repo])
    refs = {}
    for line in out.decode("utf-8", "replace").splitlines():
        sha, _, name = line.partition("\t")
        refs[name.replace("refs/preserved/%s/" % repo, "refs/")] = sha
    return refs


def main() -> int:
    repos = sys.argv[1:]
    if not repos:
        print("give repo names")
        return 2

    failures = 0
    for repo in repos:
        print("== %s" % repo)
        try:
            want = source_refs(repo)
        except RuntimeError as exc:
            print("   REFUSED  %s" % exc)
            failures += 1
            continue

        # Clear leftovers before preserving. A previous run may have kept a ref
        # the source does not have, for example an upstream branch pulled in by
        # `gh repo clone`; a leftover misrepresents the fork, and it would also
        # make the preservation's own equality check fail.
        existing = registry_refs(repo)
        stale = sorted(set(existing) - set(want))
        for name in stale:
            pd.sh(["gh", "api", "--method", "DELETE",
                   "repos/%s/%s/git/refs/preserved/%s/%s"
                   % (OWNER, REGISTRY, repo, name[len("refs/"):])])
        if stale:
            print("   cleared    %d stale refs: %s" % (len(stale), ", ".join(stale)))

        try:
            ok, detail = pd.store_history_as_refs(REGISTRY, OWNER, repo)
        except Exception as exc:  # noqa: BLE001 - report, do not abort the batch
            print("   REFUSED  crash: %s" % exc)
            failures += 1
            continue
        if not ok:
            print("   REFUSED  %s" % detail)
            failures += 1
            continue

        got = registry_refs(repo)
        if got != want:
            missing = sorted(set(want) - set(got))
            differ = sorted(k for k in set(want) & set(got) if want[k] != got[k])
            print("   REFUSED  ref mismatch: %d missing, %d differing"
                  % (len(missing), len(differ)))
            failures += 1
            continue

        print("   preserved  %d refs identical, %s" % (len(want), detail))
        print("   DELETE-AUTHORISED %s" % repo)

    print()
    print("preserved %d, blocked %d" % (len(repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
