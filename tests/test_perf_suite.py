import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from perf.resources import ResourceSampler
from perf.streaming import nonstream_chat, parse_sse, stream_chat
from perf.sweep import run_sweep


class PerfSuiteTests(unittest.TestCase):
    def test_sse_timing_and_usage(self):
        events = [
            b'data: {"choices":[{"delta":{"content":"hello"}}]}\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            b'data: {"choices":[],"usage":{"completion_tokens":2}}\n',
            b"data: [DONE]\n",
        ]
        result = parse_sse(events, started=0.0)
        self.assertEqual(result["completion"], "hello world")
        self.assertEqual(result["completion_tokens"], 2)
        self.assertEqual(result["measurement_quality"], "stream_chunk_proxy")

    def test_sweep_runs_parallel_levels(self):
        def call(task):
            return {"elapsed_ms": 2.0, "completion_tokens": 4}

        result = run_sweep(call, [{"prompt": "x"}] * 4, [1, 2], warmup=1)
        self.assertEqual([level["request_count"] for level in result["levels"]], [4, 4])
        self.assertEqual(result["levels"][0]["latency_ms_p95"], 2.0)

    def test_sweep_preserves_caller_failures_and_warmups(self):
        def call(task):
            if task.get("fail"):
                raise RuntimeError("expected")
            return {"elapsed_ms": 1.0, "completion_tokens": 1}

        result = run_sweep(call, [{"fail": False}, {"fail": True}], [1], warmup=1)
        self.assertEqual(result["warmup"]["error_count"], 0)
        self.assertEqual(result["levels"][0]["error_count"], 1)

    def test_stream_chat_normalizes_v1_and_sends_auth(self):
        seen = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                seen["path"] = self.path
                seen["auth"] = self.headers.get("Authorization")
                payload = (
                    b'data: {"choices":[{"delta":{"content":"ok"}}]}\r\n\r\n'
                    b"data: [DONE]\r\n\r\n"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
                self.wfile.flush()

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = stream_chat(
                f"http://127.0.0.1:{server.server_port}/v1",
                "m",
                "p",
                4,
                0.0,
                5.0,
                "test",
            )
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
        self.assertNotIn("error", result)
        self.assertEqual(seen, {"path": "/v1/chat/completions", "auth": "Bearer test"})

    def test_nonstream_chat_reports_total_latency_proxy_and_usage(self):
        seen = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                seen["path"] = self.path
                seen["auth"] = self.headers.get("Authorization")
                request = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                seen["stream"] = request.get("stream")
                payload = json.dumps(
                    {
                        "choices": [{"message": {"content": "ok"}}],
                        "usage": {
                            "prompt_tokens": 3,
                            "completion_tokens": 2,
                            "total_tokens": 5,
                        },
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = nonstream_chat(
                f"http://127.0.0.1:{server.server_port}/v1",
                "m",
                "p",
                4,
                0.0,
                5.0,
                "test",
            )
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
        self.assertNotIn("error", result)
        self.assertEqual(
            seen,
            {"path": "/v1/chat/completions", "auth": "Bearer test", "stream": False},
        )
        self.assertEqual(result["completion"], "ok")
        self.assertEqual(result["completion_tokens"], 2)
        self.assertEqual(result["prompt_tokens"], 3)
        self.assertEqual(result["total_tokens"], 5)
        self.assertEqual(result["itl_ms"], [])
        self.assertEqual(
            result["measurement_quality"], "non_streaming_total_latency_proxy"
        )
        self.assertGreaterEqual(result["elapsed_ms"], 0.0)

    def test_resource_probe_overhead_is_finite_without_gpu(self):
        sampler = ResourceSampler(interval=0.1, include_gpu=False)
        overhead = sampler.measure_collect_overhead(iterations=2)
        self.assertGreaterEqual(overhead["mean_ms"], 0.0)
        self.assertGreaterEqual(overhead["max_ms"], overhead["mean_ms"])


if __name__ == "__main__":
    unittest.main()
