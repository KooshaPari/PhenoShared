/**
 * Interceptor pipeline for the Quill HTTP client.
 *
 * An interceptor chain lets consumers register request, response, and error
 * interceptors that are invoked in order for every HTTP call.
 *
 * @module interceptor
 */

import type {
  Interceptor,
  InterceptorContext,
  QuillError,
  QuillResponse,
  RequestInterceptor,
  ResponseInterceptor,
  ErrorInterceptor,
} from "./types";

// ---------------------------------------------------------------------------
// Type guards
// ---------------------------------------------------------------------------

function isRequestInterceptor(i: Interceptor): i is RequestInterceptor {
  return "onRequest" in i;
}
function isResponseInterceptor(i: Interceptor): i is ResponseInterceptor {
  return "onResponse" in i;
}
function isErrorInterceptor(i: Interceptor): i is ErrorInterceptor {
  return "onError" in i;
}

// ---------------------------------------------------------------------------
// InterceptorChain
// ---------------------------------------------------------------------------

/**
 * Ordered collection of interceptors that process a request -> response flow.
 *
 * The chain runs all request interceptors (in registration order), dispatches
 * the fetch, then runs all response interceptors. If any step throws, error
 * interceptors are given a chance to handle the error.
 */
export class InterceptorChain {
  private readonly interceptors: Interceptor[] = [];

  /** Register one or more interceptors (appended to the chain). */
  use(...interceptors: Interceptor[]): void {
    this.interceptors.push(...interceptors);
  }

  /** Run request interceptors and return a (potentially) modified context. */
  async runRequestInterceptors(ctx: InterceptorContext): Promise<InterceptorContext> {
    let current = ctx;
    for (const i of this.interceptors) {
      if (isRequestInterceptor(i)) {
        current = await i.onRequest(current);
      }
    }
    return current;
  }

  /** Run response interceptors on a successful response. */
  async runResponseInterceptors<T>(
    response: QuillResponse<T>,
  ): Promise<QuillResponse<T>> {
    let current = response;
    for (const i of this.interceptors) {
      if (isResponseInterceptor(i)) {
        current = await i.onResponse(current);
      }
    }
    return current;
  }

  /** Run error interceptors when an error occurs. */
  async runErrorInterceptors(error: QuillError): Promise<QuillError> {
    let current = error;
    for (const i of this.interceptors) {
      if (isErrorInterceptor(i)) {
        current = await i.onError(current);
      }
    }
    return current;
  }
}
