# ADR-001: Validation Approach Selection

**Document ID:** PHENOTYPE_VALIDATION_ADR_001  
**Status:** Accepted  
**Last Updated:** 2026-04-03  
**Author:** Phenotype Architecture Team  
**Supersedes:** N/A  
**Related:** ADR-002, ADR-003, VALIDATION_FRAMEWORKS_SOTA

---

## Table of Contents

1. [Context](#1-context)
2. [Decision](#2-decision)
3. [Consequences](#3-consequences)
4. [Alternatives Considered](#4-alternatives-considered)
5. [Implementation Notes](#5-implementation-notes)
6. [Cross-References](#6-cross-references)

---

## 1. Context

### 1.1 Problem Statement

The Phenotype ecosystem requires a robust, extensible validation library capable of:

- Validating JSON documents against JSON Schema definitions
- Validating YAML documents against JSON Schema definitions (via conversion)
- Supporting both synchronous and asynchronous validation patterns
- Aggregating validation errors for comprehensive reporting
- Integrating with other Phenotype ecosystem libraries
- Maintaining high performance for batch validation scenarios

### 1.2 Current State

The initial implementation of Phenotype.Validation provides:
- `ISchemaValidator<TSchema, TDocument>` generic interface
- `IJsonSchemaValidator` specialized interface with schema registry
- `JsonSchemaValidator` using NJsonSchema (v11.0.0)
- `YamlValidator` using YamlDotNet (v16.0.0) + Newtonsoft.Json
- `ValidationResult` with `IsValid`, `Errors`, and `Warnings` properties

### 1.3 Constraints

- Target framework: .NET 9.0
- Must support nullable reference types
- Must be compatible with the broader Phenotype ecosystem
- Performance requirements: <50ms for typical document validation
- Must handle documents up to 10MB in size
- Must provide actionable error messages

### 1.4 Stakeholders

- Phenotype platform team (primary consumers)
- Configuration management systems (YAML validation)
- API integration layer (JSON validation)
- CI/CD pipeline (schema validation in automation)

---

## 2. Decision

### 2.1 Primary Decision: Schema-Based Validation

We **accept** schema-based validation as the primary approach for Phenotype.Validation, using the following technology stack:

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| JSON Schema Engine | NJsonSchema | 11.0.0 | Mature, OpenAPI integration, existing dependency |
| YAML Parser | YamlDotNet | 16.0.0 | Industry standard, well-maintained |
| JSON Serializer | Newtonsoft.Json | 13.0.3 | Compatibility with YamlDotNet output |
| Test Framework | xUnit | 2.6.2 | Standard for .NET testing |

### 2.2 Architecture Decision

```
+--------------------------------------------------------------+
|                  Phenotype.Validation                         |
+--------------------------------------------------------------+
|                                                              |
|  +------------------+    +-------------------------------+  |
|  | ISchemaValidator |<---| IJsonSchemaValidator          |  |
|  | <TSchema, TDoc>  |    | (specialized interface)       |  |
|  +------------------+    +-------------------------------+  |
|           ^                          ^                     |
|           |                          |                     |
|  +--------+--------+      +----------+----------+          |
|  | YamlValidator   |      | JsonSchemaValidator |          |
|  |                 |      |                     |          |
|  | - YamlDotNet   |      | - NJsonSchema       |          |
|  | - Newtonsoft   |      | - Schema caching    |          |
|  +-----------------+      +---------------------+          |
|                                                              |
|  +------------------------------------------------------+  |
|  | ValidationResult                                     |  |
|  | - IsValid: bool                                      |  |
|  | - Errors: List<string>                               |  |
|  | - Warnings: List<string>                             |  |
|  | - Success() / Failure() factory methods              |  |
|  +------------------------------------------------------+  |
+--------------------------------------------------------------+
```

### 2.3 Validation Flow

```
  Input Document                    Output
  +-----------+              +------------------+
  |  JSON     |              |  ValidationResult|
  |  or YAML  |              |  - IsValid       |
  +-----+-----+              |  - Errors[]      |
        |                    |  - Warnings[]    |
        v                    +------------------+
  +-----------+
  | Schema    |
  | Validator |
  +-----+-----+
        |
        v
  +-----------+
  | JSON      |
  | Schema    |
  | Engine    |
  +-----------+
```

### 2.4 Interface Design Rationale

The generic `ISchemaValidator<TSchema, TDocument>` interface provides:
- Type safety for schema and document types
- Extensibility for future validator types (XML, TOML, etc.)
- Clear contract for both sync and async operations

```csharp
public interface ISchemaValidator<TSchema, TDocument>
{
    ValidationResult Validate(TSchema schema, TDocument document);
    Task<ValidationResult> ValidateAsync(
        TDocument document, 
        TSchema schema, 
        CancellationToken ct = default);
}
```

The specialized `IJsonSchemaValidator` interface provides:
- Schema registry functionality (named schemas)
- Convenience methods for common JSON validation patterns
- Backward compatibility with existing code

```csharp
public interface IJsonSchemaValidator : ISchemaValidator<string, string>
{
    void AddSchema(string name, string schemaContent);
    Task<ValidationResult> ValidateAgainstNamedSchemaAsync(
        string document, 
        string schemaName, 
        CancellationToken ct = default);
}
```

---

## 3. Consequences

### 3.1 Positive Consequences

1. **Proven Technology**: NJsonSchema and YamlDotNet are mature, well-tested libraries with active maintenance and large communities. This reduces risk and development time.

2. **OpenAPI Integration**: NJsonSchema's native OpenAPI support enables seamless integration with API-first development workflows used across the Phenotype ecosystem.

3. **Schema Reusability**: JSON Schema definitions can be shared across multiple tools, languages, and platforms, promoting consistency in the Phenotype ecosystem.

4. **Clear Separation of Concerns**: The interface-based design cleanly separates validation contracts from implementations, enabling easy testing and future extensions.

5. **Comprehensive Error Reporting**: JSON Schema validation provides detailed error messages with JSON paths, enabling precise error localization in documents.

6. **Async-First Design**: The async validation methods support high-throughput scenarios without blocking threads, critical for batch processing in CI/CD pipelines.

7. **Zero Configuration**: The validators work out of the box with sensible defaults, reducing boilerplate for common use cases.

8. **Type Safety**: Generic interfaces ensure compile-time type checking for schema and document types, catching errors early.

### 3.2 Negative Consequences

1. **NJsonSchema Limitations**: NJsonSchema supports up to Draft 7 of JSON Schema, not the latest Draft 2020-12. This means some modern JSON Schema features (dynamic `$ref`, `$anchor`, `prefixItems`) are unavailable.

2. **YAML Conversion Overhead**: Converting YAML to JSON for validation introduces additional processing overhead and potential data loss for YAML-specific features (anchors, aliases, multi-line strings).

3. **String-Based Errors**: Current `ValidationResult` uses `List<string>` for errors, which lacks structure and makes programmatic error handling difficult.

4. **Newtonsoft.Json Dependency**: Using Newtonsoft.Json alongside modern .NET (which prefers System.Text.Json) adds an additional dependency and potential serialization inconsistencies.

5. **No Fluent API**: Unlike FluentValidation, the current API does not provide a fluent interface for building validation rules programmatically.

6. **Limited Composability**: Validators cannot be easily composed or chained without additional infrastructure.

7. **Schema Cache Thread Safety**: The current `_schemaCache` dictionary in `JsonSchemaValidator` is not thread-safe (`Dictionary` vs `ConcurrentDictionary`), which could cause issues in concurrent scenarios.

8. **Blocking Sync Methods**: The synchronous `Validate` method uses `.GetAwaiter().GetResult()` which can cause thread pool starvation under load.

### 3.3 Neutral Consequences

1. **Learning Curve**: Developers unfamiliar with JSON Schema will need to learn the specification, though this is a one-time investment with broad applicability.

2. **Dependency Management**: Three external dependencies (NJsonSchema, YamlDotNet, Newtonsoft.Json) must be tracked and updated, though this is standard for .NET libraries.

3. **Version Pinning**: The library is tied to specific major versions of its dependencies, which may require coordination when other Phenotype libraries update.

---

## 4. Alternatives Considered

### 4.1 Alternative A: Data Annotations

**Description**: Use `System.ComponentModel.DataAnnotations` for validation.

**Rejected Because**:
- Not suitable for document-level validation (JSON/YAML)
- Limited composability and testability
- No async support
- Poor error aggregation capabilities

### 4.2 Alternative B: FluentValidation

**Description**: Use FluentValidation for all validation needs.

**Rejected Because**:
- Designed for domain object validation, not document validation
- No native JSON Schema support
- Would require custom adapters for schema-based validation
- Better suited as a complementary library for domain validation (future phase)

### 4.3 Alternative C: JsonSchema.Net

**Description**: Use JsonSchema.Net instead of NJsonSchema.

**Deferred Because**:
- JsonSchema.Net supports Draft 2020-12 (more modern)
- However, NJsonSchema provides OpenAPI integration needed by Phenotype
- Migration path exists for future (see ADR-002)
- Will re-evaluate when OpenAPI 3.1 adoption increases

### 4.4 Alternative D: Custom Validation Engine

**Description**: Build a custom validation engine from scratch.

**Rejected Because**:
- Reinventing well-solved problems
- Significant development and maintenance cost
- JSON Schema is an industry standard with broad tooling support
- Custom engines lack the testing and edge case coverage of established libraries

---

## 5. Implementation Notes

### 5.1 Thread Safety Fix Required

The current implementation has a thread safety issue in `JsonSchemaValidator`:

```csharp
// Current (unsafe):
private readonly Dictionary<string, JsonSchema> _schemaCache = new();

// Recommended (safe):
private readonly ConcurrentDictionary<string, JsonSchema> _schemaCache = new();
```

### 5.2 Error Format Standardization

Error messages should follow a consistent format:

```
[<path>] <error-kind>: <details>
```

Example:
```
[properties.email] Format: Value does not match email format
[properties.age] Type: Expected integer but found string
```

### 5.3 Schema Validation

Schemas themselves should be validated before use:

```csharp
public ValidationResult RegisterSchema(string name, string schemaContent)
{
    // Validate the schema is valid JSON Schema
    var schemaValidation = ValidateSchemaSyntax(schemaContent);
    if (!schemaValidation.IsValid)
        return schemaValidation;
    
    // Parse and cache
    var schema = JsonSchema.FromJsonAsync(schemaContent).GetAwaiter().GetResult();
    _schemaCache[name] = schema;
    return ValidationResult.Success();
}
```

### 5.4 Performance Optimization

Schema parsing should be cached:

```csharp
public async Task<ValidationResult> ValidateAsync(string document, string schema, CancellationToken ct = default)
{
    var schemaHash = ComputeSchemaHash(schema);
    var jsonSchema = await _schemaCache.GetOrAddAsync(schemaHash, 
        async () => await JsonSchema.FromJsonAsync(schema, ct));
    
    var errors = jsonSchema.Validate(document);
    // ...
}
```

---

## 7. Risk Assessment

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| NJsonSchema deprecation | Low | High | Monitor project activity; JsonSchema.Net migration path exists |
| Breaking changes in dependencies | Medium | Medium | Pin versions; test against dependency updates |
| Performance degradation at scale | Medium | Medium | Implement caching; benchmark regularly |
| Thread safety issues | High | Medium | Replace Dictionary with ConcurrentDictionary |
| YAML conversion data loss | Low | Low | Test YAML-specific features; document limitations |

### 7.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Schema versioning conflicts | Medium | Medium | Implement schema registry with versioning |
| Large document processing | Medium | Low | Enforce size limits; streaming support |
| Error message confusion | Low | Low | Standardize error format; provide examples |
| Developer misuse | Medium | Low | Comprehensive documentation; code examples |

### 7.3 Migration Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking changes in future versions | Low | High | Semantic versioning; migration guides |
| Dependency conflicts with other libraries | Low | Medium | Isolate dependencies; use assembly binding |
| Performance regression after updates | Medium | Medium | Benchmark suite; performance gates in CI |

---

## 8. Compliance and Standards

### 8.1 JSON Schema Compliance

The library supports JSON Schema through NJsonSchema, which implements:

- Draft 4 (2013) - Full support
- Draft 6 (2017) - Full support
- Draft 7 (2018) - Full support
- Draft 2019-09 - Partial support
- Draft 2020-12 - Not supported

### 8.2 RFC Compliance

| RFC | Description | Compliance |
|-----|-------------|------------|
| RFC 7159 | The JavaScript Object Notation (JSON) Data Interchange Format | Full |
| RFC 7493 | The I-JSON Message Format | Partial |
| RFC 8259 | The JavaScript Object Notation (JSON) Data Interchange Format (obsoletes RFC 7159) | Full |

### 8.3 Industry Standards

| Standard | Relevance | Compliance |
|----------|-----------|------------|
| OpenAPI 3.0 | API specification | Full (via NJsonSchema) |
| OpenAPI 3.1 | API specification (JSON Schema 2020-12) | Partial |
| AsyncAPI 2.x | Event-driven API specification | Partial |

---

## 9. Validation Approach Comparison

### 9.1 Decision Matrix

```
                    Schema-Based    FluentValidation    Data Annotations    Custom Engine
Expressiveness        ★★★★☆            ★★★★★              ★★★☆☆              ★★★★☆
Composability         ★★★☆☆            ★★★★★              ★★☆☆☆              ★★★★☆
Performance           ★★★☆☆            ★★★★☆              ★★★☆☆              ★★★★★
Testability           ★★★☆☆            ★★★★★              ★★☆☆☆              ★★★★☆
Error Reporting       ★★★★☆            ★★★★☆              ★★☆☆☆              ★★★★★
Ecosystem             ★★★★☆            ★★★★★              ★★★★★              ★★☆☆☆
Integration           ★★★★☆            ★★★★☆              ★★★★★              ★★★☆☆
Learning Curve        ★★★★☆            ★★★★☆              ★★★★★              ★★☆☆☆
Extensibility         ★★★★☆            ★★★★★              ★★☆☆☆              ★★★★★
─────────────────────────────────────────────────────────────────────────────────────────
Weighted Score        3.7              4.6                3.1                3.8
```

### 9.2 Why Schema-Based Won

Schema-based validation was selected because:

1. **Document-Centric**: Phenotype.Validation primarily validates documents (JSON/YAML), not domain objects
2. **Portability**: JSON Schema is language-agnostic, enabling cross-platform validation
3. **Declarative**: Schemas are data, not code, enabling external management and versioning
4. **Ecosystem Fit**: Aligns with Phenotype's configuration-first approach
5. **Tooling**: Rich ecosystem of schema editors, validators, and generators

### 9.3 When to Revisit

This decision should be revisited when:

- OpenAPI 3.1 adoption requires Draft 2020-12 support
- Domain object validation becomes a primary use case
- Performance requirements exceed NJsonSchema capabilities
- Business rule validation complexity justifies a rule engine

---

## 10. Implementation Checklist

### 10.1 Immediate Actions

- [ ] Replace `Dictionary` with `ConcurrentDictionary` in `JsonSchemaValidator`
- [ ] Add XML documentation to all public APIs
- [ ] Add comprehensive unit tests for all validators
- [ ] Add integration tests with real-world schemas
- [ ] Set up BenchmarkDotNet for performance tracking

### 10.2 Short-Term Actions (Next Sprint)

- [ ] Add schema validation on registration
- [ ] Implement error code constants
- [ ] Add validation limits (size, depth)
- [ ] Create test data directory with sample schemas
- [ ] Add CI/CD pipeline for automated testing

### 10.3 Medium-Term Actions (Next Quarter)

- [ ] Evaluate JsonSchema.Net migration
- [ ] Implement structured error types (ADR-003)
- [ ] Add error formatters (console, JSON)
- [ ] Implement rule engine foundation (ADR-002)
- [ ] Add performance benchmarks to CI

---

## 6. Cross-References

| Document | Relationship | Description |
|----------|-------------|-------------|
| ADR-002 | Extends | Rule Engine Architecture builds on this validation approach |
| ADR-003 | Depends | Error Aggregation Strategy depends on the validation result structure |
| VALIDATION_FRAMEWORKS_SOTA | Informs | SOTA research informed this decision |
| SPEC.md | Specifies | Full specification of the validation library |

---

*This ADR was accepted by the Phenotype Architecture Team on 2026-04-03.*
