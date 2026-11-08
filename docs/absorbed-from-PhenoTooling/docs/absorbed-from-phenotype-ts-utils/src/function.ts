/* eslint-disable @typescript-eslint/no-explicit-any */
/** Debounce: call fn after `wait` ms of silence. */
export function debounce<T extends (...args: any[]) => void>(
  fn: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/** Throttle: call fn at most once per `wait` ms. */
export function throttle<T extends (...args: any[]) => void>(
  fn: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= wait) {
      lastCall = now;
      fn(...args);
    }
  };
}
