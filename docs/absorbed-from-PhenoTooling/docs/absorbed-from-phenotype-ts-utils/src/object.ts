/* eslint-disable @typescript-eslint/no-explicit-any */
/** Deep-merge two objects. Arrays are replaced, not concatenated. */
export function deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
  const result: Record<string, any> = { ...target };
  for (const key of Object.keys(source)) {
    const sVal = (source as any)[key];
    const tVal = (target as any)[key];
    if (
      sVal !== null &&
      typeof sVal === 'object' &&
      !Array.isArray(sVal) &&
      tVal !== null &&
      typeof tVal === 'object' &&
      !Array.isArray(tVal)
    ) {
      result[key] = deepMerge(tVal, sVal);
    } else {
      result[key] = sVal;
    }
  }
  return result as T;
}

/** Deep-clone a JSON-serializable value. */
export function deepClone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}
