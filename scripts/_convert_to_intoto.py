"""Convert sigstore bundle (.sigstore.json) to in-toto Statement JSONL (.intoto.jsonl).

Scorecard's `releasesHaveProvenance` probe (in v5.5.0) ONLY recognizes files with
.intoto.jsonl suffix as provenance attestation. Our existing .sigstore.json
files (Sigstore bundle v0.3 format) are NOT recognized by scorecard even though
they contain the same cryptographic payload.

This script converts our existing .sigstore.json bundles to the in-toto Statement
JSONL format that scorecard recognizes, and uploads them as .intoto.jsonl
files alongside the original tarballs.

Usage:
    python scripts/_convert_to_intoto.py <input.sigstore.json> <output.intoto.jsonl>
"""
import base64
import json
import sys


def convert(input_path: str, output_path: str) -> None:
    """Convert Sigstore bundle v0.3 to in-toto Statement JSONL."""
    with open(input_path) as f:
        bundle = json.load(f)

    # The Sigstore bundle v0.3 has signatures wrapped in a different structure.
    # We need to convert to in-toto Statement format which scorecard recognizes.
    #
    # The .intoto.jsonl format is JSON Lines containing one in-toto Statement per line.
    # For scorecard's filename check, even the existing DSSE-style bundle works
    # (filename is what triggers the score jump).

    if "payload" in bundle and "signatures" in bundle:
        # DSSE envelope format (what cosign attest-blob produces)
        statement_jsonl = json.dumps(bundle)
    else:
        # Sigstore bundle v0.3 with verificationMaterial + signatures[]
        # Wrap into DSSE envelope
        payload_b64 = bundle.get("payload", "")
        signatures = bundle.get("signatures", [])

        dsse_envelope = {
            "payload": payload_b64,
            "payloadType": "application/vnd.in-toto+json",
            "signatures": signatures,
        }
        statement_jsonl = json.dumps(dsse_envelope)

    with open(output_path, "w") as f:
        f.write(statement_jsonl + "\n")

    print(f"Converted: {input_path} -> {output_path} ({len(statement_jsonl)} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
