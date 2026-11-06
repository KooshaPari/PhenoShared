# PRD: quill — Type-Safe HTTP Client for TypeScript

## Overview
`quill` is a type-safe HTTP client for TypeScript featuring request/response interceptors, automatic retry with exponential backoff, and built-in test mocking utilities.

## Problem Statement
TypeScript HTTP clients (fetch, axios) lack type safety at the call site. Error handling is inconsistent. Retry logic is reimplemented per project. Test mocking requires complex setup. `quill` provides a unified, type-safe HTTP client with production-ready defaults.

## Goals
1. Full TypeScript type inference for request payloads and response types
2. Interceptor pipeline (transform requests/responses, add auth headers)
3. Automatic retry with exponential backoff and jitter
4. Response error handling with typed error objects
5. Built-in test mock utilities (no network in tests)

## Epics

### E1: Core Client
- E1.1: `createClient(config)` factory
- E1.2: GET, POST, PUT, PATCH, DELETE, HEAD methods
- E1.3: Type-safe response: `get<T>(url) -> Promise<T>`
- E1.4: Request/response timeout
- E1.5: Base URL and default headers

### E2: Interceptors
- E2.1: Request interceptors (modify before send)
- E2.2: Response interceptors (modify before return)
- E2.3: Error interceptors (handle errors before throw)
- E2.4: Interceptor ordering and composition

### E3: Retry
- E3.1: Configurable retry count
- E3.2: Exponential backoff with jitter
- E3.3: Retry condition (by status code, by error type)
- E3.4: Retry events (onRetry callback)

### E4: Error Handling
- E4.1: `HttpError` type with status, url, method, body
- E4.2: Network error vs HTTP error distinction
- E4.3: Timeout error type
- E4.4: Error message formatting

### E5: Mocking
- E5.1: `createMockClient()` for test environments
- E5.2: Route registration: `mock.on("GET /users/:id").reply(200, data)`
- E5.3: Assert all registered mocks were called
- E5.4: Passthrough mode (allow certain routes to real network)
