#!/usr/bin/env python3
"""Loopback-only CrossEncoder adapter for the ResearchLedger rerank contract.

The model directory is supplied explicitly so the app never downloads a model
implicitly and never sends document text off-device.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("RESEARCHLEDGER_RERANK_MODEL_PATH")
if not MODEL:
    print(
        "RESEARCHLEDGER_RERANK_MODEL_PATH must be set to a local model directory",
        file=sys.stderr,
    )
    raise SystemExit(2)

from sentence_transformers import CrossEncoder

PORT = int(os.environ.get("RESEARCHLEDGER_RERANK_PORT", "8082"))
encoder = CrossEncoder(MODEL, max_length=512, local_files_only=True)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ("/rerank", "/v1/rerank"):
            self.send_json(404, {"error": "rerank endpoint not found"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            self.send_json(400, {"error": "content-length must be an integer"})
            return
        if length < 0 or length > 1_000_000:
            self.send_json(400, {"error": "request body exceeds the 1 MB limit"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "request body must be valid JSON"})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "request JSON must be an object"})
            return
        query = payload.get("query")
        documents = payload.get("documents", payload.get("texts"))
        if not isinstance(query, str) or not query.strip():
            self.send_json(400, {"error": "query must be a non-empty string"})
            return
        if (
            not isinstance(documents, list)
            or not documents
            or any(not isinstance(document, str) for document in documents)
        ):
            self.send_json(400, {"error": "documents must be a non-empty list of strings"})
            return
        scores = encoder.predict([(query, document) for document in documents])
        results = [
            {"index": index, "relevance_score": float(score)}
            for index, score in enumerate(scores)
        ]
        results.sort(key=lambda item: (-item["relevance_score"], item["index"]))
        self.send_json(200, {"model": os.path.basename(MODEL), "results": results})

    def log_message(self, *_args):
        return


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
