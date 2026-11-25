#!/usr/bin/env python3
"""REST API for evaluation results. Uses only Python stdlib."""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional

# Data paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
EVAL_RESULTS_PATH = OUTPUT_DIR / "evaluation-results.json"
RUBRIC_PATH = BASE_DIR / "CONSOLIDATED_RUBRIC.json"


def load_json(path: Path) -> dict:
    """Load JSON from file."""
    with open(path, "r") as f:
        return json.load(f)


# Load data once at startup
eval_data = load_json(EVAL_RESULTS_PATH)
rubric_data = load_json(RUBRIC_PATH)


def get_products() -> dict:
    """Get all products with scores."""
    return {
        "evaluated_at": eval_data.get("evaluated_at"),
        "rubric_criteria_count": eval_data.get("rubric_criteria_count"),
        "products": eval_data.get("products", {}),
    }


def get_product(name: str) -> Optional[dict]:
    """Get single product detail."""
    products = eval_data.get("products", {})
    if name in products:
        return products[name]
    return None


def get_criteria() -> dict:
    """Get all criteria with statuses."""
    criteria_list = rubric_data.get("criteria", [])
    # Group by domain
    criteria_by_domain = {}
    for c in criteria_list:
        domain = c.get("domain", "unknown")
        if domain not in criteria_by_domain:
            criteria_by_domain[domain] = []
        criteria_by_domain[domain].append({
            "id": c.get("id"),
            "title": c.get("title"),
            "status": c.get("status"),
            "source": c.get("source"),
        })
    return {
        "total": len(criteria_list),
        "domains": rubric_data.get("domains", []),
        "by_domain": criteria_by_domain,
    }


def get_health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "products_count": len(eval_data.get("products", {})),
        "criteria_count": len(rubric_data.get("criteria", [])),
    }


class APIHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for API endpoints."""

    def do_GET(self):
        """Handle GET requests."""
        path = self.path.rstrip("/")

        # API routes
        if path == "/api/health":
            self._send_json(get_health())
        elif path == "/api/products":
            self._send_json(get_products())
        elif path.startswith("/api/products/"):
            name = path[len("/api/products/"):]
            product = get_product(name)
            if product:
                self._send_json(product)
            else:
                self._send_error(404, f"Product '{name}' not found")
        elif path == "/api/criteria":
            self._send_json(get_criteria())
        else:
            # Serve static files from output/
            self._serve_static(path)

    def _send_json(self, data: dict, status: int = 200):
        """Send JSON response with CORS headers."""
        response = json.dumps(data, indent=2)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(response.encode())

    def _send_error(self, status: int, message: str):
        """Send error response."""
        self._send_json({"error": message}, status)

    def _add_cors_headers(self):
        """Add CORS headers for cross-origin access."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_static(self, path: str):
        """Serve static files from output/ directory."""
        if path == "":
            path = "/dashboard.html"

        # Map path to output/ directory
        if path.startswith("/"):
            file_path = OUTPUT_DIR / path[1:]
        else:
            file_path = OUTPUT_DIR / path

        if file_path.exists() and file_path.is_file():
            content_type = self._get_content_type(file_path.suffix)
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self._add_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        else:
            self._send_error(404, f"File '{path}' not found")

    def _get_content_type(self, ext: str) -> str:
        """Get content type for file extension."""
        types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
        }
        return types.get(ext, "application/octet-stream")

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluation Results API Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), APIHandler)
    print(f"Starting API server on http://localhost:{args.port}")
    print(f"Serving static files from {OUTPUT_DIR}")
    print(f"API endpoints:")
    print(f"  GET /api/health")
    print(f"  GET /api/products")
    print(f"  GET /api/products/{{name}}")
    print(f"  GET /api/criteria")
    print(f"\nPress Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
