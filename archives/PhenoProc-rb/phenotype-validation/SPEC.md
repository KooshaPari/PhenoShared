# Phenotype.Validation - Comprehensive Specification

**Document ID:** PHENOTYPE_VALIDATION_SPEC_001  
**Status:** Active Research  
**Last Updated:** 2026-04-03  
**Author:** Phenotype Architecture Team

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Functionality Specification](#3-functionality-specification)
4. [Technical Architecture](#4-technical-architecture)
5. [API Reference](#5-api-reference)
6. [Error Handling](#6-error-handling)
7. [Security](#7-security)
8. [Performance](#8-performance)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment and Distribution](#10-deployment-and-distribution)
11. [Migration Guide](#11-migration-guide)
12. [Future Roadmap](#12-future-roadmap)
13. [Appendices](#13-appendices)

---

## 1. Project Overview

### 1.1 Purpose

Phenotype.Validation is a .NET 9.0 validation library that provides schema-based validation for JSON and YAML documents within the Phenotype ecosystem. It serves as the foundational validation layer for configuration files, API contracts, data pipelines, and document processing workflows.

### 1.2 Scope

The library addresses:

- **JSON Schema Validation**: Validating JSON documents against JSON Schema definitions
- **YAML Schema Validation**: Validating YAML documents against JSON Schema definitions (via JSON conversion)
- **Schema Management**: Registering, caching, and retrieving named schemas
- **Error Reporting**: Structured error reporting with path information
- **Extensibility**: Interface-based design for custom validators

### 1.3 Non-Goals

The following are explicitly out of scope for the current version:

- Domain object validation (use FluentValidation)
- XML Schema validation
- Real-time form validation
- Business rule engine (planned for future, see ADR-002)
- Data annotation replacement
- ASP.NET Core model binding integration

### 1.4 Target Audience

- Phenotype platform developers
- Configuration management systems
- CI/CD pipeline engineers
- API integration developers
- Data pipeline engineers

### 1.5 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Runtime | .NET | 9.0 | Target framework |
| Language | C# | 13 | Implementation language |
| JSON Schema | NJsonSchema | 11.0.0 | Schema validation engine |
| YAML Parser | YamlDotNet | 16.0.0 | YAML document parsing |
| JSON Serializer | Newtonsoft.Json | 13.0.3 | YAML-to-JSON conversion |
| Test Framework | xUnit | 2.6.2 | Unit testing |
| Build System | dotnet CLI | 9.0 | Build and test |

### 1.6 Project Structure

```
phenotype-validation/
├── Phenotype.Validation.sln          # Solution file
├── SPEC.md                           # This specification
├── docs/
│   ├── research/
│   │   └── VALIDATION_FRAMEWORKS_SOTA.md  # State-of-the-art research
│   └── adr/
│       ├── ADR-001-validation-approach.md # Validation approach decision
│       ├── ADR-002-rule-engine.md         # Rule engine architecture
│       └── ADR-003-error-aggregation.md   # Error aggregation strategy
├── src/
│   └── Phenotype.Validation/
│       ├── Phenotype.Validation.csproj    # Library project
│       ├── ISchemaValidator.cs            # Core interfaces
│       ├── JsonSchemaValidator.cs         # JSON Schema implementation
│       ├── YamlValidator.cs               # YAML validation implementation
│       └── ValidationResult.cs            # Result type
└── tests/
    ├── Phenotype.Validation.Tests.csproj  # Test project
    └── SchemaValidatorTests.cs            # Unit tests
```

### 1.7 Design Principles

1. **Schema-First**: Validation is driven by formal schema definitions, not imperative code
2. **Async-First**: All I/O-bound operations support async/await
3. **Error Accumulation**: Collect all errors, do not fail fast by default
4. **Interface-Driven**: Contracts are defined by interfaces, enabling testability and extensibility
5. **Zero Configuration**: Validators work out of the box with sensible defaults
6. **Thread Safety**: All public APIs are thread-safe for concurrent use
7. **Backward Compatibility**: API changes follow semantic versioning

### 1.8 Ecosystem Integration

```
+--------------------------------------------------------------+
|                    Phenotype Ecosystem                        |
+--------------------------------------------------------------+
|                                                              |
|  +------------------+    +-------------------------------+  |
|  | Phenotype.Config |    | Phenotype.API                 |  |
|  | (YAML configs)   |    | (JSON request/response)       |  |
|  +--------+---------+    +---------------+---------------+  |
|           |                                |                |
|           | validates                      | validates      |
|           v                                v                |
|  +------------------------------------------------------+  |
|  |              Phenotype.Validation                     |  |
|  |                                                       |  |
|  |  - JSON Schema validation                            |  |
|  |  - YAML Schema validation                            |  |
|  |  - Schema registry                                   |  |
|  |  - Error aggregation                                 |  |
|  +------------------------------------------------------+  |
|           |                                |                |
|           | validates                      | validates      |
|           v                                v                |
|  +--------+---------+    +---------------+---------------+  |
|  | Phenotype.Data   |    | Phenotype.Pipeline              |  |
|  | (data files)     |    | (data transformations)          |  |
|  +------------------+    +-------------------------------+  |
+--------------------------------------------------------------+
```

---

## 2. Architecture

### 2.1 Layered Architecture

```
+--------------------------------------------------------------+
|                    Layered Architecture                       |
+--------------------------------------------------------------+
|                                                              |
|  +------------------------------------------------------+  |
|  | Layer 4: Integration Layer                           |  |
|  | - DI registration extensions                         |  |
|  | - ASP.NET Core middleware (future)                   |  |
|  | - CLI integration (future)                           |  |
|  +------------------------------------------------------+  |
|           |                                                |
|  +------------------------------------------------------+  |
|  | Layer 3: Validation Pipeline Layer                   |  |
|  | - ValidationPipeline                                 |  |
|  | - IValidationStep                                    |  |
|  | - Error aggregation                                  |  |
|  | - Rule engine (ADR-002)                              |  |
|  +------------------------------------------------------+  |
|           |                                                |
|  +------------------------------------------------------+  |
|  | Layer 2: Validator Layer                             |  |
|  | - JsonSchemaValidator                                |  |
|  | - YamlValidator                                      |  |
|  | - Custom validators                                  |  |
|  | - Schema registry                                    |  |
|  +------------------------------------------------------+  |
|           |                                                |
|  +------------------------------------------------------+  |
|  | Layer 1: Core Layer                                  |  |
|  | - ISchemaValidator<TSchema, TDocument>               |  |
|  | - IJsonSchemaValidator                               |  |
|  | - ValidationResult                                   |  |
|  | - IValidationIssue / ValidationError / Warning       |  |
|  +------------------------------------------------------+  |
|           |                                                |
|  +------------------------------------------------------+  |
|  | Layer 0: External Dependencies                       |  |
|  | - NJsonSchema                                        |  |
|  | - YamlDotNet                                         |  |
|  | - Newtonsoft.Json                                    |  |
|  +------------------------------------------------------+  |
+--------------------------------------------------------------+
```

### 2.2 Component Diagram

```
+--------------------------------------------------------------+
|                    Component Diagram                          |
+--------------------------------------------------------------+
|                                                              |
|  +------------------+    +-------------------------------+  |
|  | ISchemaValidator |    | IJsonSchemaValidator          |  |
|  | <TSchema, TDoc>  |    |                               |  |
|  |                  |    | Extends:                      |  |
|  | + Validate()     |    |   ISchemaValidator<string,    |  |
|  | + ValidateAsync()|    |     string>                   |  |
|  +--------+---------+    |                               |  |
|           ^              | + AddSchema()                 |  |
|           |              | + ValidateAgainstNamedSchema()|  |
|           | implements   +---------------+---------------+  |
|           |                                |                |
|  +--------+--------+      +----------------+-------------+  |
|  | YamlValidator   |      | JsonSchemaValidator          |  |
|  |                 |      |                              |  |
|  | Dependencies:   |      | Dependencies:                |  |
|  | - IDeserializer |      | - NJsonSchema                |  |
|  | - IJsonSchema   |      | - Schema cache               |  |
|  |   Validator     |      |                              |  |
|  +-----------------+      +------------------------------+  |
|                                                              |
|  +------------------------------------------------------+  |
|  | ValidationResult                                     |  |
|  |                                                      |  |
|  | Properties:                                          |  |
|  | - IsValid: bool                                      |  |
|  | - Errors: List<string>                               |  |
|  | - Warnings: List<string>                             |  |
|  | - Issues: IReadOnlyList<IValidationIssue> (future)   |  |
|  |                                                      |  |
|  | Factory Methods:                                     |  |
|  | - Success(): ValidationResult                        |  |
|  | - Failure(errors): ValidationResult                  |  |
|  +------------------------------------------------------+  |
+--------------------------------------------------------------+
```

### 2.3 Data Flow

#### 2.3.1 JSON Validation Flow

```
  JSON Document          Schema String
  +-----------+          +-----------+
  | {         |          | {         |
  |   "name": |          |   "type": |
  |   "test"  |          |   "object"|
  | }         |          | }         |
  +-----+-----+          +-----+-----+
        |                      |
        |    +-----------------+
        |    |
        v    v
  +-----------+
  | JsonSchema|
  | Validator |
  |           |
  | 1. Parse  |
  |    schema |
  | 2. Parse  |
  |    doc    |
  | 3. Eval   |
  |    rules  |
  | 4. Collect|
  |    errors |
  +-----+-----+
        |
        v
  +-----------+
  |Validation |
  | Result    |
  |           |
  | IsValid:  |
  |   true    |
  | Errors: []|
  +-----------+
```

#### 2.3.2 YAML Validation Flow

```
  YAML Document          Schema String
  +-----------+          +-----------+
  | name: test|          | {         |
  | age: 25   |          |   "type": |
  +-----+-----+          |   "object"|
        |                | }         |
        |                +-----+-----+
        v                      |
  +-----------+                |
  | YamlDotNet|                |
  | Deserial. |                |
  +-----+-----+                |
        |                      |
        v                      |
  +-----------+                |
  | Newtonsoft|                |
  | Serialize |                |
  +-----+-----+                |
        |                      |
        v                      v
  +-----------+          +-----------+
  | JSON      |--------->| JsonSchema|
  | String    |          | Validator |
  +-----------+          +-----+-----+
                                |
                                v
                          +-----------+
                          |Validation |
                          | Result    |
                          +-----------+
```

### 2.4 Dependency Graph

```
  Phenotype.Validation
        |
        +-- NJsonSchema (11.0.0)
        |       |
        |       +-- Namotion.Reflection
        |       +-- Newtonsoft.Json (transitive)
        |
        +-- YamlDotNet (16.0.0)
        |
        +-- Newtonsoft.Json (13.0.3)

  Phenotype.Validation.Tests
        |
        +-- Phenotype.Validation (project ref)
        +-- xUnit (2.6.2)
        +-- xUnit.runner.visualstudio (2.5.4)
        +-- Microsoft.NET.Test.Sdk (17.8.0)
```

### 2.5 Thread Safety Model

| Component | Thread Safety | Notes |
|-----------|--------------|-------|
| `JsonSchemaValidator` | Partial | Schema cache uses `Dictionary` (not thread-safe) |
| `YamlValidator` | Yes | Stateless, depends on thread-safe validator |
| `ValidationResult` | Yes | Immutable after creation |
| `_yamlDeserializer` | Yes | YamlDotNet deserializer is thread-safe |

**Known Issue**: The `_schemaCache` in `JsonSchemaValidator` should use `ConcurrentDictionary` for thread safety. This is tracked for resolution.

---

## 3. Functionality Specification

### 3.1 JSON Schema Validation

#### 3.1.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-001 | Validate JSON document against JSON Schema string | P0 | Implemented |
| F-002 | Validate JSON document asynchronously | P0 | Implemented |
| F-003 | Register named schemas for reuse | P0 | Implemented |
| F-004 | Validate against named schema | P0 | Implemented |
| F-005 | Return structured error messages with paths | P0 | Implemented |
| F-006 | Support JSON Schema Draft 4/6/7 | P1 | Implemented (via NJsonSchema) |
| F-007 | Cache parsed schemas for performance | P1 | Implemented |
| F-008 | Handle invalid schema gracefully | P1 | Implemented |
| F-009 | Handle invalid JSON document gracefully | P1 | Implemented |
| F-010 | Support cancellation tokens | P1 | Implemented |

#### 3.1.2 Supported JSON Schema Keywords

| Keyword | Support | Notes |
|---------|---------|-------|
| `type` | Full | object, array, string, number, integer, boolean, null |
| `properties` | Full | Object property definitions |
| `required` | Full | Required property list |
| `additionalProperties` | Full | Additional property control |
| `patternProperties` | Full | Regex-based property names |
| `items` | Full | Array item schema |
| `minItems` / `maxItems` | Full | Array size constraints |
| `uniqueItems` | Full | Array uniqueness |
| `minLength` / `maxLength` | Full | String length constraints |
| `pattern` | Full | String regex pattern |
| `format` | Full | Email, URI, date-time, etc. |
| `minimum` / `maximum` | Full | Numeric range |
| `exclusiveMinimum` / `exclusiveMaximum` | Full | Exclusive numeric range |
| `multipleOf` | Full | Numeric divisibility |
| `enum` | Full | Enumeration values |
| `const` | Full | Constant value |
| `default` | Partial | Not validated, informational only |
| `definitions` | Full | Schema definitions (Draft 4) |
| `$ref` | Full | Schema references |
| `$defs` | Partial | Schema definitions (Draft 2019-09+) |
| `allOf` | Full | All schemas must match |
| `anyOf` | Full | At least one schema must match |
| `oneOf` | Full | Exactly one schema must match |
| `not` | Full | Schema must not match |
| `if` / `then` / `else` | Full | Conditional schemas (Draft 7+) |
| `dependencies` | Full | Property dependencies |
| `propertyNames` | Full | Property name validation (Draft 6+) |
| `contains` | Full | Array contains validation (Draft 6+) |

#### 3.1.3 Error Format

JSON Schema validation errors follow this format:

```
[<json-path>] <error-kind>: <details>
```

Examples:
```
[properties.email] Format: Value does not match email format
[properties.age] Type: Expected integer but found string
[items[2].name] Required: Required property is missing
[properties.tags] Type: Expected array but found string
```

### 3.2 YAML Schema Validation

#### 3.2.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-011 | Parse YAML document | P0 | Implemented |
| F-012 | Convert YAML to JSON for validation | P0 | Implemented |
| F-013 | Validate YAML against JSON Schema | P0 | Implemented |
| F-014 | Return YAML-specific parse errors | P0 | Implemented |
| F-015 | Support YAML anchors and aliases | P1 | Implemented (via YamlDotNet) |
| F-016 | Support multi-line strings | P1 | Implemented (via YamlDotNet) |
| F-017 | Handle invalid YAML gracefully | P1 | Implemented |

#### 3.2.2 YAML Conversion Pipeline

```
  YAML Document
  +-----------+
  | key: value|
  | list:     |
  |   - item1 |
  |   - item2 |
  +-----+-----+
        |
        | YamlDotNet Deserialize
        v
  +-----------+
  | .NET      |
  | Object    |
  | (object)  |
  +-----+-----+
        |
        | Newtonsoft.Json Serialize
        v
  +-----------+
  | JSON      |
  | String    |
  +-----+-----+
        |
        | JsonSchemaValidator.Validate
        v
  +-----------+
  |Validation |
  | Result    |
  +-----------+
```

#### 3.2.3 YAML-Specific Error Handling

YAML parse errors are reported with line and column information:

```
Invalid YAML: while parsing a block mapping at line 3, column 5
Invalid YAML: could not find expected ':' at line 7, column 1
Invalid YAML: found unexpected end of stream at line 12, column 1
```

### 3.3 Schema Registry

#### 3.3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-018 | Register schemas by name | P0 | Implemented |
| F-019 | Retrieve schemas by name | P0 | Implemented |
| F-020 | Validate against named schema | P0 | Implemented |
| F-021 | Handle missing schema gracefully | P1 | Implemented |
| F-022 | Schema versioning | P2 | Not implemented |
| F-023 | Schema validation (validate the schema itself) | P2 | Not implemented |
| F-024 | Schema deprecation | P2 | Not implemented |

#### 3.3.2 Schema Registry Interface

```csharp
public interface ISchemaRegistry
{
    void Register(string name, string schemaContent);
    Task<JsonSchema> GetSchemaAsync(string name, CancellationToken ct = default);
    bool HasSchema(string name);
    IReadOnlyList<string> GetSchemaNames();
    void RemoveSchema(string name);
    void Clear();
}
```

### 3.4 Validation Result

#### 3.4.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-025 | Indicate validation success/failure | P0 | Implemented |
| F-026 | Collect error messages | P0 | Implemented |
| F-027 | Collect warning messages | P0 | Implemented |
| F-028 | Factory methods for success/failure | P0 | Implemented |
| F-029 | Structured error objects | P1 | Proposed (ADR-003) |
| F-030 | Error grouping | P2 | Proposed (ADR-003) |
| F-031 | Error deduplication | P2 | Proposed (ADR-003) |
| F-032 | Error formatting | P2 | Proposed (ADR-003) |

### 3.5 Future Functionality (Not Implemented)

#### 3.5.1 Rule Engine (ADR-002)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-033 | Expression-based rule definitions | P1 | Not implemented |
| F-034 | Rule composition | P1 | Not implemented |
| F-035 | Conditional rule execution | P1 | Not implemented |
| F-036 | Async rule evaluation | P1 | Not implemented |
| F-037 | Rule sets | P1 | Not implemented |
| F-038 | Rule versioning | P2 | Not implemented |
| F-039 | Rule metadata | P2 | Not implemented |

#### 3.5.2 Validation Pipeline

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-040 | Multi-step validation pipeline | P1 | Not implemented |
| F-041 | Fail-fast mode | P1 | Not implemented |
| F-042 | Error aggregation strategies | P1 | Not implemented |
| F-043 | Pipeline context passing | P2 | Not implemented |

#### 3.5.3 Additional Validators

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F-044 | XML Schema validation | P2 | Not implemented |
| F-045 | TOML validation | P3 | Not implemented |
| F-046 | Custom format validators | P2 | Not implemented |
| F-047 | FluentValidation integration | P2 | Not implemented |

---

## 4. Technical Architecture

### 4.1 Core Interfaces

#### 4.1.1 ISchemaValidator<TSchema, TDocument>

The foundational interface for all validators in the library.

```csharp
namespace Phenotype.Validation;

/// <summary>
/// Generic interface for schema-based validators.
/// </summary>
/// <typeparam name="TSchema">The type of the schema definition.</typeparam>
/// <typeparam name="TDocument">The type of the document to validate.</typeparam>
public interface ISchemaValidator<TSchema, TDocument>
{
    /// <summary>
    /// Validates a document against a schema synchronously.
    /// </summary>
    /// <param name="schema">The schema definition.</param>
    /// <param name="document">The document to validate.</param>
    /// <returns>A ValidationResult indicating success or failure.</returns>
    ValidationResult Validate(TSchema schema, TDocument document);

    /// <summary>
    /// Validates a document against a schema asynchronously.
    /// </summary>
    /// <param name="document">The document to validate.</param>
    /// <param name="schema">The schema definition.</param>
    /// <param name="ct">Cancellation token.</param>
    /// <returns>A ValidationResult indicating success or failure.</returns>
    Task<ValidationResult> ValidateAsync(
        TDocument document, 
        TSchema schema, 
        CancellationToken ct = default);
}
```

**Design Rationale**:
- Generic parameters allow type-safe validation for any schema/document type combination
- Both sync and async methods support different usage patterns
- Parameter order differs between sync and async (document first for async) to align with common async patterns

#### 4.1.2 IJsonSchemaValidator

Specialized interface for JSON Schema validation with schema registry support.

```csharp
namespace Phenotype.Validation;

/// <summary>
/// Specialized interface for JSON Schema validation with named schema support.
/// </summary>
public interface IJsonSchemaValidator : ISchemaValidator<string, string>
{
    /// <summary>
    /// Registers a schema with a name for reuse.
    /// </summary>
    /// <param name="name">The unique name for the schema.</param>
    /// <param name="schemaContent">The JSON Schema content.</param>
    void AddSchema(string name, string schemaContent);

    /// <summary>
    /// Validates a document against a previously registered named schema.
    /// </summary>
    /// <param name="document">The JSON document to validate.</param>
    /// <param name="schemaName">The name of the registered schema.</param>
    /// <param name="ct">Cancellation token.</param>
    /// <returns>A ValidationResult indicating success or failure.</returns>
    Task<ValidationResult> ValidateAgainstNamedSchemaAsync(
        string document, 
        string schemaName, 
        CancellationToken ct = default);
}
```

**Design Rationale**:
- Extends `ISchemaValidator<string, string>` for JSON-specific validation
- Schema registry enables reuse without reparsing
- Named schema validation simplifies common validation patterns

### 4.2 Implementations

#### 4.2.1 JsonSchemaValidator

```csharp
namespace Phenotype.Validation;

/// <summary>
/// JSON Schema validator using NJsonSchema.
/// </summary>
public class JsonSchemaValidator : IJsonSchemaValidator
{
    private readonly Dictionary<string, JsonSchema> _schemaCache = new();
    
    public ValidationResult Validate(string schema, string document)
    {
        return ValidateAsync(document, schema).GetAwaiter().GetResult();
    }
    
    public async Task<ValidationResult> ValidateAsync(
        string document, 
        string schema, 
        CancellationToken ct = default)
    {
        try
        {
            var jsonSchema = await JsonSchema.FromJsonAsync(schema, ct);
            var errors = jsonSchema.Validate(document);
            
            if (!errors.Any())
                return ValidationResult.Success();
                
            return ValidationResult.Failure(
                errors.Select(e => $"[{e.Path}] {e.Kind}: {e.Property}"));
        }
        catch (Exception ex)
        {
            return ValidationResult.Failure(new[] { ex.Message });
        }
    }
    
    public void AddSchema(string name, string schemaContent)
    {
        var schema = JsonSchema.FromJsonAsync(schemaContent)
            .GetAwaiter().GetResult();
        _schemaCache[name] = schema;
    }
    
    public async Task<ValidationResult> ValidateAgainstNamedSchemaAsync(
        string document, 
        string schemaName, 
        CancellationToken ct = default)
    {
        if (!_schemaCache.TryGetValue(schemaName, out var schema))
            return ValidationResult.Failure(
                new[] { $"Schema '{schemaName}' not found" });
            
        var errors = schema.Validate(document);
        if (!errors.Any()) return ValidationResult.Success();
        return ValidationResult.Failure(errors.Select(e => $"[{e.Path}] {e.Kind}"));
    }
}
```

**Implementation Notes**:
- Uses NJsonSchema's `JsonSchema.FromJsonAsync()` for schema parsing
- Uses `JsonSchema.Validate()` for document validation
- Error formatting includes JSON path, error kind, and property name
- Schema cache enables reuse without reparsing
- Thread safety issue: `_schemaCache` should be `ConcurrentDictionary`

#### 4.2.2 YamlValidator

```csharp
namespace Phenotype.Validation;

/// <summary>
/// YAML validator that converts YAML to JSON and validates against JSON Schema.
/// </summary>
public class YamlValidator : ISchemaValidator<string, string>
{
    private readonly IJsonSchemaValidator _jsonValidator;
    private readonly IDeserializer _yamlDeserializer = new DeserializerBuilder().Build();
    
    public YamlValidator(IJsonSchemaValidator? jsonValidator = null)
    {
        _jsonValidator = jsonValidator ?? new JsonSchemaValidator();
    }
    
    public ValidationResult Validate(string schema, string document)
    {
        try
        {
            _yamlDeserializer.Deserialize<object>(document);
            var yamlObject = _yamlDeserializer.Deserialize<object>(document);
            var json = JsonConvert.SerializeObject(yamlObject);
            return _jsonValidator.Validate(json, schema);
        }
        catch (Exception ex)
        {
            return ValidationResult.Failure(new[] { $"Invalid YAML: {ex.Message}" });
        }
    }
    
    public Task<ValidationResult> ValidateAsync(
        string document, 
        string schema, 
        CancellationToken ct = default)
    {
        return Task.FromResult(Validate(schema, document));
    }
}
```

**Implementation Notes**:
- Uses YamlDotNet for YAML parsing
- Converts to JSON via Newtonsoft.Json for schema validation
- Delegates to `IJsonSchemaValidator` for actual validation
- Constructor injection enables testing with mock validators
- Double deserialization in `Validate()` is a minor inefficiency (first call validates YAML syntax, second parses)

### 4.3 Result Types

#### 4.3.1 ValidationResult

```csharp
namespace Phenotype.Validation;

/// <summary>
/// Represents the result of a validation operation.
/// </summary>
public class ValidationResult
{
    /// <summary>
    /// Indicates whether the validation passed.
    /// </summary>
    public bool IsValid { get; set; }
    
    /// <summary>
    /// Collection of error messages.
    /// </summary>
    public List<string> Errors { get; set; } = new();
    
    /// <summary>
    /// Collection of warning messages.
    /// </summary>
    public List<string> Warnings { get; set; } = new();
    
    /// <summary>
    /// Creates a successful validation result.
    /// </summary>
    public static ValidationResult Success() => new() { IsValid = true };
    
    /// <summary>
    /// Creates a failed validation result with errors.
    /// </summary>
    public static ValidationResult Failure(IEnumerable<string> errors) => 
        new() { IsValid = false, Errors = errors.ToList() };
}
```

**Design Rationale**:
- Simple, easy-to-understand API
- Factory methods provide clean construction patterns
- Separate error and warning collections
- Mutable properties enable incremental error collection (future enhancement)

---

## 5. API Reference

### 5.1 Complete API Surface

#### 5.1.1 Public Types

| Type | Kind | Description |
|------|------|-------------|
| `ISchemaValidator<TSchema, TDocument>` | Interface | Generic validator contract |
| `IJsonSchemaValidator` | Interface | JSON Schema validator with registry |
| `JsonSchemaValidator` | Class | NJsonSchema-based implementation |
| `YamlValidator` | Class | YAML-to-JSON validation implementation |
| `ValidationResult` | Class | Validation result container |

#### 5.1.2 Method Signatures

```csharp
// ISchemaValidator<TSchema, TDocument>
ValidationResult Validate(TSchema schema, TDocument document);
Task<ValidationResult> ValidateAsync(TDocument document, TSchema schema, CancellationToken ct = default);

// IJsonSchemaValidator (extends ISchemaValidator<string, string>)
void AddSchema(string name, string schemaContent);
Task<ValidationResult> ValidateAgainstNamedSchemaAsync(string document, string schemaName, CancellationToken ct = default);

// JsonSchemaValidator
ValidationResult Validate(string schema, string document);
Task<ValidationResult> ValidateAsync(string document, string schema, CancellationToken ct = default);
void AddSchema(string name, string schemaContent);
Task<ValidationResult> ValidateAgainstNamedSchemaAsync(string document, string schemaName, CancellationToken ct = default);

// YamlValidator
ValidationResult Validate(string schema, string document);
Task<ValidationResult> ValidateAsync(string document, string schema, CancellationToken ct = default);

// ValidationResult
bool IsValid { get; set; }
List<string> Errors { get; set; }
List<string> Warnings { get; set; }
static ValidationResult Success();
static ValidationResult Failure(IEnumerable<string> errors);
```

### 5.2 Usage Examples

#### 5.2.1 Basic JSON Validation

```csharp
var validator = new JsonSchemaValidator();

var schema = """
{
    "type": "object",
    "required": ["name", "email"],
    "properties": {
        "name": { "type": "string", "minLength": 2 },
        "email": { "type": "string", "format": "email" },
        "age": { "type": "integer", "minimum": 0 }
    }
}
""";

var document = """
{
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
}
""";

var result = validator.Validate(schema, document);
Console.WriteLine($"Valid: {result.IsValid}");
// Output: Valid: True
```

#### 5.2.2 JSON Validation with Errors

```csharp
var validator = new JsonSchemaValidator();

var schema = """
{
    "type": "object",
    "required": ["name", "email"],
    "properties": {
        "name": { "type": "string", "minLength": 2 },
        "email": { "type": "string", "format": "email" }
    }
}
""";

var document = """
{
    "name": "J",
    "email": "not-an-email"
}
""";

var result = validator.Validate(schema, document);
Console.WriteLine($"Valid: {result.IsValid}");
foreach (var error in result.Errors)
{
    Console.WriteLine($"  Error: {error}");
}
// Output:
// Valid: False
//   Error: [properties.name] MinLength: 
//   Error: [properties.email] Format: 
```

#### 5.2.3 Async JSON Validation

```csharp
var validator = new JsonSchemaValidator();
var result = await validator.ValidateAsync(document, schema, cancellationToken);
```

#### 5.2.4 Named Schema Validation

```csharp
var validator = new JsonSchemaValidator();

// Register schema
validator.AddSchema("user", userSchemaJson);

// Validate against named schema
var result = await validator.ValidateAgainstNamedSchemaAsync(
    userDocumentJson, 
    "user");
```

#### 5.2.5 YAML Validation

```csharp
var validator = new YamlValidator();

var schema = """
{
    "type": "object",
    "properties": {
        "name": { "type": "string" },
        "settings": { "type": "object" }
    }
}
""";

var yaml = """
name: MyApplication
settings:
  debug: true
  logLevel: verbose
""";

var result = validator.Validate(schema, yaml);
```

#### 5.2.6 Dependency Injection

```csharp
// Registration
builder.Services.AddSingleton<IJsonSchemaValidator, JsonSchemaValidator>();
builder.Services.AddSingleton<YamlValidator>();

// Usage
public class ConfigValidator
{
    private readonly IJsonSchemaValidator _jsonValidator;
    private readonly YamlValidator _yamlValidator;
    
    public ConfigValidator(
        IJsonSchemaValidator jsonValidator, 
        YamlValidator yamlValidator)
    {
        _jsonValidator = jsonValidator;
        _yamlValidator = yamlValidator;
    }
}
```

### 5.3 Error Code Reference

| Error Pattern | Description | Example |
|--------------|-------------|---------|
| `[<path>] Type:` | Type mismatch | `[properties.age] Type: Expected integer but found string` |
| `[<path>] Required:` | Missing required property | `[properties.email] Required: Required property is missing` |
| `[<path>] Format:` | Format validation failure | `[properties.email] Format: Value does not match email format` |
| `[<path>] MinLength:` | String too short | `[properties.name] MinLength: String is too short` |
| `[<path>] MaxLength:` | String too long | `[properties.name] MaxLength: String is too long` |
| `[<path>] Minimum:` | Number below minimum | `[properties.age] Minimum: Value is below minimum` |
| `[<path>] Maximum:` | Number above maximum | `[properties.age] Maximum: Value is above maximum` |
| `[<path>] Pattern:` | Regex mismatch | `[properties.code] Pattern: String does not match pattern` |
| `[<path>] Enum:` | Value not in enumeration | `[properties.status] Enum: Value not in enumeration` |
| `Schema '<name>' not found` | Named schema not registered | `Schema 'user' not found` |
| `Invalid YAML: <message>` | YAML parse error | `Invalid YAML: while parsing a block mapping at line 3, column 5` |

---

## 6. Error Handling

### 6.1 Error Categories

| Category | Source | Handling |
|----------|--------|----------|
| Schema Parse Errors | Invalid JSON Schema | Caught, returned as validation failure |
| Document Parse Errors | Invalid JSON/YAML | Caught, returned as validation failure |
| Schema Validation Errors | Document violates schema | Collected, returned as validation errors |
| Registry Errors | Schema not found | Returned as validation failure |
| System Errors | Out of memory, etc. | Propagated as exceptions |

### 6.2 Error Handling Flow

```
  Input
  +-----+
  | Doc |
  +--+--+
     |
     v
  +--------+     Invalid Input     +------------------+
  | Parse  | -------------------> | Return Failure    |
  | Input  |                      | (parse error)     |
  +---+----+                      +------------------+
      |
      | Valid Input
      v
  +--------+     Schema Error      +------------------+
  | Parse  | -------------------> | Return Failure    |
  | Schema |                      | (schema error)    |
  +---+----+                      +------------------+
      |
      | Valid Schema
      v
  +--------+     Validation        +------------------+
  | Validate| ---- Failures ----> | Return Failure    |
  |         |                     | (all errors)      |
  +---+----+                     +------------------+
      |
      | Success
      v
  +------------------+
  | Return Success   |
  +------------------+
```

### 6.3 Exception Handling Strategy

| Exception Type | Handling | User-Facing Message |
|---------------|----------|-------------------|
| `JsonException` | Caught | "Invalid JSON: <message>" |
| `YamlException` | Caught | "Invalid YAML: <message>" |
| `KeyNotFoundException` | Caught | "Schema '<name>' not found" |
| `ArgumentException` | Caught | "Invalid schema: <message>" |
| `OperationCanceledException` | Propagated | (cancellation) |
| `OutOfMemoryException` | Propagated | (system error) |

### 6.4 Error Aggregation (Current)

Current implementation collects all validation errors into a flat list:

```csharp
var errors = jsonSchema.Validate(document);
return ValidationResult.Failure(
    errors.Select(e => $"[{e.Path}] {e.Kind}: {e.Property}"));
```

### 6.5 Error Aggregation (Proposed - ADR-003)

Future implementation will use structured error objects:

```csharp
var errors = jsonSchema.Validate(document);
var validationErrors = errors.Select(e => new ValidationError
{
    Code = e.Kind.ToString(),
    Message = e.Property ?? "Validation failed",
    Path = e.Path,
    PropertyName = e.Property
});
return ValidationResult.Failure(validationErrors);
```

### 6.6 Warning Handling

Warnings are collected separately from errors and do not affect `IsValid`:

```csharp
var result = ValidationResult.Success();
result.Warnings.Add("Deprecated schema version used");
// result.IsValid is still true
```

---

## 7. Security

### 7.1 Threat Model

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| Malicious schema | DoS via regex backtracking | Medium | Schema size limits, regex timeout |
| YAML bomb | Memory exhaustion | Low | Document size limits, depth limits |
| Schema injection | Validation bypass | Low | Schema validation before use |
| Error information leakage | Information disclosure | Medium | Error sanitization |
| Large document | Memory exhaustion | Medium | Document size limits |

### 7.2 Input Validation

#### 7.2.1 Schema Size Limits

```csharp
public class ValidationLimits
{
    public const int MaxSchemaSize = 1024 * 1024; // 1MB
    public const int MaxDocumentSize = 10 * 1024 * 1024; // 10MB
    public const int MaxSchemaDepth = 20;
    public const int MaxDocumentDepth = 50;
    public const int MaxRegexTimeoutMs = 100;
}
```

#### 7.2.2 YAML Bomb Prevention

YAML documents can be crafted to cause exponential memory expansion through anchors and aliases:

```yaml
# YAML bomb example
a: &a ["lol","lol","lol","lol","lol","lol","lol","lol","lol"]
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
# ... continues exponentially
```

Mitigation:
- Enforce maximum document size before parsing
- Use YamlDotNet's streaming parser for large documents
- Monitor memory usage during parsing

### 7.3 Schema Validation

Schemas should be validated before use to prevent malicious patterns:

```csharp
public ValidationResult ValidateSchema(string schemaContent)
{
    // Check size
    if (schemaContent.Length > ValidationLimits.MaxSchemaSize)
        return ValidationResult.Failure(
            new[] { "Schema exceeds maximum size" });
    
    // Check for dangerous patterns
    if (ContainsCatastrophicRegex(schemaContent))
        return ValidationResult.Failure(
            new[] { "Schema contains potentially dangerous regex patterns" });
    
    // Parse and validate
    try
    {
        var schema = JsonSchema.FromJsonAsync(schemaContent)
            .GetAwaiter().GetResult();
        return ValidationResult.Success();
    }
    catch (Exception ex)
    {
        return ValidationResult.Failure(
            new[] { $"Invalid schema: {ex.Message}" });
    }
}
```

### 7.4 Error Sanitization

Validation errors should not expose internal system details:

```csharp
public static class ErrorSanitizer
{
    private static readonly Regex InternalPathRegex = 
        new(@"(at\s+.*\.(cs|dll):line\s+\d+)", RegexOptions.Compiled);
    
    public static string Sanitize(string error)
    {
        return InternalPathRegex.Replace(error, "[internal]");
    }
    
    public static ValidationResult Sanitize(ValidationResult result)
    {
        return ValidationResult.Failure(
            result.Errors.Select(Sanitize));
    }
}
```

### 7.5 Secure Defaults

| Setting | Default | Rationale |
|---------|---------|-----------|
| Schema size limit | 1MB | Prevents DoS via large schemas |
| Document size limit | 10MB | Prevents memory exhaustion |
| Regex timeout | 100ms | Prevents catastrophic backtracking |
| Schema depth limit | 20 | Prevents deep nesting attacks |
| Document depth limit | 50 | Prevents deeply nested documents |

---

## 8. Performance

### 8.1 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Simple JSON validation | <10ms | 100-property document |
| Complex JSON validation | <50ms | Nested object with references |
| YAML validation | <20ms | Simple YAML document |
| Schema parsing (cached) | <1ms | Subsequent validation |
| Schema parsing (cold) | <5ms | First validation |
| Memory per validation | <100KB | Typical document |
| Concurrent validations | 1000/sec | Thread-safe operation |

### 8.2 Performance Characteristics

#### 8.2.1 Schema Parsing

Schema parsing is the most expensive operation:

```
Operation          | Time (ms) | Memory (KB)
-------------------|-----------|------------
Parse simple schema| 2-5       | 15-30
Parse complex schema| 5-15     | 30-100
Validate (cached)  | 1-5       | 5-15
Validate (uncached)| 3-10      | 10-25
```

#### 8.2.2 Caching Strategy

Schema caching eliminates parsing overhead:

```csharp
public class CachedJsonSchemaValidator
{
    private readonly ConcurrentDictionary<string, JsonSchema> _cache = new();
    
    public async Task<JsonSchema> GetOrParseAsync(
        string schemaJson, 
        CancellationToken ct = default)
    {
        var hash = ComputeHash(schemaJson);
        return _cache.GetOrAdd(hash, _ => 
            JsonSchema.FromJsonAsync(schemaJson, ct)
                .GetAwaiter().GetResult());
    }
    
    private static string ComputeHash(string schemaJson)
    {
        using var sha = SHA256.Create();
        var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(schemaJson));
        return Convert.ToBase64String(bytes);
    }
}
```

### 8.3 Optimization Opportunities

| Optimization | Impact | Effort | Status |
|-------------|--------|--------|--------|
| ConcurrentDictionary for cache | High | Low | Not implemented |
| Schema hash-based caching | Medium | Low | Not implemented |
| Remove double YAML deserialization | Low | Low | Not implemented |
| System.Text.Json instead of Newtonsoft | Medium | Medium | Not implemented |
| JsonSchema.Net instead of NJsonSchema | High | High | Deferred |
| Source-generated validators | High | High | Future |

### 8.4 Benchmark Configuration

```csharp
[MemoryDiagnoser]
public class ValidationBenchmarks
{
    private JsonSchemaValidator _validator = null!;
    private string _simpleSchema = null!;
    private string _simpleDocument = null!;
    private string _complexSchema = null!;
    private string _complexDocument = null!;

    [GlobalSetup]
    public void Setup()
    {
        _validator = new JsonSchemaValidator();
        _simpleSchema = File.ReadAllText("benchmarks/simple-schema.json");
        _simpleDocument = File.ReadAllText("benchmarks/simple-document.json");
        _complexSchema = File.ReadAllText("benchmarks/complex-schema.json");
        _complexDocument = File.ReadAllText("benchmarks/complex-document.json");
    }

    [Benchmark]
    public ValidationResult SimpleValidation() =>
        _validator.Validate(_simpleSchema, _simpleDocument);

    [Benchmark]
    public ValidationResult ComplexValidation() =>
        _validator.Validate(_complexSchema, _complexDocument);
}
```

---

## 9. Testing Strategy

### 9.1 Test Categories

| Category | Purpose | Tools | Coverage Target |
|----------|---------|-------|----------------|
| Unit Tests | Individual component testing | xUnit | 80%+ |
| Integration Tests | Cross-component testing | xUnit | 60%+ |
| Schema Tests | JSON Schema compliance | xUnit + test schemas | All supported keywords |
| Performance Tests | Benchmark validation | BenchmarkDotNet | N/A |
| Security Tests | Vulnerability testing | Custom test cases | All threat model items |

### 9.2 Current Test Coverage

```csharp
public class SchemaValidatorTests
{
    [Fact]
    public void JsonValidator_ValidJson_ReturnsSuccess()
    {
        var validator = new JsonSchemaValidator();
        var schema = @"{ ""type"": ""object"", ""properties"": { ""name"": { ""type"": ""string"" } } }";
        var document = @"{ ""name"": ""test"" }";
        
        var result = validator.Validate(schema, document);
        
        Assert.True(result.IsValid);
    }

    [Fact]
    public void JsonValidator_InvalidSchemaType_ReturnsErrors()
    {
        var validator = new JsonSchemaValidator();
        var schema = @"{ ""type"": ""array"" }";
        var document = @"{ ""name"": ""test"" }";
        
        var result = validator.Validate(schema, document);
        
        Assert.False(result.IsValid);
        Assert.NotEmpty(result.Errors);
    }

    [Fact]
    public void YamlValidator_ValidYaml_ReturnsSuccess()
    {
        var validator = new YamlValidator();
        var schema = @"{ ""type"": ""object"", ""properties"": { ""name"": { ""type"": ""string"" } } }";
        var yaml = "name: test";
        
        var result = validator.Validate(schema, yaml);
        
        Assert.True(result.IsValid);
    }
}
```

### 9.3 Required Test Additions

| Test Category | Test Cases | Priority |
|--------------|-----------|----------|
| JSON Schema - Types | All 7 JSON types | P0 |
| JSON Schema - Strings | minLength, maxLength, pattern, format | P0 |
| JSON Schema - Numbers | minimum, maximum, multipleOf | P0 |
| JSON Schema - Arrays | items, minItems, maxItems, uniqueItems | P0 |
| JSON Schema - Objects | properties, required, additionalProperties | P0 |
| JSON Schema - Combinators | allOf, anyOf, oneOf, not | P1 |
| JSON Schema - Conditionals | if/then/else | P1 |
| JSON Schema - References | $ref, definitions | P1 |
| YAML - Valid Documents | Simple, nested, arrays, anchors | P0 |
| YAML - Invalid Documents | Syntax errors, bombs, edge cases | P0 |
| Schema Registry | Add, retrieve, missing, duplicate | P0 |
| Async Operations | Cancellation, timeout | P1 |
| Thread Safety | Concurrent access | P1 |
| Error Formatting | All error types, edge cases | P1 |
| Performance | Benchmarks, memory profiling | P2 |

### 9.4 Test Data Management

Test data should be organized by category:

```
tests/
├── TestData/
│   ├── Schemas/
│   │   ├── simple-object.json
│   │   ├── nested-object.json
│   │   ├── array-schema.json
│   │   ├── conditional-schema.json
│   │   └── reference-schema.json
│   ├── Documents/
│   │   ├── valid/
│   │   │   ├── simple-object.json
│   │   │   └── nested-object.json
│   │   └── invalid/
│   │       ├── wrong-type.json
│   │       ├── missing-required.json
│   │       └── format-invalid.json
│   └── Yaml/
│       ├── valid/
│       │   ├── simple.yaml
│       │   └── nested.yaml
│       └── invalid/
│           ├── syntax-error.yaml
│           └── bomb.yaml
```

---

## 10. Deployment and Distribution

### 10.1 Package Configuration

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <PackageId>Phenotype.Validation</PackageId>
    <Version>0.1.0</Version>
    <Authors>Phenotype Team</Authors>
    <Description>Generic schema validation for JSON and YAML</Description>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
    
    <!-- NuGet package metadata -->
    <PackageLicenseExpression>MIT</PackageLicenseExpression>
    <PackageProjectUrl>https://github.com/KooshaPari/phenotype-validation</PackageProjectUrl>
    <RepositoryUrl>https://github.com/KooshaPari/phenotype-validation</RepositoryUrl>
    <PackageTags>validation;json-schema;yaml;phenotype</PackageTags>
    <PackageReadmeFile>README.md</PackageReadmeFile>
  </PropertyGroup>
  
  <ItemGroup>
    <PackageReference Include="NJsonSchema" Version="11.0.0" />
    <PackageReference Include="YamlDotNet" Version="16.0.0" />
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
  
  <ItemGroup>
    <None Include="..\README.md" Pack="true" PackagePath="\" />
  </ItemGroup>
</Project>
```

### 10.2 Versioning Strategy

Follow semantic versioning (SemVer 2.0):

| Version | Meaning | Example |
|---------|---------|---------|
| 0.x.y | Pre-release, API not stable | 0.1.0 |
| x.0.0 | Breaking API changes | 1.0.0 |
| x.y.0 | New features, backward compatible | 1.1.0 |
| x.y.z | Bug fixes | 1.1.1 |

### 10.3 Build Pipeline

```yaml
# .github/workflows/traceability.yml (existing)
name: Traceability

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '9.0.x'
      - run: dotnet restore
      - run: dotnet build --no-restore
      - run: dotnet test --no-build --verbosity normal
```

### 10.4 CI/CD Requirements

| Stage | Action | Success Criteria |
|-------|--------|-----------------|
| Build | `dotnet build` | Zero errors, zero warnings |
| Test | `dotnet test` | All tests pass |
| Package | `dotnet pack` | Valid NuGet package |
| Publish | `dotnet nuget push` | Package published to registry |

---

## 11. Migration Guide

### 11.1 From Manual Validation

If you currently validate JSON/YAML manually:

```csharp
// Before: Manual validation
try
{
    var obj = JObject.Parse(json);
    if (obj["name"] == null)
        throw new Exception("Name is required");
    if (obj["email"]?.ToString().Contains("@") != true)
        throw new Exception("Invalid email");
}
catch (Exception ex)
{
    // Handle error
}

// After: Schema-based validation
var validator = new JsonSchemaValidator();
var result = validator.Validate(schema, json);
if (!result.IsValid)
{
    foreach (var error in result.Errors)
    {
        // Handle error
    }
}
```

### 11.2 From Data Annotations

If you currently use Data Annotations for document validation:

```csharp
// Before: Data Annotations (not suitable for documents)
public class UserDto
{
    [Required]
    public string Name { get; set; }
    [EmailAddress]
    public string Email { get; set; }
}

// After: JSON Schema validation
var schema = """
{
    "type": "object",
    "required": ["name", "email"],
    "properties": {
        "name": { "type": "string" },
        "email": { "type": "string", "format": "email" }
    }
}
""";
var result = validator.Validate(schema, jsonDocument);
```

### 11.3 Breaking Changes (Future)

| Change | Version | Migration |
|--------|---------|-----------|
| Thread-safe schema cache | 0.2.0 | No action needed |
| Structured error types | 0.3.0 | Use `Issues` property |
| Schema validation on register | 0.3.0 | Handle schema validation errors |
| Newtonsoft.Json removal | 1.0.0 | Use System.Text.Json |

---

## 12. Future Roadmap

### 12.1 Phase 1: Foundation (Current - v0.1.x)

- [x] JSON Schema validation via NJsonSchema
- [x] YAML validation via YamlDotNet
- [x] Schema registry with named schemas
- [x] Basic error reporting
- [x] Async validation support
- [ ] Thread-safe schema cache
- [ ] Comprehensive test coverage

### 12.2 Phase 2: Enhancement (v0.2.x)

- [ ] Thread-safe schema cache (ConcurrentDictionary)
- [ ] Schema validation on registration
- [ ] Structured error types (ADR-003)
- [ ] Error grouping and deduplication
- [ ] Error formatters (console, JSON)
- [ ] Performance benchmarks
- [ ] System.Text.Json migration evaluation

### 12.3 Phase 3: Advanced (v0.3.x)

- [ ] Rule engine (ADR-002)
- [ ] Validation pipeline
- [ ] Rule sets and conditional rules
- [ ] Schema versioning
- [ ] JsonSchema.Net evaluation
- [ ] Source generator for validators
- [ ] OpenAPI 3.1 integration

### 12.4 Phase 4: Ecosystem (v1.0.x)

- [ ] ASP.NET Core middleware
- [ ] CLI tool for schema validation
- [ ] FluentValidation integration
- [ ] XML Schema validation
- [ ] Custom format validators
- [ ] WebAssembly support

---

## 13. Appendices

### 13.1 Glossary

| Term | Definition |
|------|-----------|
| JSON Schema | A vocabulary for annotating and validating JSON documents |
| YAML | A human-readable data serialization language |
| Schema Registry | A store for named schema definitions |
| Validation Result | The output of a validation operation |
| Error Aggregation | The process of collecting and organizing validation errors |
| Rule Engine | A system for evaluating business rules against data |
| Validation Pipeline | A sequence of validation steps executed in order |

### 13.2 JSON Schema Draft Support

| Feature | Draft 4 | Draft 6 | Draft 7 | Draft 2019-09 | Draft 2020-12 |
|---------|---------|---------|---------|---------------|---------------|
| NJsonSchema | Yes | Yes | Yes | Partial | No |
| JsonSchema.Net | Yes | Yes | Yes | Yes | Yes |

### 13.3 Dependency Version Matrix

| Phenotype.Validation | NJsonSchema | YamlDotNet | Newtonsoft.Json | .NET |
|---------------------|-------------|------------|-----------------|------|
| 0.1.0 | 11.0.0 | 16.0.0 | 13.0.3 | 9.0 |

### 13.4 Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| SOTA Research | `docs/research/VALIDATION_FRAMEWORKS_SOTA.md` | Technology analysis |
| ADR-001 | `docs/adr/ADR-001-validation-approach.md` | Validation approach decision |
| ADR-002 | `docs/adr/ADR-002-rule-engine.md` | Rule engine architecture |
| ADR-003 | `docs/adr/ADR-003-error-aggregation.md` | Error aggregation strategy |

### 13.5 Registry References

| Registry | URL | Purpose |
|----------|-----|---------|
| PhenoSpecs | https://github.com/KooshaPari/PhenoSpecs | Specifications and ADRs |
| PhenoHandbook | https://github.com/KooshaPari/PhenoHandbook | Patterns and guidelines |
| HexaKit | https://github.com/KooshaPari/HexaKit | Templates and scaffolding |
| Master Index | https://github.com/KooshaPari/phenotype-registry | Ecosystem index |

### 13.6 Change Log

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-04-03 | Initial specification |

### 13.7 JSON Schema Keyword Reference

#### 13.7.1 Type Validation

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `type` | string/array | Expected JSON type(s) | `"type": "string"` |
| `type` (multiple) | array | Multiple allowed types | `"type": ["string", "null"]` |

Supported types:
- `string` - JSON string value
- `number` - JSON number (integer or float)
- `integer` - JSON number without fractional part
- `boolean` - JSON boolean (true/false)
- `object` - JSON object (key-value pairs)
- `array` - JSON array (ordered list)
- `null` - JSON null value

#### 13.7.2 String Validation

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `minLength` | integer | Minimum string length | `"minLength": 1` |
| `maxLength` | integer | Maximum string length | `"maxLength": 255` |
| `pattern` | string | Regex pattern | `"pattern": "^[a-z]+$"` |
| `format` | string | Semantic format | `"format": "email"` |

Supported formats:
- `date-time` - RFC 3339 date-time
- `date` - RFC 3339 full-date
- `time` - RFC 3339 time
- `email` - RFC 5322 email address
- `idn-email` - Internationalized email
- `hostname` - RFC 1123 hostname
- `idn-hostname` - Internationalized hostname
- `ipv4` - IPv4 address
- `ipv6` - IPv6 address
- `uri` - RFC 3986 URI
- `uri-reference` - URI reference
- `iri` - Internationalized URI
- `iri-reference` - Internationalized URI reference
- `uri-template` - RFC 6570 URI template
- `json-pointer` - RFC 6901 JSON Pointer
- `relative-json-pointer` - Relative JSON Pointer
- `regex` - Regular expression
- `uuid` - RFC 4122 UUID

#### 13.7.3 Numeric Validation

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `minimum` | number | Inclusive minimum | `"minimum": 0` |
| `maximum` | number | Inclusive maximum | `"maximum": 100` |
| `exclusiveMinimum` | number | Exclusive minimum | `"exclusiveMinimum": 0` |
| `exclusiveMaximum` | number | Exclusive maximum | `"exclusiveMaximum": 100` |
| `multipleOf` | number | Must be multiple of | `"multipleOf": 0.5` |

#### 13.7.4 Array Validation

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `items` | schema | Schema for all items | `"items": {"type": "string"}` |
| `additionalItems` | schema/boolean | Schema for extra items | `"additionalItems": false` |
| `minItems` | integer | Minimum array length | `"minItems": 1` |
| `maxItems` | integer | Maximum array length | `"maxItems": 100` |
| `uniqueItems` | boolean | All items must be unique | `"uniqueItems": true` |
| `contains` | schema | At least one item must match | `"contains": {"type": "string"}` |

#### 13.7.5 Object Validation

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `properties` | object | Property schemas | `"properties": {"name": {...}}` |
| `patternProperties` | object | Regex-based property schemas | `"patternProperties": {"^S_": {...}}` |
| `additionalProperties` | schema/boolean | Schema for extra properties | `"additionalProperties": false` |
| `required` | array | Required property names | `"required": ["name", "email"]` |
| `dependencies` | object | Property dependencies | `"dependencies": {"creditCard": ["billingAddress"]}` |
| `propertyNames` | schema | Schema for property names | `"propertyNames": {"pattern": "^[a-z]+$"}` |
| `minProperties` | integer | Minimum property count | `"minProperties": 1` |
| `maxProperties` | integer | Maximum property count | `"maxProperties": 10` |

#### 13.7.6 Combinator Keywords

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `allOf` | array | Must match ALL schemas | `"allOf": [{"type": "object"}, {"required": ["id"]}]` |
| `anyOf` | array | Must match ANY schema | `"anyOf": [{"type": "string"}, {"type": "number"}]` |
| `oneOf` | array | Must match EXACTLY ONE schema | `"oneOf": [{"type": "string"}, {"type": "number"}]` |
| `not` | schema | Must NOT match schema | `"not": {"type": "null"}` |

#### 13.7.7 Conditional Keywords

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `if` | schema | Condition schema | `"if": {"properties": {"type": {"const": "premium"}}}` |
| `then` | schema | Schema if condition matches | `"then": {"required": ["discount"]}` |
| `else` | schema | Schema if condition doesn't match | `"else": {"not": {"required": ["discount"]}}` |

#### 13.7.8 Reuse and Reference

| Keyword | Type | Description | Example |
|---------|------|-------------|---------|
| `$ref` | string | Reference to another schema | `"$ref": "#/definitions/address"` |
| `definitions` | object | Schema definitions (Draft 4) | `"definitions": {"address": {...}}` |
| `$defs` | object | Schema definitions (Draft 2019-09+) | `"$defs": {"address": {...}}` |
| `$id` | string | Schema identifier | `"$id": "https://example.com/schemas/user"` |
| `$anchor` | string | Fragment identifier | `"$anchor": "user"` |

### 13.8 Error Code Taxonomy

#### 13.8.1 Schema-Level Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `SCHEMA_INVALID` | Critical | Schema is not valid JSON Schema | Fix schema syntax |
| `SCHEMA_NOT_FOUND` | Error | Named schema not in registry | Register schema first |
| `SCHEMA_DEPRECATED` | Warning | Schema version is deprecated | Migrate to current version |

#### 13.8.2 Type Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `TYPE_MISMATCH` | Error | Value has wrong JSON type | Change value to expected type |
| `TYPE_NULL` | Error | Value is null but type doesn't allow null | Provide non-null value or update schema |

#### 13.8.3 String Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `STRING_TOO_SHORT` | Error | String below minLength | Increase string length |
| `STRING_TOO_LONG` | Error | String above maxLength | Decrease string length |
| `FORMAT_INVALID` | Error | String doesn't match format | Fix string format |
| `PATTERN_MISMATCH` | Error | String doesn't match pattern | Fix string to match regex |

#### 13.8.4 Numeric Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `VALUE_TOO_LOW` | Error | Number below minimum | Increase number |
| `VALUE_TOO_HIGH` | Error | Number above maximum | Decrease number |
| `NOT_MULTIPLE` | Error | Number not multiple of value | Adjust to valid multiple |

#### 13.8.5 Array Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `ARRAY_TOO_SHORT` | Error | Array has too few items | Add more items |
| `ARRAY_TOO_LONG` | Error | Array has too many items | Remove items |
| `DUPLICATE_ITEMS` | Error | Array has duplicate items (uniqueItems) | Remove duplicates |
| `ITEM_TYPE_MISMATCH` | Error | Array item has wrong type | Fix item type |
| `NO_MATCHING_ITEM` | Error | No item matches contains schema | Add matching item |

#### 13.8.6 Object Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `REQUIRED_MISSING` | Error | Required property is missing | Add required property |
| `ADDITIONAL_PROPERTY` | Error | Unexpected property (additionalProperties: false) | Remove property or update schema |
| `PROPERTY_TYPE_MISMATCH` | Error | Property has wrong type | Fix property type |
| `TOO_FEW_PROPERTIES` | Error | Object has too few properties (minProperties) | Add more properties |
| `TOO_MANY_PROPERTIES` | Error | Object has too many properties (maxProperties) | Remove properties |
| `INVALID_PROPERTY_NAME` | Error | Property name doesn't match propertyNames schema | Rename property |

#### 13.8.7 YAML Errors

| Code | Severity | Description | Resolution |
|------|----------|-------------|------------|
| `YAML_PARSE_ERROR` | Error | YAML syntax error | Fix YAML syntax |
| `YAML_ANCHOR_NOT_FOUND` | Error | YAML anchor reference not found | Define anchor or remove reference |
| `YAML_CIRCULAR_REF` | Error | Circular YAML reference | Remove circular reference |
| `YAML_BOMB_DETECTED` | Critical | Exponential expansion detected | Reduce document size |

### 13.9 Integration Patterns

#### 13.9.1 Configuration Validation Pattern

```csharp
public class ConfigurationValidator
{
    private readonly IJsonSchemaValidator _validator;
    private readonly ISchemaRegistry _registry;

    public ConfigurationValidator(
        IJsonSchemaValidator validator,
        ISchemaRegistry registry)
    {
        _validator = validator;
        _registry = registry;
    }

    public async Task<ValidationResult> ValidateConfigFileAsync(
        string filePath, 
        string schemaName,
        CancellationToken ct = default)
    {
        // Read file
        var content = await File.ReadAllTextAsync(filePath, ct);
        
        // Determine format
        var extension = Path.GetExtension(filePath).ToLowerInvariant();
        
        // Validate
        return extension switch
        {
            ".json" => await _validator.ValidateAsync(content, 
                await _registry.GetSchemaAsync(schemaName, ct), ct),
            ".yaml" or ".yml" => await ValidateYamlAsync(content, schemaName, ct),
            _ => ValidationResult.Failure(new[] { $"Unsupported format: {extension}" })
        };
    }

    private async Task<ValidationResult> ValidateYamlAsync(
        string yaml, 
        string schemaName, 
        CancellationToken ct)
    {
        var yamlValidator = new YamlValidator(_validator);
        var schema = await _registry.GetSchemaAsync(schemaName, ct);
        return await yamlValidator.ValidateAsync(yaml, schema, ct);
    }
}
```

#### 13.9.2 API Request Validation Pattern

```csharp
public class ApiValidationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IJsonSchemaValidator _validator;
    private readonly ISchemaRegistry _registry;

    public ApiValidationMiddleware(
        RequestDelegate next,
        IJsonSchemaValidator validator,
        ISchemaRegistry registry)
    {
        _next = next;
        _validator = validator;
        _registry = registry;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var schemaName = context.Request.Path.Value?.TrimStart('/');
        
        if (context.Request.Method == HttpMethods.Post || 
            context.Request.Method == HttpMethods.Put)
        {
            var body = await ReadBodyAsync(context.Request);
            var schema = await _registry.GetSchemaAsync(schemaName);
            var result = await _validator.ValidateAsync(body, schema);
            
            if (!result.IsValid)
            {
                context.Response.StatusCode = 400;
                await context.Response.WriteAsJsonAsync(new
                {
                    error = "Validation Failed",
                    details = result.Errors
                });
                return;
            }
        }
        
        await _next(context);
    }

    private async Task<string> ReadBodyAsync(HttpRequest request)
    {
        request.EnableBuffering();
        using var reader = new StreamReader(request.Body);
        var body = await reader.ReadToEndAsync();
        request.Body.Position = 0;
        return body;
    }
}
```

#### 13.9.3 Batch Validation Pattern

```csharp
public class BatchValidator
{
    private readonly IJsonSchemaValidator _validator;
    private readonly int _maxConcurrency;

    public BatchValidator(IJsonSchemaValidator validator, int maxConcurrency = 10)
    {
        _validator = validator;
        _maxConcurrency = maxConcurrency;
    }

    public async Task<BatchValidationResult> ValidateBatchAsync(
        IEnumerable<ValidationRequest> requests,
        CancellationToken ct = default)
    {
        var semaphore = new SemaphoreSlim(_maxConcurrency);
        var results = new ConcurrentBag<DocumentValidationResult>();
        
        var tasks = requests.Select(async request =>
        {
            await semaphore.WaitAsync(ct);
            try
            {
                var result = await _validator.ValidateAsync(
                    request.Document, request.Schema, ct);
                
                results.Add(new DocumentValidationResult
                {
                    DocumentId = request.DocumentId,
                    IsValid = result.IsValid,
                    Errors = result.Errors,
                    Warnings = result.Warnings
                });
            }
            finally
            {
                semaphore.Release();
            }
        });
        
        await Task.WhenAll(tasks);
        
        return new BatchValidationResult
        {
            TotalDocuments = requests.Count(),
            ValidDocuments = results.Count(r => r.IsValid),
            InvalidDocuments = results.Count(r => !r.IsValid),
            Results = results.ToList()
        };
    }
}

public record ValidationRequest(
    string DocumentId,
    string Document,
    string Schema);

public record DocumentValidationResult
{
    public string DocumentId { get; init; } = string.Empty;
    public bool IsValid { get; init; }
    public List<string> Errors { get; init; } = new();
    public List<string> Warnings { get; init; } = new();
}

public record BatchValidationResult
{
    public int TotalDocuments { get; init; }
    public int ValidDocuments { get; init; }
    public int InvalidDocuments { get; init; }
    public List<DocumentValidationResult> Results { get; init; } = new();
}
```

### 13.10 Troubleshooting Guide

#### 13.10.1 Common Issues

| Issue | Symptom | Cause | Solution |
|-------|---------|-------|----------|
| Schema parsing fails | "Invalid schema" exception | Malformed JSON Schema | Validate schema with online validator |
| Validation always fails | All documents fail | Schema references not resolved | Use absolute $ref or register definitions |
| YAML validation loses data | Missing fields after validation | YAML anchors not converted | Check YamlDotNet deserializer settings |
| Slow validation | >100ms per document | Schema not cached | Use named schemas or hash-based caching |
| Thread safety errors | Random exceptions under load | Dictionary not thread-safe | Use ConcurrentDictionary |
| Memory leaks | Growing memory usage | Schema cache never cleared | Implement cache eviction policy |

#### 13.10.2 Debug Mode

```csharp
public class DebugJsonSchemaValidator : IJsonSchemaValidator
{
    private readonly IJsonSchemaValidator _inner;
    private readonly ILogger<DebugJsonSchemaValidator> _logger;

    public DebugJsonSchemaValidator(
        IJsonSchemaValidator inner,
        ILogger<DebugJsonSchemaValidator> logger)
    {
        _inner = inner;
        _logger = logger;
    }

    public ValidationResult Validate(string schema, string document)
    {
        _logger.LogDebug("Validating document against schema");
        _logger.LogDebug("Schema: {Schema}", schema);
        _logger.LogDebug("Document: {Document}", document);
        
        var result = _inner.Validate(schema, document);
        
        _logger.LogDebug("Validation result: {IsValid}, Errors: {ErrorCount}", 
            result.IsValid, result.Errors.Count);
        
        return result;
    }

    public Task<ValidationResult> ValidateAsync(
        string document, string schema, CancellationToken ct = default)
    {
        _logger.LogDebug("Async validating document against schema");
        return _inner.ValidateAsync(document, schema, ct);
    }

    public void AddSchema(string name, string schemaContent)
    {
        _logger.LogDebug("Registering schema: {Name}", name);
        _inner.AddSchema(name, schemaContent);
    }

    public Task<ValidationResult> ValidateAgainstNamedSchemaAsync(
        string document, string schemaName, CancellationToken ct = default)
    {
        _logger.LogDebug("Validating against named schema: {SchemaName}", schemaName);
        return _inner.ValidateAgainstNamedSchemaAsync(document, schemaName, ct);
    }
}
```

---

*This specification is maintained by the Phenotype Architecture Team. Last reviewed: 2026-04-03.*
