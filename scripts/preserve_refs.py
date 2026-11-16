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

        # Quarantine leftovers before preserving, never delete them.
        #
        # A previous run may hold a ref the source no longer has. That happens
        # two ways, and they are not equivalent:
        #
        #   * an inherited branch pulled in by `gh repo clone`, which really
        #     does misrepresent the fork; and
        #   * a branch the source deleted after this preservation captured it.
        #
        # The first is noise. The second is the only remaining record of that
        # branch, because the source has already thrown it away. Deleting both
        # is a data-loss bug: re-preserving host-ops destroyed 27 captured
        # branches that way before this was noticed.
        #
        # So move them aside under refs/superseded/ instead. That keeps
        # refs/preserved/<repo>/* exactly equal to the source, which is what the
        # equality check needs, without discarding anything.
        existing = registry_refs(repo)
        stale = sorted(set(existing) - set(want))
        quarantined = 0
        for name in stale:
            sha = existing[name]
            # Create the superseded ref first, then remove the preserved one, so
            # an interruption leaves a duplicate rather than a gap. Both return
            # codes are checked: an ignored failure here silently deletes the
            # only copy, which is the exact bug this whole block exists to undo.
            code, _, err = pd.sh(["gh", "api", "--method", "POST",
                                  "repos/%s/%s/git/refs" % (OWNER, REGISTRY),
                                  "-f", "ref=refs/superseded/%s/%s"
                                  % (repo, name[len("refs/"):]),
                                  "-f", "sha=%s" % sha])
            if code != 0:
                print("   KEPT      could not quarantine %s: %s"
                      % (name, err.decode("utf-8", "replace").strip()[:90]))
                continue
            code, _, err = pd.sh(["gh", "api", "--method", "DELETE",
                                  "repos/%s/%s/git/refs/preserved/%s/%s"
                                  % (OWNER, REGISTRY, repo,
                                     name[len("refs/"):])])
            if code != 0:
                print("   DUPLICATE %s copied to superseded but not removed: %s"
                      % (name, err.decode("utf-8", "replace").strip()[:90]))
                continue
            quarantined += 1
        if stale:
            print("   superseded %d/%d stale refs under refs/superseded/%s/"
                  % (quarantined, len(stale), repo))

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

        # The source is live and may be pushed to while this runs, so a ref can
        # appear after `want` was read, and a branch deleted on the source after
        # the push leaves the registry holding a ref the source no longer has.
        # Only a ref the source has and the registry lacks is a real failure:
        # that one would be lost by deleting the source. Registry-only refs are
        # preserved history and are kept.
        got = registry_refs(repo)
        missing = sorted(set(want) - set(got))
        differ = sorted(k for k in set(want) & set(got) if want[k] != got[k])
        extra = sorted(set(got) - set(want))
        if missing or differ:
            print("   REFUSED  ref mismatch: %d missing, %d differing"
                  % (len(missing), len(differ)))
            for k in missing[:5]:
                print("      MISSING %s" % k)
            for k in differ[:5]:
                print("      DIFFER  %s" % k)
            failures += 1
            continue

        note = ""
        if extra:
            note = " (%d registry-only kept)" % len(extra)
        print("   preserved  %d refs verified, %s%s" % (len(want), detail, note))
        print("   DELETE-AUTHORISED %s" % repo)

    print()
    print("preserved %d, blocked %d" % (len(repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
