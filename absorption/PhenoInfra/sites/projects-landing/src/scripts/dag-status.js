/**
 * DAG Status Event System (F26)
 *
 * Provides:
 *  - Status event schema (DagStatusEvent)
 *  - Event log with bounded capacity
 *  - Simulated F9-style event source for demo/live mode
 *  - Subscriber notification pattern
 *  - Start/stop/toggle live mode with configurable polling interval
 *
 * The event source can be swapped: currently ships with a simulated
 * schedule that exercises all status transitions. A real implementation
 * would replace the simulated source with fetch() to a server-sent event
 * endpoint or WebSocket.
 */

(function () {
  "use strict";

  // ── constants ──────────────────────────────────────────────────────────────

  /** All valid node statuses, including the new "blocked" status. */
  var STATUSES = {
    PENDING: "pending",
    IN_PROGRESS: "in-progress",
    COMPLETED: "completed",
    FAILED: "failed",
    BLOCKED: "blocked",
  };

  /** Maximum events retained in the event log ring buffer. */
  var MAX_EVENTS = 500;

  /** Default polling interval (ms). */
  var DEFAULT_POLL_MS = 4000;

  // ── colours (matching dag-renderer.js + blocked) ───────────────────────────

  var STATUS_COLORS = {};
  STATUS_COLORS[STATUSES.COMPLETED] = { fill: "#16a34a", stroke: "#15803d", text: "#fff", bg: "#052e16" };
  STATUS_COLORS[STATUSES.IN_PROGRESS] = { fill: "#2563eb", stroke: "#1d4ed8", text: "#fff", bg: "#172554" };
  STATUS_COLORS[STATUSES.PENDING] = { fill: "#6b7280", stroke: "#4b5563", text: "#fff", bg: "#1f2937" };
  STATUS_COLORS[STATUSES.FAILED] = { fill: "#dc2626", stroke: "#b91c1c", text: "#fff", bg: "#450a0a" };
  STATUS_COLORS[STATUSES.BLOCKED] = { fill: "#d97706", stroke: "#b45309", text: "#fff", bg: "#451a03" };
  var DEFAULT_STATUS = STATUSES.PENDING;

  // ── internal state ─────────────────────────────────────────────────────────

  /** Ring buffer of DagStatusEvent objects. */
  var eventLog = [];

  /** Map<nodeId, DagNodeMeta> – per-node metadata including lastUpdated. */
  var nodeMeta = {};

  /** Subscriber callbacks: function(event) called on each new event. */
  var subscribers = [];

  /** Are we in live (polling) mode? */
  var live = false;

  /** setInterval id for the polling loop. */
  var pollId = null;

  /** Polling interval in ms. */
  var pollMs = DEFAULT_POLL_MS;

  /** Timestamp (epoch ms) of the most recent event. */
  var lastEventTimestamp = null;

  /** Current event source function: () => DagStatusEvent[] */
  var sourceFn = null;

  /** Simulated event schedule index. */
  var simScheduleIndex = 0;

  /**
   * A schedule of simulated F9-style events that progressively advance
   * the DAG's state. Each entry yields one or more events per tick.
   * The schedule wraps around so live mode keeps cycling.
   */
  var SIM_SCHEDULE = [
    // Each element: { nodeId, toStatus } — events are generated with
    // appropriate fromStatus based on current node state.
    [
      { nodeId: "f06", toStatus: STATUSES.IN_PROGRESS, source: "execution-engine" },
    ],
    [
      { nodeId: "f10", toStatus: STATUSES.IN_PROGRESS, source: "manual" },
    ],
    [
      { nodeId: "f06", toStatus: STATUSES.COMPLETED, source: "execution-engine" },
      { nodeId: "f07", toStatus: STATUSES.IN_PROGRESS, source: "execution-engine" },
    ],
    [
      { nodeId: "f08", toStatus: STATUSES.IN_PROGRESS, source: "execution-engine" },
      { nodeId: "f11", toStatus: STATUSES.BLOCKED, source: "ci" },
    ],
    [
      { nodeId: "f07", toStatus: STATUSES.COMPLETED, source: "persistence" },
      { nodeId: "f08", toStatus: STATUSES.COMPLETED, source: "reporting" },
    ],
    [
      { nodeId: "f09", toStatus: STATUSES.IN_PROGRESS, source: "cli-tooling" },
    ],
    [
      { nodeId: "f14", toStatus: STATUSES.IN_PROGRESS, source: "manual" },
      { nodeId: "f13", toStatus: STATUSES.COMPLETED, source: "test-suite" },
    ],
    [
      { nodeId: "f09", toStatus: STATUSES.COMPLETED, source: "cli-tooling" },
      { nodeId: "f15", toStatus: STATUSES.IN_PROGRESS, source: "deployment" },
    ],
    [
      { nodeId: "f11", toStatus: STATUSES.IN_PROGRESS, source: "ci" },
    ],
    [
      { nodeId: "f14", toStatus: STATUSES.COMPLETED, source: "manual" },
      { nodeId: "f11", toStatus: STATUSES.COMPLETED, source: "ci" },
      { nodeId: "f15", toStatus: STATUSES.COMPLETED, source: "deployment" },
    ],
    // Reset cycle — wrap back around
    [
      { nodeId: "f06", toStatus: STATUSES.IN_PROGRESS, source: "execution-engine" },
      { nodeId: "f07", toStatus: STATUSES.PENDING, source: "reset" },
      { nodeId: "f08", toStatus: STATUSES.PENDING, source: "reset" },
      { nodeId: "f09", toStatus: STATUSES.PENDING, source: "reset" },
      { nodeId: "f10", toStatus: STATUSES.IN_PROGRESS, source: "reset" },
      { nodeId: "f11", toStatus: STATUSES.PENDING, source: "reset" },
      { nodeId: "f13", toStatus: STATUSES.IN_PROGRESS, source: "reset" },
      { nodeId: "f14", toStatus: STATUSES.FAILED, source: "reset" },
      { nodeId: "f15", toStatus: STATUSES.PENDING, source: "reset" },
    ],
  ];

  // ── helpers ────────────────────────────────────────────────────────────────

  function now() {
    return Date.now();
  }

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function formatTimestamp(ts) {
    if (ts == null) return "—";
    var d = new Date(ts);
    return (
      d.getFullYear() +
      "-" +
      pad(d.getMonth() + 1) +
      "-" +
      pad(d.getDate()) +
      " " +
      pad(d.getHours()) +
      ":" +
      pad(d.getMinutes()) +
      ":" +
      pad(d.getSeconds())
    );
  }

  function formatRelativeTime(ts) {
    if (ts == null) return "—";
    var diff = now() - ts;
    if (diff < 1000) return "just now";
    if (diff < 60000) return Math.floor(diff / 1000) + "s ago";
    if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
    if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
    return Math.floor(diff / 86400000) + "d ago";
  }

  // ── event log ──────────────────────────────────────────────────────────────

  function appendEvent(evt) {
    eventLog.push(evt);
    if (eventLog.length > MAX_EVENTS) {
      eventLog.shift();
    }
    lastEventTimestamp = evt.timestamp;
  }

  // ── simulated event source ─────────────────────────────────────────────────

  /**
   * Simulated F9 event source.
   * Each call returns events for the next tick of the schedule.
   * Accepts a `currentStatusMap` to compute `fromStatus` automatically.
   */
  function simulatedSource(currentStatusMap) {
    if (SIM_SCHEDULE.length === 0) return [];
    var tick = SIM_SCHEDULE[simScheduleIndex] || [];
    simScheduleIndex = (simScheduleIndex + 1) % SIM_SCHEDULE.length;

    var events = [];
    var ts = now();

    for (var i = 0; i < tick.length; i++) {
      var entry = tick[i];
      var currentStatus = (currentStatusMap && currentStatusMap[entry.nodeId]) || DEFAULT_STATUS;
      events.push({
        nodeId: entry.nodeId,
        fromStatus: currentStatus,
        toStatus: entry.toStatus,
        timestamp: ts,
        source: entry.source || "simulated",
      });
    }
    return events;
  }

  // ── public API ─────────────────────────────────────────────────────────────

  /**
   * Create a single status event object.
   * @param {string} nodeId
   * @param {string} fromStatus
   * @param {string} toStatus
   * @param {string} [source="manual"]
   * @param {number} [timestamp=Date.now()]
   * @returns {object} DagStatusEvent
   */
  function createEvent(nodeId, fromStatus, toStatus, source, timestamp) {
    return {
      nodeId: nodeId,
      fromStatus: fromStatus,
      toStatus: toStatus,
      timestamp: timestamp != null ? timestamp : now(),
      source: source || "manual",
    };
  }

  /**
   * Register a subscriber that is called with each new event.
   * @param {function} fn  callback(event)
   * @returns {function} unsubscribe
   */
  function subscribe(fn) {
    subscribers.push(fn);
    return function unsubscribe() {
      var idx = subscribers.indexOf(fn);
      if (idx !== -1) subscribers.splice(idx, 1);
    };
  }

  /**
   * Dispatch an event to all subscribers and record in the log.
   * @param {object} event  DagStatusEvent
   */
  function dispatch(event) {
    appendEvent(event);
    // Update per-node metadata
    if (!nodeMeta[event.nodeId]) {
      nodeMeta[event.nodeId] = { lastUpdated: null, statusHistory: [] };
    }
    nodeMeta[event.nodeId].lastUpdated = event.timestamp;

    for (var i = 0; i < subscribers.length; i++) {
      try {
        subscribers[i](event);
      } catch (e) {
        console.error("[dag-status] subscriber error:", e);
      }
    }
  }

  /**
   * Run one poll cycle: ask the source for events and dispatch them.
   * @param {object} currentStatusMap  { nodeId: status }
   */
  function poll(currentStatusMap) {
    if (!sourceFn) return;
    var events = sourceFn(currentStatusMap);
    for (var i = 0; i < events.length; i++) {
      dispatch(events[i]);
    }
  }

  /**
   * Start live mode.
   * @param {string} [emitterType="simulated"]  "simulated" or (in future) "server-sent"
   * @param {number} [intervalMs=4000]
   * @param {function} [onPoll]  Called each poll cycle with (events[], currentStatusMap)
   */
  function startLive(emitterType, intervalMs, onPoll) {
    if (live) return;
    pollMs = intervalMs || DEFAULT_POLL_MS;

    // Set the source function
    if (emitterType === "server-sent") {
      // Placeholder for real SSE/WebSocket consumption
      sourceFn = function () { return []; };
    } else {
      sourceFn = function (statusMap) { return simulatedSource(statusMap); };
    }

    live = true;

    // Do an immediate poll, then every pollMs
    if (typeof onPoll === "function") {
      pollId = setInterval(function () {
        // gather current status map from subscribers if available
        var statusMap = {};
        // The onPoll callback should provide status map
        // We pass empty and let onPoll fill it
        poll(statusMap);
        onPoll(eventLog.slice(-10), statusMap);
      }, pollMs);
    } else {
      pollId = setInterval(function () {
        poll({});
      }, pollMs);
    }
  }

  /**
   * Stop live mode.
   */
  function stopLive() {
    if (!live) return;
    live = false;
    if (pollId) {
      clearInterval(pollId);
      pollId = null;
    }
  }

  /**
   * Toggle live mode.
   * @param {string} [emitterType="simulated"]
   * @param {number} [intervalMs=4000]
   * @param {function} [onPoll]
   * @returns {boolean} new live state
   */
  function toggleLive(emitterType, intervalMs, onPoll) {
    if (live) {
      stopLive();
    } else {
      startLive(emitterType, intervalMs, onPoll);
    }
    return live;
  }

  /**
   * Get current event log.
   * @param {number} [limit]  max number of recent events to return
   * @returns {object[]}
   */
  function getEventLog(limit) {
    if (limit && limit > 0) {
      return eventLog.slice(-limit);
    }
    return eventLog.slice();
  }

  /**
   * Get per-node metadata (lastUpdated, statusHistory).
   * @returns {object} nodeMeta map
   */
  function getNodeMeta() {
    return nodeMeta;
  }

  /**
   * Get the last event timestamp.
   * @returns {number|null}
   */
  function getLastEventTimestamp() {
    return lastEventTimestamp;
  }

  /**
   * Is live mode active?
   * @returns {boolean}
   */
  function isLive() {
    return live;
  }

  /**
   * Get the polling interval.
   * @returns {number}
   */
  function getPollInterval() {
    return pollMs;
  }

  /**
   * Set the polling interval (takes effect next poll cycle).
   * @param {number} ms
   */
  function setPollInterval(ms) {
    if (ms >= 1000) {
      pollMs = ms;
    }
  }

  /**
   * Clear the event log and node meta.
   */
  function reset() {
    eventLog = [];
    nodeMeta = {};
    simScheduleIndex = 0;
  }

  // ── export formatters (also available) ─────────────────────────────────────
  var formatters = {
    timestamp: formatTimestamp,
    relativeTime: formatRelativeTime,
  };

  // ── public API surface ─────────────────────────────────────────────────────
  window.DagStatus = {
    STATUSES: STATUSES,
    STATUS_COLORS: STATUS_COLORS,
    DEFAULT_STATUS: DEFAULT_STATUS,

    createEvent: createEvent,
    subscribe: subscribe,
    dispatch: dispatch,
    poll: poll,

    startLive: startLive,
    stopLive: stopLive,
    toggleLive: toggleLive,
    isLive: isLive,

    getEventLog: getEventLog,
    getNodeMeta: getNodeMeta,
    getLastEventTimestamp: getLastEventTimestamp,
    getPollInterval: getPollInterval,
    setPollInterval: setPollInterval,

    reset: reset,
    formatTimestamp: formatTimestamp,
    formatRelativeTime: formatRelativeTime,
  };
})();
