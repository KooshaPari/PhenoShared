/**
 * DesignGenerator Tests
 *
 * Traces to: FR-DESIGN-004 (error handling), FR-DESIGN-005 (resilience)
 *
 * Verifies:
 * - L14: All pipeline steps (validate/compose/render) propagate errors through Result type
 * - L26: Timeout handling and cancellation via AbortSignal
 * - Step context enrichment (error.step, error.hint) on failure
 */

import { describe, it, expect, vi } from 'vitest'
import type {
  Composer,
  DesignError,
  DesignSpec,
  GeneratedDesign,
  Renderer,
  Result,
  Validator,
} from '../src/domain/types'
import { DesignGenerator, type GeneratorDeps } from '../src/application/generator'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const makeSpec = (overrides?: Partial<DesignSpec>): DesignSpec => ({
  id: 'test-001',
  prompt: 'Build a landing page',
  constraints: ['responsive', 'dark-mode'],
  metadata: {},
  ...overrides,
})

const okValidator: Validator = {
  validate: async () => ({ ok: true, value: { warnings: [] } }),
}

const okComposer: Composer = {
  compose: async () => ({ ok: true, value: { sections: [] } }),
}

const okRenderer: Renderer = {
  render: async () => ({
    ok: true,
    value: {
      id: 'gen-001',
      format: 'html',
      output: '<div>Hello</div>',
      warnings: [],
    },
  }),
}

const makeDeps = (overrides?: Partial<GeneratorDeps>): GeneratorDeps => ({
  validator: okValidator,
  composer: okComposer,
  renderer: okRenderer,
  ...overrides,
})

function expectErrorCode(
  result: Result<GeneratedDesign, DesignError>,
  expectedCode: string,
  expectedStep?: string,
): void {
  expect(result.ok).toBe(false)
  if (!result.ok) {
    expect(result.error.code).toBe(expectedCode)
    if (expectedStep !== undefined) {
      expect(result.error.step).toBe(expectedStep)
    }
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('DesignGenerator — happy path', () => {
  it('returns ok:true with generated design on success', async () => {
    const gen = new DesignGenerator(makeSpec(), makeDeps())
    const result = await gen.generate()

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.value.id).toBe('gen-001')
      expect(result.value.format).toBe('html')
      expect(result.value.output).toContain('Hello')
    }
  })

  it('passes spec through all three pipeline steps', async () => {
    const validateFn = vi.fn().mockResolvedValue({ ok: true, value: { warnings: [] } })
    const composeFn = vi.fn().mockResolvedValue({ ok: true, value: { sections: [] } })
    const renderFn = vi.fn().mockResolvedValue({
      ok: true,
      value: { id: 'gen-002', format: 'json', output: '{}', warnings: [] },
    })

    const spec = makeSpec({ id: 'pipeline-test' })
    const gen = new DesignGenerator(spec, {
      validator: { validate: validateFn },
      composer: { compose: composeFn },
      renderer: { render: renderFn },
    })

    const result = await gen.generate()
    expect(result.ok).toBe(true)

    // Each step was called exactly once with the spec
    expect(validateFn).toHaveBeenCalledTimes(1)
    expect(validateFn).toHaveBeenCalledWith(spec)
    expect(composeFn).toHaveBeenCalledTimes(1)
    expect(composeFn).toHaveBeenCalledWith(spec)
    expect(renderFn).toHaveBeenCalledTimes(1)
    // Render receives RenderInput wrapping spec + layout + warnings
    expect(renderFn.mock.calls[0][0]).toMatchObject({
      spec,
      layout: { sections: [] },
      warnings: [],
    })
  })
})

