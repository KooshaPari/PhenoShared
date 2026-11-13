// Config and mapping tests. A config that cannot be trusted must throw, not start.
import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { readConfig } from "../src/index.js";
import { normalizeRecipient, parseRecipientMap, resolveRecipient } from "../src/mapping.js";

describe("config parsing", () => {
  test("a missing token is rejected", () => {
    assert.throws(() => readConfig({}), /WAKE_RECEIVER_TOKEN is required/);
  });

  test("port 0 is out of range", () => {
    assert.throws(
      () => readConfig({ WAKE_RECEIVER_TOKEN: "t", WAKE_RECEIVER_PORT: "0" }),
      /WAKE_RECEIVER_PORT must be an integer 1-65535/,
    );
  });

  test("port 70000 is out of range", () => {
    assert.throws(
      () => readConfig({ WAKE_RECEIVER_TOKEN: "t", WAKE_RECEIVER_PORT: "70000" }),
      /WAKE_RECEIVER_PORT must be an integer 1-65535/,
    );
  });

  test("a non-integer port is rejected", () => {
    assert.throws(
      () => readConfig({ WAKE_RECEIVER_TOKEN: "t", WAKE_RECEIVER_PORT: "abc" }),
      /WAKE_RECEIVER_PORT must be an integer 1-65535/,
    );
  });

  test("a valid config loads the inline recipient map", () => {
    const config = readConfig({
      WAKE_RECEIVER_TOKEN: "synthetic-token",
      WAKE_RECEIVER_PORT: "3211",
      WAKE_RECEIVER_MAP_JSON: JSON.stringify({ civis: "wE:p1" }),
    });
    assert.equal(config.token, "synthetic-token");
    assert.equal(config.port, 3211);
    assert.equal(config.dryRun, false);
    assert.deepEqual(config.recipientMap, { civis: { paneId: "wE:p1" } });
  });

  test("dry-run is enabled only by the literal '1'", () => {
    const base = { WAKE_RECEIVER_TOKEN: "t", WAKE_RECEIVER_MAP_JSON: "{}" };
    assert.equal(readConfig({ ...base, WAKE_RECEIVER_DRY_RUN: "1" }).dryRun, true);
    assert.equal(readConfig({ ...base, WAKE_RECEIVER_DRY_RUN: "true" }).dryRun, false);
    assert.equal(readConfig({ ...base }).dryRun, false);
  });

  test("an invalid rate limit is rejected", () => {
    assert.throws(
      () =>
        readConfig({
          WAKE_RECEIVER_TOKEN: "t",
          WAKE_RECEIVER_MAP_JSON: "{}",
          WAKE_RECEIVER_MAX_PER_MINUTE: "-1",
        }),
      /WAKE_RECEIVER_MAX_PER_MINUTE must be an integer >= 0/,
    );
  });

  test("the rate limit defaults to 30 and is configurable", () => {
    const base = { WAKE_RECEIVER_TOKEN: "t", WAKE_RECEIVER_MAP_JSON: "{}" };
    assert.equal(readConfig(base).maxPerMinute, 30);
    assert.equal(readConfig({ ...base, WAKE_RECEIVER_MAX_PER_MINUTE: "0" }).maxPerMinute, 0);
    assert.equal(readConfig({ ...base, WAKE_RECEIVER_MAX_PER_MINUTE: "5" }).maxPerMinute, 5);
  });
});

describe("recipient mapping", () => {
  test("normalization strips the domain and lowercases", () => {
    assert.equal(normalizeRecipient("Civis@example.com"), "civis");
    assert.equal(normalizeRecipient("  jcode-w7-p1q  "), "jcode-w7-p1q");
    assert.equal(normalizeRecipient(""), "");
    assert.equal(normalizeRecipient("@example.com"), "");
  });

  test("parse skips underscore comment keys and normalizes keys", () => {
    const map = parseRecipientMap({ _comment: "not a recipient", "Civis@x": { paneId: "wE:p1" } });
    assert.deepEqual(map, { civis: { paneId: "wE:p1" } });
  });

  test("parse accepts a string shorthand and an object binding", () => {
    const map = parseRecipientMap({
      civis: "wE:p1",
      deskops: { paneId: "wE:p2", label: "Desk Ops" },
    });
    assert.deepEqual(map.civis, { paneId: "wE:p1" });
    assert.deepEqual(map.deskops, { paneId: "wE:p2", label: "Desk Ops" });
  });

  test("parse rejects an empty or invalid binding", () => {
    assert.throws(() => parseRecipientMap({ civis: "" }), /empty pane binding/);
    assert.throws(() => parseRecipientMap({ civis: { nope: 1 } }), /invalid binding/);
  });

  test("resolve is case-insensitive on the local part", () => {
    const map = parseRecipientMap({ civis: "wE:p1" });
    assert.deepEqual(resolveRecipient(map, "CIVIS@example.com"), { paneId: "wE:p1" });
    assert.equal(resolveRecipient(map, "unknown@example.com"), undefined);
  });
});
