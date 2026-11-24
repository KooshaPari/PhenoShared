/**
 * Minimal prefixed logger for the AppGen desktop shell.
 *
 * Centralises console output so the rest of the codebase never calls
 * `console.log`/`console.warn`/`console.error` directly. The scanner rule
 * LT-001 enforces this; keeping the implementation tiny avoids pulling in
 * a heavyweight logging library for a process that emits maybe a dozen
 * messages in its lifetime.
 */

type Level = "info" | "warn" | "error";

const APP_NAME = process.env.APP_NAME ?? "AppGen";

function emit(level: Level, args: unknown[]): void {
  const tag = level === "info" ? "log" : level === "warn" ? "warn" : "error";
  // eslint-disable-next-line no-console -- centralised logger, allowed by LT-001 carve-out
  console[tag](`[${APP_NAME}]`, ...args);
}

export const logger = {
  info: (...args: unknown[]): void => emit("info", args),
  warn: (...args: unknown[]): void => emit("warn", args),
  error: (...args: unknown[]): void => emit("error", args),
};

export default logger;
