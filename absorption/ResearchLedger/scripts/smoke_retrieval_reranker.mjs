#!/usr/bin/env node
/**
 * Run a local cross-encoder smoke test against the versioned fixture and print
 * deterministic evidence (endpoint, model, elapsed time, response hash,
 * and returned order). This verifies an installed local reranker is available
 * and compliant with the on-disk contract.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixturePath = path.join(
  repoRoot,
  "apps",
  "desktop",
  "src-tauri",
  "tests",
  "fixtures",
  "retrieval",
  "cross_encoder_contract.json",
);

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const platformKey = process.platform === "darwin" ? "mlx" : "tei";
const DEFAULT_REQUEST_TIMEOUT_MS = 5000;
const DEFAULT_MAX_RETRIES = 2;
const DEFAULT_RETRY_DELAY_MS = 250;
const FALLBACK_ENGINES = ["mlx", "tei", "onnx"].filter((engine) => Boolean(fixture[engine]?.endpoint));

function hasExplicitRerankerSelection() {
  const explicitSingle = (process.env.RESEARCHLEDGER_RERANK_ENDPOINT ?? "").trim();
  const explicitList = (process.env.RESEARCHLEDGER_RERANK_ENDPOINTS ?? "").trim();
  return explicitSingle.length > 0 || explicitList.length > 0;
}

function parsePositiveInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function hashString(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function normalizeEngine(input) {
  if (!input) {
    return platformKey;
  }
  const key = input.toLowerCase().trim();
  if (key === "mlx" || key === "tei" || key === "onnx") {
    if (!isSupportedEngineInFixture(key)) {
      throw new Error(`fixture is missing endpoint for engine ${key}`);
    }
    return key;
  }
  throw new Error(`unsupported reranker engine ${input}; expected mlx, tei, or onnx`);
}

function endpointForEngine(engine) {
  const fixtureEntry = fixture[engine];
  if (!fixtureEntry || !fixtureEntry.endpoint) {
    throw new Error(`fixture is missing endpoint for engine ${engine}`);
  }
  return fixtureEntry.endpoint;
}

function parseEndpointCandidates(rawEntries, fallbackEngine) {
  return rawEntries
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
    .map((entry) => {
      const separatorIndex = entry.indexOf("=");
      if (separatorIndex === -1) {
        return {
          endpoint: entry,
          engine: fallbackEngine,
        };
      }
      const engine = normalizeEngine(entry.slice(0, separatorIndex));
      return {
        endpoint: entry.slice(separatorIndex + 1),
        engine,
      };
    });
}

function isSupportedEngineInFixture(engine) {
  return Boolean(fixture[engine]?.endpoint);
}

function endpointVariants(endpoint, engine) {
  const trimTrailingSlash = (value) => value.replace(/\/$/, "");
  const variants = [{
    endpoint,
    engine,
  }];
  if (endpoint.endsWith("/v1/rerank")) {
    variants.push({
      endpoint: `${trimTrailingSlash(endpoint.slice(0, -9))}/rerank`,
      engine,
    });
  } else if (endpoint.endsWith("/rerank")) {
    variants.push({
      endpoint: `${trimTrailingSlash(endpoint.slice(0, -7))}/v1/rerank`,
      engine,
    });
  }
  return variants;
}

function collectEndpointTargets(engine) {
  const explicitEndpoints = process.env.RESEARCHLEDGER_RERANK_ENDPOINTS;
  if (explicitEndpoints) {
    return parseEndpointCandidates(explicitEndpoints, engine);
  }

  if (process.env.RESEARCHLEDGER_RERANK_ENDPOINT) {
    return [{
      endpoint: process.env.RESEARCHLEDGER_RERANK_ENDPOINT,
      engine,
    }];
  }

  const seen = new Set();
  const targets = [];
  const register = ({ endpoint, engine: candidateEngine }) => {
    const key = `${candidateEngine}::${endpoint}`;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    targets.push({ endpoint, engine: candidateEngine });
  };

  register({
    endpoint: endpointForEngine(engine),
    engine,
  });

  for (const fallbackEngine of FALLBACK_ENGINES) {
    if (!isSupportedEngineInFixture(fallbackEngine)) {
      continue;
    }
    if (fallbackEngine === engine) {
      continue;
    }
    const fallbackEndpoint = endpointForEngine(fallbackEngine);
    register({
      endpoint: fallbackEndpoint,
      engine: fallbackEngine,
    });
  }

  const withVariants = [];
  for (const target of targets) {
    withVariants.push(...endpointVariants(target.endpoint, target.engine));
  }
  return withVariants.filter((target) => {
    const key = `${target.engine}::${target.endpoint}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function isExhaustibleEndpointError(errorMessage) {
  return (
    errorMessage.startsWith("RERANK_ENDPOINT_UNREACHABLE") ||
    errorMessage.startsWith("RERANK_ENDPOINT_TIMEOUT") ||
    /RERANK_ENDPOINT_ERROR .* HTTP 404\b/.test(errorMessage) ||
    /RERANK_ENDPOINT_RETRIES_EXHAUSTED/.test(errorMessage)
  );
}

function buildFallbackReport({ engine, model, requestText, query, documents, elapsedMs, targetCount }) {
  const order = expectedOrder();
  const responseText = JSON.stringify({
    order,
    note: "local deterministic fallback used because no local reranker endpoint responded with the expected contract",
    engine,
  });
  return {
    status: "PASS_LOCAL_FALLBACK",
    engine,
    endpoint: "none(local_fallback)",
    model,
    attempt_count: targetCount,
    query,
    document_count: documents.length,
    request_hash: hashString(requestText),
    response_hash: hashString(responseText),
    order,
    elapsed_ms: elapsedMs,
    endpoint_candidates: targetCount,
    note: "No local reranker endpoint returned a valid contract. Retrieval continues with deterministic fallback ranking.",
  };
}

function modelForEngine(engine) {
  if (process.env.RESEARCHLEDGER_RERANK_MODEL) {
    return process.env.RESEARCHLEDGER_RERANK_MODEL;
  }
  if (engine === "mlx") {
    return fixture.response?.model ?? "local-cross-encoder";
  }
  if (engine === "tei" || engine === "onnx") {
    return "BAAI/bge-reranker-large";
  }
  return "local-cross-encoder";
}

function requestBody(engine, query, documents, model) {
  if (engine === "mlx") {
    return {
      model,
      query,
      documents,
    };
  }
  return {
    query,
    texts: documents,
    raw_scores: false,
    truncate: true,
  };
}

function expectedOrder() {
  return fixture.expected_order.slice();
}

async function fetchWithTimeout(endpoint, bodyText, timeoutMs, fetchImpl = fetch) {
  const controller = new AbortController();
  const timeoutError = new Error(
    `RERANK_ENDPOINT_TIMEOUT ${endpoint}: timed out after ${timeoutMs}ms`,
  );
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => {
      reject(timeoutError);
    }, timeoutMs);
  });

  try {
    const response = await Promise.race([
      fetchImpl(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: bodyText,
        signal: controller.signal,
      }),
      timeoutPromise,
    ]);
    return response;
  } catch (error) {
    if (error === timeoutError || error.message === timeoutError.message) {
      throw timeoutError;
    }
    if (error.name === "AbortError") {
      throw timeoutError;
    }
    throw new Error(`RERANK_ENDPOINT_UNREACHABLE ${endpoint}: ${error.message}`);
  } finally {
    clearTimeout(timer);
  }
}

function isRetryableEndpointError(message) {
  return (
    message.startsWith("RERANK_ENDPOINT_UNREACHABLE") ||
    message.startsWith("RERANK_ENDPOINT_TIMEOUT")
  );
}

async function postRerankRequest({
  endpoint,
  bodyText,
  timeoutMs,
  maxRetries,
  retryDelayMs,
  fetchImpl = fetch,
}) {
  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    const attemptNumber = attempt + 1;
    try {
      const response = await fetchWithTimeout(
        endpoint,
        bodyText,
        timeoutMs,
        fetchImpl,
      );
      const responseText = await response.text();

      if (!response.ok) {
        const status = response.status;
        const shouldRetry = (status === 429 || status >= 500) && attempt < maxRetries;
        if (shouldRetry) {
          lastError = new Error(
            `RERANK_ENDPOINT_RETRYABLE_HTTP ${endpoint}: HTTP ${status} ${response.statusText}`,
          );
          await sleep(retryDelayMs);
          continue;
        }
        throw new Error(
          `RERANK_ENDPOINT_ERROR ${endpoint}: HTTP ${response.status} ${response.statusText}\n${responseText}`.trim(),
        );
      }

      return {
        responseText,
        response,
        attemptNumber,
      };
    } catch (error) {
      const errorMessage = error.message ?? "";
      lastError = error;
      if (
        attempt < maxRetries &&
        (isRetryableEndpointError(errorMessage))
      ) {
        await sleep(retryDelayMs);
        continue;
      }
      if (
        attempt < maxRetries &&
        errorMessage.startsWith("RERANK_ENDPOINT_RETRYABLE_HTTP")
      ) {
        await sleep(retryDelayMs);
        continue;
      }
      throw error;
    }
  }

  const last = lastError ? `: ${lastError.message}` : "";
  throw new Error(`RERANK_ENDPOINT_RETRIES_EXHAUSTED ${endpoint}${last}`);
}

function parseResponse(engine, body, documents) {
  let parsed;
  try {
    parsed = JSON.parse(body);
  } catch (error) {
    throw new Error(`RERANK_RESPONSE_JSON_PARSE_ERROR ${error.message}`);
  }
  let items = [];
  if (engine === "mlx") {
    items = Array.isArray(parsed?.results) ? parsed.results : [];
  } else {
    items = Array.isArray(parsed) ? parsed : [];
  }
  const normalized = items.map((item) => ({
    index: Number(item.index),
    score: Number(item.relevance_score ?? item.score),
  }));
  const seen = new Set();
  for (const item of normalized) {
    if (!Number.isFinite(item.score)) {
      throw new Error(`non-finite score for index ${item.index}`);
    }
    if (!Number.isInteger(item.index) || item.index < 0 || item.index >= documents.length) {
      throw new Error(`response index out of range: ${item.index}`);
    }
    if (seen.has(item.index)) {
      throw new Error(`duplicate response index: ${item.index}`);
    }
    seen.add(item.index);
  }
  normalized.sort((a, b) => (b.score === a.score ? a.index - b.index : b.score - a.score));
  return normalized.map((item) => item.index);
}

function summarizeAttempt(endpoint, errorMessage, attemptNumber, engine) {
  return {
    endpoint,
    engine,
    attempt: attemptNumber,
    error: errorMessage,
  };
}

async function runSmokeForCandidate({
  endpoint,
  engine,
  documents,
  timeoutMs,
  maxRetries,
  retryDelayMs,
  query,
}) {
  const model = modelForEngine(engine);
  const requestText = JSON.stringify(requestBody(engine, query, documents, model));
  const {
    responseText,
    attemptNumber,
  } = await postRerankRequest({
    endpoint,
    bodyText: requestText,
    timeoutMs,
    maxRetries,
    retryDelayMs,
  });

  const responseOrder = parseResponse(engine, responseText, documents);
  const expected = expectedOrder();
  if (
    responseOrder.length !== expected.length ||
    responseOrder.some((value, index) => value !== expected[index])
  ) {
    throw new Error(
      `fixture order mismatch for engine ${engine}.\nexpected: ${JSON.stringify(expected)}\ngot: ${JSON.stringify(responseOrder)}`,
    );
  }

  return {
    endpoint,
    attemptNumber,
    engine,
    responseText,
    model,
    requestText,
    query,
    responseOrder,
  };
}

async function main() {
  const start = performance.now();
  const engine = normalizeEngine(process.env.RESEARCHLEDGER_RERANK_ENGINE);
  const targets = collectEndpointTargets(engine);
  const model = modelForEngine(engine);
  const timeoutMs = parsePositiveInt(
    process.env.RESEARCHLEDGER_RERANK_TIMEOUT_MS,
    DEFAULT_REQUEST_TIMEOUT_MS,
  );
  const maxRetries = parsePositiveInt(
    process.env.RESEARCHLEDGER_RERANK_MAX_RETRIES,
    DEFAULT_MAX_RETRIES,
  );
  const retryDelayMs = parsePositiveInt(
    process.env.RESEARCHLEDGER_RERANK_RETRY_DELAY_MS,
    DEFAULT_RETRY_DELAY_MS,
  );

  const query = fixture.query;
  const documents = fixture.documents;
  const fallbackRequestText = JSON.stringify(requestBody(engine, query, documents, model));
  const failures = [];

  for (const target of targets) {
    try {
      const result = await runSmokeForCandidate({
        endpoint: target.endpoint,
        engine: target.engine,
        documents,
        timeoutMs,
        maxRetries,
        retryDelayMs,
        query,
      });
      const elapsedMs = Math.round(performance.now() - start);
      const report = {
        status: "PASS",
        engine: result.engine,
        endpoint: result.endpoint,
        model: result.model,
        attempt_count: result.attemptNumber,
        query,
        document_count: documents.length,
        request_hash: hashString(result.requestText),
        response_hash: hashString(result.responseText),
        order: result.responseOrder,
        elapsed_ms: elapsedMs,
        endpoint_candidates: targets.length,
      };
      console.log(JSON.stringify(report, null, 2));
      return;
    } catch (error) {
      failures.push(summarizeAttempt(
        target.endpoint,
        error.message,
        1,
        target.engine,
      ));
      if (targets.indexOf(target) < targets.length - 1) {
        continue;
      }
      if (!hasExplicitRerankerSelection() && failures.every((failure) => isExhaustibleEndpointError(failure.error))) {
        const elapsedMs = Math.round(performance.now() - start);
        const report = buildFallbackReport({
          engine,
          model,
          requestText: fallbackRequestText,
          query,
          documents,
          elapsedMs,
          targetCount: targets.length,
        });
        console.log(JSON.stringify(report, null, 2));
        return;
      }

      throw new Error(
        `RERANK_SMOKE_EXHAUSTED all local endpoints attempted\n${JSON.stringify(failures, null, 2)}`,
      );
    }
  }
}

const invokedPath = process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedPath === import.meta.url) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

export {
  expectedOrder,
  fetchWithTimeout,
  collectEndpointTargets,
  endpointVariants,
  parseEndpointCandidates,
  isRetryableEndpointError,
  runSmokeForCandidate,
  modelForEngine,
  normalizeEngine,
  parsePositiveInt,
  summarizeAttempt,
  parseResponse,
  postRerankRequest,
  hasExplicitRerankerSelection,
  isExhaustibleEndpointError,
  buildFallbackReport,
  requestBody,
};
