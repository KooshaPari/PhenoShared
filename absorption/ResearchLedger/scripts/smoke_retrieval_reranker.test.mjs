#!/usr/bin/env node
/**
 * Deterministic unit tests for smoke_retrieval_reranker helpers and transport
 * control flow (timeouts, retries, parse validation).
 */

import { describe, expect, it } from "vitest";

import {
  fetchWithTimeout,
  collectEndpointTargets,
  hasExplicitRerankerSelection,
  isRetryableEndpointError,
  isExhaustibleEndpointError,
  buildFallbackReport,
  normalizeEngine,
  parsePositiveInt,
  parseEndpointCandidates,
  parseResponse,
  postRerankRequest,
  runSmokeForCandidate,
  requestBody,
  summarizeAttempt,
} from "./smoke_retrieval_reranker.mjs";

function makeResponse({ ok, status = 200, statusText = "OK", body = "{}" }) {
  return {
    ok,
    status,
    statusText,
    text: async () => body,
  };
}

describe("smoke_retrieval_reranker helper parsing and transport helpers", () => {
  it("normalizes supported engines and falls back to current platform key", () => {
    expect(normalizeEngine("TeI")).toBe("tei");
    expect(normalizeEngine(undefined)).toBe(process.platform === "darwin" ? "mlx" : "tei");
  });

  it("parses positive integers and returns fallback when invalid", () => {
    expect(parsePositiveInt("45", 10)).toBe(45);
    expect(parsePositiveInt("0", 10)).toBe(10);
    expect(parsePositiveInt("-7", 10)).toBe(10);
    expect(parsePositiveInt("n/a", 7)).toBe(7);
  });

  it("parses endpoint candidate lists with optional engine prefixes", () => {
    const parsed = parseEndpointCandidates(
      "tei=http://127.0.0.1:8080/rerank,  http://127.0.0.1:9000/v1/rerank",
      "mlx",
    );
    expect(parsed).toEqual([
      { endpoint: "http://127.0.0.1:8080/rerank", engine: "tei" },
      { endpoint: "http://127.0.0.1:9000/v1/rerank", engine: "mlx" },
    ]);
  });

  it("collects fallback endpoints when no explicit endpoint is provided", () => {
    const originalSingle = process.env.RESEARCHLEDGER_RERANK_ENDPOINT;
    const originalList = process.env.RESEARCHLEDGER_RERANK_ENDPOINTS;
    process.env.RESEARCHLEDGER_RERANK_ENDPOINT = "";
    process.env.RESEARCHLEDGER_RERANK_ENDPOINTS = "";
    const targets = collectEndpointTargets(process.platform === "darwin" ? "mlx" : "tei");
    const engines = new Set(targets.map((entry) => entry.engine));
    expect(targets.length).toBeGreaterThanOrEqual(2);
    expect(engines.size).toBeGreaterThanOrEqual(2);
    for (const target of targets) {
      expect(target.endpoint).toContain("://");
      expect(["mlx", "tei"]).toContain(target.engine);
    }
    process.env.RESEARCHLEDGER_RERANK_ENDPOINT = originalSingle;
    process.env.RESEARCHLEDGER_RERANK_ENDPOINTS = originalList;
  });

  it("detects explicit reranker endpoint env settings", () => {
    const originalSingle = process.env.RESEARCHLEDGER_RERANK_ENDPOINT;
    const originalList = process.env.RESEARCHLEDGER_RERANK_ENDPOINTS;

    process.env.RESEARCHLEDGER_RERANK_ENDPOINT = "";
    process.env.RESEARCHLEDGER_RERANK_ENDPOINTS = "";
    expect(hasExplicitRerankerSelection()).toBe(false);

    process.env.RESEARCHLEDGER_RERANK_ENDPOINT = "http://127.0.0.1:9000/v1/rerank";
    expect(hasExplicitRerankerSelection()).toBe(true);

    process.env.RESEARCHLEDGER_RERANK_ENDPOINT = "";
    process.env.RESEARCHLEDGER_RERANK_ENDPOINTS = "mlx=http://127.0.0.1:9000/v1/rerank";
    expect(hasExplicitRerankerSelection()).toBe(true);

    process.env.RESEARCHLEDGER_RERANK_ENDPOINT = originalSingle;
    process.env.RESEARCHLEDGER_RERANK_ENDPOINTS = originalList;
  });

  it("classifies unavailable endpoint errors as fallback-eligible", () => {
    expect(isExhaustibleEndpointError("RERANK_ENDPOINT_UNREACHABLE http://localhost:1: nope")).toBe(true);
    expect(isExhaustibleEndpointError("RERANK_ENDPOINT_TIMEOUT http://localhost:1: timed out")).toBe(true);
    expect(isExhaustibleEndpointError("RERANK_ENDPOINT_ERROR http://127.0.0.1:9000/v1/rerank: HTTP 404 Not Found")).toBe(true);
    expect(isExhaustibleEndpointError("RERANK_ENDPOINT_ERROR http://127.0.0.1:9000/v1/rerank: HTTP 500 Internal Server Error")).toBe(false);
  });

  it("builds deterministic fallback report deterministically", () => {
    const report = buildFallbackReport({
      engine: "mlx",
      model: "local-cross-encoder",
      requestText: "{\"model\":\"x\"}",
      query: "q",
      documents: ["a", "b", "c"],
      elapsedMs: 12,
      targetCount: 4,
    });
    expect(report.status).toBe("PASS_LOCAL_FALLBACK");
    expect(report.endpoint).toBe("none(local_fallback)");
    expect(report.engine).toBe("mlx");
    expect(report.document_count).toBe(3);
    expect(report.order).toEqual([2, 1, 0]);
  });

  it("builds engine-specific request bodies", () => {
    expect(requestBody("mlx", "q", ["a", "b"], "local-cross-encoder")).toEqual({
      model: "local-cross-encoder",
      query: "q",
      documents: ["a", "b"],
    });
    expect(requestBody("tei", "q", ["a", "b"], "BAAI/bge-reranker-large")).toEqual({
      query: "q",
      texts: ["a", "b"],
      raw_scores: false,
      truncate: true,
    });
    expect(requestBody("onnx", "q", ["a"], "m")).toEqual({
      query: "q",
      texts: ["a"],
      raw_scores: false,
      truncate: true,
    });
  });

  it("treats retryable and non-retryable endpoint errors explicitly", () => {
    expect(isRetryableEndpointError("RERANK_ENDPOINT_TIMEOUT http://localhost:1: timed out")).toBe(true);
    expect(isRetryableEndpointError("RERANK_ENDPOINT_UNREACHABLE x: nope")).toBe(true);
    expect(isRetryableEndpointError("RERANK_ENDPOINT_RETRYABLE_HTTP x: HTTP 429")).toBe(false);
    expect(isRetryableEndpointError("RERANK_ENDPOINT_ERROR x: HTTP 404 Not Found")).toBe(false);
  });

  it("orders and validates parsed rerank payloads", () => {
    const response = JSON.stringify({
      results: [
        { index: 1, relevance_score: 0.2 },
        { index: 2, score: 0.7 },
        { index: 0, score: 0.7 },
      ],
    });
    expect(parseResponse("mlx", response, ["a", "b", "c"])).toEqual([0, 2, 1]);
  });

  it("raises a deterministic parse error for malformed response bodies", () => {
    expect(() => parseResponse("mlx", "{ not-json", ["a", "b"])).toThrow(
      /RERANK_RESPONSE_JSON_PARSE_ERROR/,
    );
  });

  it("retries on 5xx and then succeeds with the final successful payload", async () => {
    let attempts = 0;

    const fetchImpl = async () => {
      attempts += 1;
      if (attempts === 1) {
        return makeResponse({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          body: "temporary failure",
        });
      }

      return makeResponse({
        ok: true,
        body: JSON.stringify([
          { index: 2, score: 0.42 },
          { index: 0, score: 0.31 },
          { index: 1, score: 0.12 },
        ]),
      });
    };

    const result = await postRerankRequest({
      endpoint: "http://127.0.0.1:0/rerank",
      bodyText: "{}",
      timeoutMs: 1000,
      maxRetries: 2,
      retryDelayMs: 1,
      fetchImpl,
    });

    expect(attempts).toBe(2);
    expect(result.attemptNumber).toBe(2);
    expect(result.responseText).toContain("index");
  });

  it("retries transient network errors with explicit timeout-cap behavior", async () => {
    const hangingFetch = async () => new Promise(() => {});
    await expect(
      fetchWithTimeout(
        "http://127.0.0.1:0/rerank",
        "{}",
        5,
        hangingFetch,
      ),
    ).rejects.toThrow(/RERANK_ENDPOINT_TIMEOUT/);
  });

  it("fails non-retryable HTTP status without retry", async () => {
    let attempts = 0;
    const fetchImpl = async () => {
      attempts += 1;
      return makeResponse({
        ok: false,
        status: 404,
        statusText: "Not Found",
        body: "not found",
      });
    };

    await expect(
      postRerankRequest({
        endpoint: "http://127.0.0.1:0/rerank",
        bodyText: "{}",
        timeoutMs: 1000,
        maxRetries: 2,
        retryDelayMs: 1,
        fetchImpl,
      }),
    ).rejects.toThrow("RERANK_ENDPOINT_ERROR");
    expect(attempts).toBe(1);
  });

  it("runs a candidate fully through order validation before PASS", async () => {
    let called = false;
    let request;
    const fetchImpl = async (_endpoint, options) => {
      called = true;
      request = JSON.parse(options.body);
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () => JSON.stringify([
          { index: 2, score: 0.9 },
          { index: 1, score: 0.4 },
          { index: 0, score: 0.2 },
        ]),
      };
    };

    const originalFetch = global.fetch;
    global.fetch = fetchImpl;
    try {
      const result = await runSmokeForCandidate({
        endpoint: "http://127.0.0.1:0/rerank",
        engine: "tei",
        documents: ["a", "b", "c"],
        model: "x",
        timeoutMs: 1000,
        maxRetries: 1,
        retryDelayMs: 1,
        query: "q",
      });
      expect(called).toBe(true);
      expect(result.engine).toBe("tei");
      expect(result.attemptNumber).toBe(1);
      expect(result.responseOrder).toEqual([2, 1, 0]);
      expect(request).toEqual({
        query: "q",
        texts: ["a", "b", "c"],
        raw_scores: false,
        truncate: true,
      });
    } finally {
      global.fetch = originalFetch;
    }
  });

  it("summarizes failures deterministically", () => {
    expect(summarizeAttempt("http://127.0.0.1:0/rerank", "boom", 3, "tei")).toEqual({
      endpoint: "http://127.0.0.1:0/rerank",
      error: "boom",
      attempt: 3,
      engine: "tei",
    });
  });
});