describe('DesignGenerator — error propagation (L14)', () => {
  it('propagates validator errors through Result type', async () => {
    const validator: Validator = {
      validate: async () => ({
        ok: false as const,
        error: { code: 'INVALID_PROMPT', message: 'Prompt is too short' },
      }),
    }
    const gen = new DesignGenerator(makeSpec(), makeDeps({ validator }))
    const result = await gen.generate()

    expectErrorCode(result, 'INVALID_PROMPT', 'validate')
    if (!result.ok) {
      expect(result.error.message).toContain('Prompt is too short')
    }
  })

  it('propagates composer errors through Result type', async () => {
    const composer: Composer = {
      compose: async () => ({
        ok: false as const,
        error: { code: 'COMPOSITION_FAILED', message: 'Could not arrange sections' },
      }),
    }
    const gen = new DesignGenerator(makeSpec(), makeDeps({ composer }))
    const result = await gen.generate()

    expectErrorCode(result, 'COMPOSITION_FAILED', 'compose')
    if (!result.ok) {
      expect(result.error.message).toContain('Could not arrange sections')
    }
  })

  it('propagates renderer errors through Result type', async () => {
    const renderer: Renderer = {
      render: async () => ({
        ok: false as const,
        error: { code: 'RENDER_FAILED', message: 'SVG generation exceeded limit' },
      }),
    }
    const gen = new DesignGenerator(makeSpec(), makeDeps({ renderer }))
    const result = await gen.generate()

    expectErrorCode(result, 'RENDER_FAILED', 'render')
    if (!result.ok) {
      expect(result.error.message).toContain('SVG generation exceeded limit')
    }
  })

  it('includes step and hint context in propagated errors', async () => {
    const composer: Composer = {
      compose: async () => ({
        ok: false as const,
        error: { code: 'COMPOSE_ERR', message: 'test' },
      }),
    }
    const gen = new DesignGenerator(makeSpec(), makeDeps({ composer }))
    const result = await gen.generate()

    if (!result.ok) {
      expect(result.error.step).toBe('compose')
      expect(result.error.hint).toBeTruthy()
      expect(typeof result.error.hint).toBe('string')
    }
  })

  it('stops pipeline on first error — does not call subsequent steps', async () => {
    const composeFn = vi.fn().mockResolvedValue({
      ok: false as const,
      error: { code: 'COMPOSE_FAILED', message: 'fail' },
    })
    const renderFn = vi.fn()

    const gen = new DesignGenerator(makeSpec(), makeDeps({
      composer: { compose: composeFn },
      renderer: { render: renderFn },
    }))

    await gen.generate()
    expect(composeFn).toHaveBeenCalledTimes(1)
    expect(renderFn).not.toHaveBeenCalled()
  })
})

describe('DesignGenerator — timeout (L26)', () => {
  it('returns TIMEOUT when a step exceeds the stepTimeout', async () => {
    const slowComposer: Composer = {
      compose: async () => {
        await new Promise((r) => setTimeout(r, 500))
        return { ok: true, value: { sections: [] } }
      },
    }
    const gen = new DesignGenerator(
      makeSpec(),
      makeDeps({ composer: slowComposer }),
      { stepTimeout: 50 }, // 50ms timeout
    )

    const result = await gen.generate()
    expectErrorCode(result, 'TIMEOUT', 'compose')
    if (!result.ok) {
      expect(result.error.hint).toBeTruthy()
    }
  })
})

describe('DesignGenerator — cancellation via AbortSignal (L26)', () => {
  it('returns CANCELLED when signal is already aborted before start', async () => {
    const aborted = AbortSignal.abort()
    const gen = new DesignGenerator(
      makeSpec(),
      makeDeps(),
      { signal: aborted },
    )

    const result = await gen.generate()
    expectErrorCode(result, 'CANCELLED')
  })

  it('returns CANCELLED when signal is aborted during execution', async () => {
    const controller = new AbortController()
    const slowComposer: Composer = {
      compose: async () => {
        await new Promise((r) => setTimeout(r, 500))
        return { ok: true, value: { sections: [] } }
      },
    }

    const gen = new DesignGenerator(
      makeSpec(),
      makeDeps({ composer: slowComposer }),
      { signal: controller.signal, stepTimeout: 10_000 },
    )

    // Abort after a short delay so the step is in-flight
    const abortAfterDelay = new Promise<Result<GeneratedDesign, DesignError>>((resolve) => {
      setTimeout(() => controller.abort(), 20)
      // Also capture the result
      gen.generate().then(resolve)
    })

    const result = await abortAfterDelay
    expectErrorCode(result, 'CANCELLED')
  })
})

describe('DesignGenerator — edge cases', () => {
  it('handles unexpected rejection from a step gracefully', async () => {
    const brokenComposer: Composer = {
      compose: async () => {
        throw new Error('Network partition')
      },
    }
    const gen = new DesignGenerator(makeSpec(), makeDeps({ composer: brokenComposer }))
    const result = await gen.generate()

    expectErrorCode(result, 'INTERNAL_ERROR', 'compose')
    if (!result.ok) {
      expect(result.error.cause).toContain('Network partition')
    }
  })

  it('uses default 30s timeout when not specified', async () => {
    // We just verify the generator runs without specifying timeout
    const gen = new DesignGenerator(makeSpec(), makeDeps())
    const result = await gen.generate()
    expect(result.ok).toBe(true)
  })
})
