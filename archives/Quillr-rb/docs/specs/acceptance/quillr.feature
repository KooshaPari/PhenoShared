Feature: Quillr TypeScript Client
  @FR-1 @FR-2
  Scenario: Client creates with typed HTTP methods
    Given a ClientConfig with baseUrl "https://api.example.com" and headers
    When createClient is called with the config
    Then a QuillClient is returned with get, post, put, delete methods

  @FR-1
  Scenario: Client configuration includes timeout
    Given a ClientConfig with timeout 5000
    When createClient is called
    Then the client uses the configured timeout

  @FR-2
  Scenario: GET request is type-safe
    Given a QuillClient with baseUrl "https://api.example.com"
    When get<User>("/users/123") is called
    Then the return type is Promise<User>

  @FR-2
  Scenario: POST request is type-safe
    Given a QuillClient
    When post<User>("/users", { name: "Alice" }) is called
    Then the return type is Promise<User>

  @FR-2
  Scenario: PUT request is type-safe
    Given a QuillClient
    When put<User>("/users/123", { name: "Bob" }) is called
    Then the return type is Promise<User>

  @FR-2
  Scenario: DELETE request is type-safe
    Given a QuillClient
    When delete("/users/123") is called
    Then the request is dispatched as DELETE

  @FR-3
  Scenario: Request interceptor modifies headers
    Given a request interceptor that adds Authorization header
    When any request is dispatched
    Then the outgoing request contains the Authorization header

  @FR-4
  Scenario: Response interceptor transforms response
    Given a response interceptor that extracts x-request-id
    When a response is received
    Then the interceptor runs before the caller gets the result

  @FR-5
  Scenario: Error interceptor catches 5xx errors
    Given an error interceptor that logs errors
    When the server returns a 500 status code
    Then the error interceptor is invoked

  @FR-6
  Scenario: Retry with exponential backoff
    Given a client configured with maxRetries 3 and backoff
    When a request fails with a network error
    Then the client retries up to 3 times before giving up

  @FR-7
  Scenario: Mock utilities simulate HTTP responses
    Given a mock response { status: 200, body: { ok: true } }
    When get("/test") is called
    Then it resolves with body { ok: true } without a network call

Feature: Quillr Rust Crate (httpora-core)
  @FR-8
  Scenario: Token bucket rate limiter allows bursts
    Given a RateLimiter::token_bucket(10, 10.0)
    When check(1.0) is called 10 times
    Then all 10 calls succeed
    And the 11th call returns HttptoraError::RateLimited

  @FR-9
  Scenario: Fixed window rate limiter enforces limit
    Given a RateLimiter::fixed_window(5, 1.0)
    When check() is called 6 times
    Then the first 5 succeed
    And the 6th returns HttptoraError::RateLimited

  @FR-10
  Scenario: Circuit breaker transitions through three states
    Given a CircuitBreaker with failure_threshold 0.5
    When failures exceed the threshold
    Then before_request() returns HttptoraError::CircuitOpen
    And after reset_timeout, a probe request is allowed
    And a successful probe transitions to Closed
    And a failed probe transitions back to Open

  @FR-11
  Scenario: RetryLayer retries on failure
    Given a RetryLayer with max_attempts 3
    When an async operation fails twice then succeeds
    Then the result is returned without error

  @FR-12
  Scenario: RetryLayer skips non-idempotent methods
    Given a RetryLayer with retry_non_idempotent false
    When execute_for_method(HttpMethod::Post, f) is called
    Then it does NOT retry on failure

  @FR-13
  Scenario: CorsLayer handles preflight requests
    Given a CorsLayer with permissive config
    When an OPTIONS request arrives with Origin "https://example.com"
    Then a 204 response is returned with Access-Control-Allow-Origin set

  @FR-14
  Scenario: ResponseBuilder constructs typed responses
    Given a ResponseBuilder::json(200, payload)
    When the response is built
    Then HttpResponse has status 200 and Content-Type application/json

  @FR-14
  Scenario: ResponseBuilder builds 429 rate-limited response
    Given ResponseBuilder::rate_limited(60)
    Then the response has status 429 and Retry-After header

  @FR-15
  Scenario: RequestExtractor extracts Bearer token
    Given an HttpRequest with Authorization: Bearer mytoken
    When RequestExtractor::bearer_token is called
    Then it returns Some("mytoken")

  @FR-15
  Scenario: RequestExtractor parses JSON body
    Given an HttpRequest with JSON body {"key": "value"}
    When RequestExtractor::json_body is called
    Then it returns the parsed JSON value

  @FR-16
  Scenario: HttptoraError variants are displayable
    Given any HttptoraError variant
    When to_string() is called
    Then it produces a human-readable message

  @NFR-1
  Scenario: TypeScript strict mode compiles
    Given a TypeScript project with strict: true
    When tsc --noEmit is run
    Then no type errors are reported

  @NFR-3
  Scenario: Clock injection for deterministic time
    Given a mock Clock that returns controlled Instants
    When RateLimiter::token_bucket_with_clock is used
    Then time-dependent behaviour is deterministic

  @NFR-4
  Scenario: Default configurations are sensible
    Given a default RateLimitConfig
    Then capacity is 100, refill_rate is 10.0, strategy is TokenBucket
