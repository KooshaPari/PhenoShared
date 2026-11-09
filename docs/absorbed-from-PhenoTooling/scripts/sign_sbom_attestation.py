"""Sign-and-attach workflow for CycloneDX SBOMs.

Loads the generated CycloneDX JSON, builds an in-toto attestation
over its SHA-256, signs the attestation with cosign (keyless OIDC
by default, KMS if --kms-key is provided), and emits the signed
attestation as a release asset.

Usage:
    python sign_sbom_attestation.py \\
        --sbom crates/sbom-gen/docs/security/sbom.json \\
        --tag v0.2.0 \\
        --out .github/sbom-attestations/ \\
        [--kms-key awskms://...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_attestation(sbom_path: Path, tag: str) -> dict:
    """Build an in-toto attestation statement over the SBOM bytes.

    The predicate follows the SLSA provenance v1 schema but the
    subject is the SBOM digest rather than a build artifact. This
    makes the SBOM itself the verifiable artifact -- the SBOM can
    be re-fetched from upstream at any time and its signature
    remains meaningful as long as the bytes match.
    """
    digest = sha256_file(sbom_path)
    attestation = {
        "_type": "https://in-toto.io/Statement/v1",
        "predicateType": "https://slsa.dev/provenance/v1",
        "subject": [
            {
                "name": sbom_path.name,
                "digest": {"sha256": digest},
            }
        ],
        "predicate": {
            "buildDefinition": {
                "buildType": "https://github.com/kooshapari/phenotype-tooling/sbom-gen@v1",
                "externalParameters": {
                    "tag": tag,
                    "tool": "cargo run -p sbom-gen",
                },
                "internalParameters": {},
                "resolvedDependencies": [
                    {
                        "uri": f"git+https://github.com/KooshaPari/phenotype-tooling@refs/tags/{tag}",
                        "digest": {"gitCommit": tag},
                    }
                ],
            },
            "runDetails": {
                "builder": {
                    "id": "https://github.com/actions/runner",
                    "version": {"github-actions-runner": "stable"},
                },
                "invocation": {
                    "configSource": {
                        "uri": f"git+https://github.com/KooshaPari/phenotype-tooling@refs/tags/{tag}",
                        "digest": {"gitCommit": tag},
                    },
                    "arguments": {},
                    "environment": {},
                },
                "metadata": {
                    "buildStartedOn": datetime.now(timezone.utc).isoformat(),
                    "buildFinishedOn": datetime.now(timezone.utc).isoformat(),
                },
            },
        },
    }
    return attestation


def cosign_attest(statement: dict, out_path: Path, kms_key: str | None) -> int:
    """Invoke `cosign attest` against a temp statement file.

    Returns the cosign exit code. Writes the cosign-produced
    .intoto.jsonl signature to out_path.
    """
    tmp = out_path.with_suffix(".statement.intoto.jsonl")
    tmp.write_text(json.dumps(statement) + "\n", encoding="utf-8")
    cmd = [
        "cosign",
        "attest",
        "--yes",
        "--type",
        "slsaprovenance",
        "--predicate",
        str(tmp),
        "--output-signature",
        str(out_path),
        "--output-certificate",
        str(out_path.with_suffix(".cert")),
    ]
    if kms_key:
        cmd.extend(["--key", kms_key])
    else:
        cmd.append("--keyless")
    result = subprocess.run(cmd, capture_output=True, text=True)
    tmp.unlink(missing_ok=True)
    if result.returncode != 0:
        sys.stderr.write(f"cosign failed: {result.stderr}\n")
    return result.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--tag", type=str, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--kms-key", type=str, default=None)
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    attestation = build_attestation(args.sbom, args.tag)
    sig_path = args.out / f"sbom-{args.tag}.intoto.jsonl"

    rc = cosign_attest(attestation, sig_path, args.kms_key)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
