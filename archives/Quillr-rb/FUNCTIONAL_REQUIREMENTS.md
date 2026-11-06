# Functional Requirements: quill

## FR-QLL-001: Client Creation
FR-QLL-001a: `createClient({ baseUrl, headers?, timeout? })` SHALL return a `QuillClient` instance.
FR-QLL-001b: Multiple independent client instances SHALL be creatable with different base URLs.
FR-QLL-001c: Default timeout SHALL be 30 seconds if not specified.

## FR-QLL-002: HTTP Methods
FR-QLL-002a: QuillClient SHALL expose: `get<T>(url, options?)`, `post<T>(url, body, options?)`, `put<T>(url, body, options?)`, `patch<T>(url, body, options?)`, `delete<T>(url, options?)`.
FR-QLL-002b: All methods SHALL return `Promise<T>` where T is the expected response body type.
FR-QLL-002c: Non-2xx responses SHALL reject the promise with an `HttpError`.

## FR-QLL-003: Type Safety
FR-QLL-003a: Response types SHALL be inferred from the generic parameter `<T>`.
FR-QLL-003b: If no type parameter is provided, the response SHALL be typed as `unknown`.

## FR-QLL-004: Interceptors
FR-QLL-004a: `client.interceptors.request.use(fn)` SHALL register a request interceptor.
FR-QLL-004b: `client.interceptors.response.use(onFulfilled, onRejected)` SHALL register a response interceptor.
FR-QLL-004c: Interceptors SHALL execute in registration order for requests and reverse order for responses.
FR-QLL-004d: An interceptor returning `undefined` SHALL pass the request/response through unchanged.

## FR-QLL-005: Retry
FR-QLL-005a: `createClient({ retry: { count: n, condition?: fn } })` SHALL configure automatic retry.
FR-QLL-005b: Retry delay SHALL use exponential backoff: `baseDelay * 2^attempt + jitter`.
FR-QLL-005c: By default, retry SHALL occur on status codes 429, 502, 503, 504 and network errors.
FR-QLL-005d: `onRetry(attempt, error)` callback SHALL be invoked before each retry.

## FR-QLL-006: Error Types
FR-QLL-006a: `HttpError` SHALL include: `status: number`, `statusText: string`, `url: string`, `method: string`, `body: unknown`.
FR-QLL-006b: `NetworkError` SHALL be thrown for connection failures (DNS, TCP).
FR-QLL-006c: `TimeoutError` SHALL be thrown when the request exceeds the configured timeout.

## FR-QLL-007: Mock Client
FR-QLL-007a: `createMockClient()` SHALL return a client that intercepts all requests without network access.
FR-QLL-007b: `mock.on("GET /users/:id").reply(200, data)` SHALL register a mock handler.
FR-QLL-007c: `mock.assertAllCalled()` SHALL throw if any registered mock was not called.
FR-QLL-007d: Unmatched requests SHALL throw a `MockNotFoundError` with the unmatched URL.
