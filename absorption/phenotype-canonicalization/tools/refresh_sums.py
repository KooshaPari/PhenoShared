"""Refresh the SHA256SUMS entries for files that were intentionally rewritten.

Only the two SOURCE-INDEX paths are re-hashed; every other entry is left
byte-identical so unrelated checksums cannot silently drift.
"""

import hashlib
import sys

ROOT = "/Users/kooshapari/CodeProjects/docs/phenotype-canonicalization"
SUMS = f"{ROOT}/SHA256SUMS"
TARGETS = {"SOURCE-INDEX.md", "SOURCE-INDEX-DETAIL.md"}


def digest(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    updated = 0
    out = []
    for line in open(SUMS).read().split("\n"):
        if not line.strip():
            out.append(line)
            continue
        current_hash, _, name = line.partition("  ")
        if name in TARGETS:
            new_hash = digest(f"{ROOT}/{name}")
            if new_hash != current_hash:
                print(f"{name}: {current_hash[:12]} -> {new_hash[:12]}")
                updated += 1
            out.append(f"{new_hash}  {name}")
        else:
            out.append(line)
    with open(SUMS, "w") as handle:
        handle.write("\n".join(out))
    print(f"updated {updated} entr(ies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
