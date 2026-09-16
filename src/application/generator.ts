import type {
  Composer,
  DesignError,
  DesignSpec,
  GeneratedDesign,
  Renderer,
  Result,
  Validator,
} from '../domain/types'

export interface GeneratorDeps {
  renderer: Renderer
  composer: Composer
  validator: Validator
}

export interface GeneratorOptions {
  /** Per-step timeout in milliseconds. Default: 30_000. */
  stepTimeout?: number
  /** Optional AbortSignal for cancellation. */
  signal?: AbortSignal
}

export class DesignGenerator {
  private readonly logPrefix = '[DesignGenerator]'

  public constructor(
    private readonly spec: DesignSpec,
    private readonly deps: GeneratorDeps,
    private readonly options: GeneratorOptions = {},
  ) {}

  public async generate(): Promise<Result<GeneratedDesign, DesignError>> {
    const timeout = this.options.stepTimeout ?? 30_000
    const signal = this.options.signal

    try {
      // ── validate ──────────────────────────────────────────────────
      this.logStep('validate:start', { specId: this.spec.id })

      const validationResult = await this.withTimeout(
        this.deps.validator.validate(this.spec),
        timeout,
        signal,
        'validate',
      )
      if (!validationResult.ok) {
        this.logStep('validate:failed', validationResult.error)
        return {
          ok: false,
          error: this.wrapError(validationResult.error, 'validate'),
        }
      }

      this.logStep('validate:complete', {
        warnings: validationResult.value.warnings.length,
      })

      // ── compose ───────────────────────────────────────────────────
      this.logStep('compose:start', { specId: this.spec.id })

      const composeResult = await this.withTimeout(
        this.deps.composer.compose(this.spec),
        timeout,
        signal,
        'compose',
      )
      if (!composeResult.ok) {
        return { ok: false, error: this.wrapError(composeResult.error, 'compose') }
      }

      this.logStep('compose:complete', {
        sectionCount: composeResult.value.sections.length,
      })

      // ── render ────────────────────────────────────────────────────
      this.logStep('render:start', { specId: this.spec.id })

      const renderResult = await this.withTimeout(
        this.deps.renderer.render({
          spec: this.spec,
          layout: composeResult.value,
          warnings: validationResult.value.warnings,
        }),
        timeout,
        signal,
        'render',
      )
      if (!renderResult.ok) {
        return { ok: false, error: this.wrapError(renderResult.error, 'render') }
      }

      this.logStep('render:complete', {
        format: renderResult.value.format,
        outputId: renderResult.value.id,
      })

      return { ok: true, value: renderResult.value }
    } catch (err: unknown) {
      return {
        ok: false,
        error: this.toDesignError(err, 'unknown'),
      }
    }
  }

  // ── helpers ─────────────────────────────────────────────────────

  /**
   * Wraps a promise with a configurable timeout and optional external
   * AbortSignal.  Throws on timeout (TimeoutError) or cancellation
   * (AbortError) so the caller handles a single error channel.
   */
  private async withTimeout<T>(
    promise: Promise<T>,
    ms: number,
    signal: AbortSignal | undefined,
    step: string,
  ): Promise<T> {
    // Fast-path: already aborted
    if (signal?.aborted) {
      throw Object.assign(
        new DOMException(`Step "${step}" cancelled before start`, 'AbortError'),
        { step },
      )
    }

    const controller = new AbortController()

    const onParentAbort = (): void => {
      controller.abort(signal?.reason)
    }
    if (signal) {
      signal.addEventListener('abort', onParentAbort, { once: true })
    }

    const timer = setTimeout(() => {
      controller.abort(
        Object.assign(
          new DOMException(`Step "${step}" timed out after ${ms}ms`, 'TimeoutError'),
          { step },
        ),
      )
    }, ms)

    // Enrich rejections from the original promise with step context
    const enriched = promise.catch((err: unknown) => {
      const enriched = err instanceof Error ? err : new Error(String(err))
      ;(enriched as Error & { step: string }).step = step
      throw enriched
    })

    try {
      return await Promise.race([
        enriched,
        new Promise<never>((_, reject) => {
          controller.signal.addEventListener(
            'abort',
            () => {
              reject(controller.signal.reason)
            },
            { once: true },
          )
        }),
      ])
    } finally {
      clearTimeout(timer)
      if (signal) {
        signal.removeEventListener('abort', onParentAbort)
      }
    }
  }

  private toDesignError(err: unknown, step: string): DesignError {
    if (err instanceof DOMException) {
      const typed = err as DOMException & { step?: string }
      if (err.name === 'TimeoutError') {
        return {
          code: 'TIMEOUT',
          message: err.message,
          step: typed.step ?? step,
          hint: 'The generation step took too long. Try a simpler design spec or increase the stepTimeout option.',
        }
      }
      if (err.name === 'AbortError') {
        return {
          code: 'CANCELLED',
          message: err.message,
          step: typed.step ?? step,
          hint: 'The operation was cancelled by the caller.',
        }
      }
    }
    // Generic / unexpected error — try to extract step from enriched error
    const enriched = err as Error & { step?: string }
    const actualStep = enriched.step ?? step
    return {
      code: 'INTERNAL_ERROR',
      message: `Step "${actualStep}" failed: ${err instanceof Error ? err.message : String(err)}`,
      cause: err instanceof Error ? err.message : String(err),
      step: actualStep,
    }
  }

  private wrapError(err: DesignError, step: string): DesignError {
    return {
      ...err,
      step: err.step ?? step,
      hint:
        err.hint ?? `The "${step}" step failed. Check the error details above.`,
    }
  }

  private logStep(step: string, payload: unknown): void {
    console.info(this.logPrefix, step, payload)
  }
}
