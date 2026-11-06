---
layout: home

hero:
  name: Quillr
  text: Multi-language HTTP toolkit
  tagline: Rate limiting, retries, circuit breakers, interceptors, and mocking — for TypeScript and Rust.
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/KooshaPari/Quillr

features:
  - title: TypeScript client
    details: Type-safe HTTP client with interceptors, retries, and mocking. Published as @kooshapari/quillts.
  - title: Rust middleware
    details: Tower-compatible middleware — rate limiter, retry, circuit breaker, CORS. Published as the httpora-core crate.
  - title: Composable primitives
    details: Rate limiting, retries, circuit breakers, interceptors, and mocking as first-class citizens across both languages.
---

## What is Quillr?

Quillr is a multi-language HTTP toolkit for the [Phenotype](https://github.com/KooshaPari) ecosystem. It provides composable HTTP primitives — rate limiting, retries, circuit breakers, interceptors, and mocking — as first-class citizens in both **TypeScript** and **Rust**.

## Packages

| Package          | Language   | Description                                                       | Path                         |
| ---------------- | ---------- | ----------------------------------------------------------------- | ---------------------------- |
| `@kooshapari/quillts` | TypeScript | Type-safe HTTP client with interceptors, retries, and mocking     | `src/`                       |
| `httpora-core`   | Rust       | Tower-compatible middleware — rate limiter, retry, circuit breaker | `crates/httpora-core/`       |

## License

MIT — see [`LICENSE`](https://github.com/KooshaPari/Quillr/blob/main/LICENSE) for details.
