/**
 * Deep-merge two plain objects. Arrays are concatenated.
 * `source` values override `target` values for primitives.
 */
export function deepMerge<T extends Record<string, unknown>>(
  target: T,
  source: Record<string, unknown>,
): T {
  const output = { ...target } as Record<string, unknown>

  for (const key of Object.keys(source)) {
    const srcVal = source[key]
    const tgtVal = output[key]

    if (Array.isArray(tgtVal) && Array.isArray(srcVal)) {
      output[key] = [...tgtVal, ...srcVal]
    } else if (
      srcVal !== null &&
      typeof srcVal === 'object' &&
      !Array.isArray(srcVal) &&
      tgtVal !== null &&
      typeof tgtVal === 'object' &&
      !Array.isArray(tgtVal)
    ) {
      output[key] = deepMerge(
        tgtVal as Record<string, unknown>,
        srcVal as Record<string, unknown>,
      )
    } else {
      output[key] = srcVal
    }
  }

  return output as T
}
