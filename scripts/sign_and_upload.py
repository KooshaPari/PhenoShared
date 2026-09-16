#!/usr/bin/env python3
"""Sign a local tarball with cosign local key and upload to GitHub Release.
Requires cosign 2.x on PATH. Designed for use via Tailscale SSH from Windows."""
import base64
import hashlib
import os
import subprocess
import sys
import tarfile

EXCLUDE_PATH_SUBSTRINGS = (
    "/.git/", "/.venv/", "/__pycache__/", "/.pytest_cache/",
    "/.ruff_cache/", "/.mypy_cache/", "/htmlcov/",
    "/dist/", "/eval/results/", "/logs/", "/.zig-cache/",
    "/zig-out/", "/rust/target/", "/state/wheels/",
    "/.sandbox/", "qwen3_5_kernel",
)

EXCLUDE_FILES = {".coverage", ".DS_Store"}

def make_tarball(src_dir: str, out_path: str) -> int:
    count = 0
    with tarfile.open(out_path, "w:gz") as tf:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f in EXCLUDE_FILES or f.endswith(".pyc"):
                    continue
                fp = os.path.relpath(os.path.join(root, f), src_dir)
                fp = fp.replace(os.sep, "/")
                if any(ex in "/" + fp for ex in EXCLUDE_PATH_SUBSTRINGS):
                    continue
                tf.add(os.path.join(root, f), arcname=fp)
                count += 1
    return count

def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "v0.41-pheno-harness-summit"
    repo_dir = os.getcwd()
    tar_name = f"pheno-harness-{tag}.tar.gz"
    tar_path = os.path.join(repo_dir, tar_name)
    sig_path = tar_path + ".sig"
    cert_path = tar_path + ".cert"
    sha_path = tar_path + ".sha256"
    key_prefix = os.path.join(os.path.expanduser("~"), "cosign_release")

    # 1. Build tarball
    print(f"[1/5] Building {tar_name}...")
    n = make_tarball(repo_dir, tar_path)
    print(f"      {n} files, {os.path.getsize(tar_path)//1024} KB")

    # 2. Compute SHA256
    print(f"[2/5] SHA256...")
    h = hashlib.sha256()
    with open(tar_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    digest = h.hexdigest()
    with open(sha_path, "w") as fh:
        fh.write(f"{digest}  {tar_name}\n")
    print(f"      {digest}")

    # 3. Sign with cosign
    print(f"[3/5] Signing with cosign local key...")
    password = os.environ.get("COSIGN_PASSWORD", "test-password")
    env = os.environ.copy()
    env["COSIGN_PASSWORD"] = password
    # cosign 2.x: --tlog-upload=false conflicts with default signing-config
    # Use explicit no-tlog config via stdin
    subprocess.run(
        ["cosign", "sign-blob",
         "--key", key_prefix + ".key",
         "--output-signature", sig_path,
         "--output-certificate", cert_path,
         "--yes",
         tar_path],
        check=True, env=env,
    )
    print(f"      signature: {os.path.getsize(sig_path)} B")
    print(f"      cert: {os.path.getsize(cert_path)} B")

    # 4. Upload to GitHub Release
    print(f"[4/5] Uploading to GitHub Release {tag}...")
    for path in [tar_path, sig_path, cert_path, sha_path]:
        subprocess.run(
            ["gh", "release", "upload", tag, path,
             "--repo", "<REDACTED>/pheno-harness",
             "--clobber"],
            check=True,
        )
        print(f"      uploaded: {os.path.basename(path)}")

    # 5. Cleanup
    print(f"[5/5] Cleaning up...")
    os.remove(tar_path)
    print("DONE")

if __name__ == "__main__":
    main()
