# ADR-002: Rule Engine Architecture

**Document ID:** PHENOTYPE_VALIDATION_ADR_002  
**Status:** Accepted  
**Last Updated:** 2026-04-03  
**Author:** Phenotype Architecture Team  
**Supersedes:** N/A  
**Related:** ADR-001, ADR-003, VALIDATION_FRAMEWORKS_SOTA

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

While schema-based validation (ADR-001) addresses document structure validation, the Phenotype ecosystem also requires:

- Business rule validation that goes beyond structural constraints
- Conditional validation rules (validate X only when Y is true)
- Cross-field validation (field A must be greater than field B)
- Dynamic rule evaluation (rules that change at runtime based on configuration)
- Rule composition (combining multiple rules into validation pipelines)
- Rule versioning and lifecycle management

### 1.2 Current State

The current Phenotype.Validation library provides schema-based validation only. There is no support for:
- Business rule validation
- Conditional validation
- Rule composition
- Dynamic rule loading
- Rule versioning

### 1.3 Requirements

The rule engine must:

1. Support both synchronous and asynchronous rule evaluation
2. Allow rules to be composed into pipelines
3. Support conditional rule execution
4. Provide structured error reporting with rule metadata
5. Be extensible for custom rule types
6. Support rule versioning and deprecation
7. Integrate with the existing schema validation infrastructure
8. Maintain performance characteristics suitable for batch processing

### 1.4 Use Cases

| Use Case | Description | Rule Type |
|----------|-------------|-----------|
| Phenotype configuration validation | Validate phenotype config files beyond schema | Business rules |
| API request validation | Validate API requests with business logic | Conditional rules |
| Data pipeline validation | Validate data transformations | Cross-field rules |
| Compliance checking | Validate against regulatory requirements | Dynamic rules |
| Migration validation | Validate data during schema migrations | Versioned rules |

---

## 2. Decision

### 2.1 Primary Decision: Expression-Based Rule Engine

We **accept** an expression-based rule engine architecture that builds on the existing schema validation infrastructure. The rule engine will:

- Use expression trees for rule definitions (compile-time safety)
- Support rule composition through pipeline patterns
- Provide both sync and async rule evaluation
- Integrate with existing `ValidationResult` types
- Support rule metadata (name, version, severity, tags)

### 2.2 Architecture

```
+--------------------------------------------------------------+
|                    Rule Engine Architecture                   |
+--------------------------------------------------------------+
|                                                              |
|  +------------------+    +-------------------------------+  |
|  | IValidationRule  |    | IValidationRuleAsync<T>       |  |
|  | <T>              |    |                               |  |
|  +--------+---------+    +---------------+---------------+  |
|           |                                |                |
|           | implements                     | implements     |
|           v                                v                |
|  +------------------+    +-------------------------------+  |
|  | ExpressionRule   |    | AsyncExpressionRule<T>        |  |
|  | <T>              |    |                               |  |
|  | - Expression     |    | - AsyncExpression             |  |
|  | - ErrorMessage   |    | - AsyncErrorMessage           |  |
|  | - Metadata       |    | - Metadata                    |  |
|  +------------------+    +-------------------------------+  |
|                                                              |
|  +------------------------------------------------------+  |
|  | RuleEngine<T>                                        |  |
|  |                                                      |  |
|  | - AddRule(IRule<T>)                                  |  |
|  | - AddRuleSet(string, Action<RuleSetBuilder<T>>)      |  |
|  | - ExecuteAsync(T, RuleOptions, CancellationToken)    |  |
|  | - ExecuteAllAsync(T[], CancellationToken)            |  |
|  +------------------------------------------------------+  |
|                                                              |
|  +------------------------------------------------------+  |
|  | ValidationPipeline                                   |  |
|  |                                                      |  |
|  | - AddStep(IValidationStep)                           |  |
|  | - WithFailFast(bool)                                 |  |
|  | - WithErrorAggregation(ErrorAggregationStrategy)     |  |
|  | - ExecuteAsync(T, CancellationToken)                 |  |
|  +------------------------------------------------------+  |
+--------------------------------------------------------------+
```

### 2.3 Rule Definition

```csharp
public interface IValidationRule<T>
{
    string RuleId { get; }
    string RuleName { get; }
    string? Description { get; }
    RuleSeverity Severity { get; }
    IReadOnlyList<string> Tags { get; }
    Version? Version { get; }
    
    ValidationResult Validate(T instance);
}

public interface IValidationRuleAsync<T> : IValidationRule<T>
{
    Task<ValidationResult> ValidateAsync(T instance, CancellationToken ct = default);
}

public enum RuleSeverity
{
    Info,
    Warning,
    Error,
    Critical
}
```

### 2.4 Expression-Based Rule Builder

```csharp
public class RuleBuilder<T>
{
    private readonly List<IValidationRule<T>> _rules = new();

    public RuleBuilder<T> RuleFor<TProperty>(
        Expression<Func<T, TProperty>> propertyExpression,
        Func<TProperty, bool> condition,
        string errorMessage)
    {
        var propertyName = GetPropertyName(propertyExpression);
        _rules.Add(new PropertyRule<T, TProperty>(
            propertyName, condition, errorMessage));
        return this;
    }

    public RuleBuilder<T> Must(
        Expression<Func<T, bool>> condition,
        string errorMessage,
        RuleSeverity severity = RuleSeverity.Error)
    {
        _rules.Add(new MustRule<T>(condition, errorMessage, severity));
        return this;
    }

    public RuleBuilder<T> When(
        Expression<Func<T, bool>> guardCondition,
        Action<RuleBuilder<T>> ruleConfig)
    {
        var conditionalBuilder = new RuleBuilder<T>();
        ruleConfig(conditionalBuilder);
        
        foreach (var rule in conditionalBuilder._rules)
        {
            _rules.Add(new ConditionalRule<T>(guardCondition, rule));
        }
        return this;
    }

    public IReadOnlyList<IValidationRule<T>> Build() => _rules.ToList();
}
```

### 2.5 Rule Engine Implementation

```csharp
public class RuleEngine<T>
{
    private readonly List<IValidationRule<T>> _rules = new();
    private readonly Dictionary<string, List<IValidationRule<T>>> _ruleSets = new();
    private readonly bool _failFast;

    public RuleEngine(bool failFast = false)
    {
        _failFast = failFast;
    }

    public RuleEngine<T> AddRule(IValidationRule<T> rule)
    {
        _rules.Add(rule);
        return this;
    }

    public RuleEngine<T> AddRuleSet(string name, IEnumerable<IValidationRule<T>> rules)
    {
        _ruleSets[name] = rules.ToList();
        return this;
    }

    public async Task<ValidationResult> ExecuteAsync(
        T instance,
        string? ruleSetName = null,
        CancellationToken ct = default)
    {
        var rulesToExecute = ruleSetName != null && _ruleSets.ContainsKey(ruleSetName)
            ? _ruleSets[ruleSetName]
            : _rules;

        var allErrors = new List<string>();
        var allWarnings = new List<string>();

        foreach (var rule in rulesToExecute)
        {
            ct.ThrowIfCancellationRequested();

            ValidationResult result;
            if (rule is IValidationRuleAsync<T> asyncRule)
            {
                result = await asyncRule.ValidateAsync(instance, ct);
            }
            else
            {
                result = await Task.FromResult(rule.Validate(instance));
            }

            if (!result.IsValid)
            {
                allErrors.AddRange(result.Errors);
                allWarnings.AddRange(result.Warnings);

                if (_failFast)
                    break;
            }
        }

        return allErrors.Count == 0
            ? ValidationResult.Success()
            : ValidationResult.Failure(allErrors);
    }
}
```

### 2.6 Validation Pipeline

```csharp
public class ValidationPipeline
{
    private readonly List<IValidationStep> _steps = new();
    private bool _failFast;
    private ErrorAggregationStrategy _errorStrategy = ErrorAggregationStrategy.CollectAll;

    public ValidationPipeline AddStep(IValidationStep step)
    {
        _steps.Add(step);
        return this;
    }

    public ValidationPipeline WithFailFast(bool value = true)
    {
        _failFast = value;
        return this;
    }

    public ValidationPipeline WithErrorAggregation(ErrorAggregationStrategy strategy)
    {
        _errorStrategy = strategy;
        return this;
    }

    public async Task<ValidationResult> ExecuteAsync<T>(
        T instance,
        CancellationToken ct = default)
    {
        var context = new ValidationContext<T>(instance);
        var aggregatedResult = new AggregatedValidationResult(_errorStrategy);

        foreach (var step in _steps)
        {
            var result = await step.ExecuteAsync(context, ct);
            aggregatedResult.Merge(result);

            if (_failFast && !result.IsValid)
                break;
        }

        return aggregatedResult.ToValidationResult();
    }
}
```

### 2.7 Rule Execution Flow

```
  Instance                    Rule Engine                    Result
  +--------+                 +------------+                 +--------+
  |        |                 |            |                 |        |
  |  T     | --------------> | RuleEngine | --------------> | Valid  |
  |        |                 |            |                 | Result |
  |        |                 |            |                 |        |
  +--------+                 +-----+------+                 +--------+
                                    |
                                    | Each Rule
                                    v
                          +--------------------+
                          | IValidationRule<T> |
                          |                    |
                          | 1. Evaluate        |
                          | 2. Collect errors  |
                          | 3. Return result   |
                          +--------------------+
                                    |
                                    | Fail fast?
                                    v
                          +--------------------+
                          | Continue or Break  |
                          +--------------------+
```

---

## 3. Consequences

### 3.1 Positive Consequences

1. **Type Safety**: Expression-based rules provide compile-time type checking, eliminating runtime errors from incorrect property names or type mismatches.

2. **Composability**: Rules can be composed into rule sets and pipelines, enabling complex validation scenarios from simple building blocks.

3. **Testability**: Individual rules are isolated and can be unit tested independently, improving test coverage and reliability.

4. **Async Support**: Native async rule evaluation enables database lookups, external API calls, and other I/O-bound validation without blocking.

5. **Metadata-Rich**: Rules carry metadata (ID, name, severity, tags, version) enabling advanced features like rule filtering, reporting, and versioning.

6. **Fail-Fast Option**: Configurable fail-fast behavior allows optimization for scenarios where only the first error matters.

7. **Rule Sets**: Named rule sets enable conditional rule execution (e.g., "Create" vs "Update" validation rules).

8. **Integration**: Seamlessly integrates with existing schema validation through shared `ValidationResult` types.

### 3.2 Negative Consequences

1. **Complexity**: The rule engine adds significant complexity compared to simple schema validation, requiring careful documentation and examples.

2. **Learning Curve**: Developers must understand expression trees, rule composition, and pipeline patterns to use the engine effectively.

3. **Performance Overhead**: Expression tree compilation adds initial overhead (~1-5ms per rule set), though cached rules execute quickly.

4. **Memory Usage**: Compiled expression trees and rule metadata increase memory footprint compared to simple validators.

5. **Debugging Difficulty**: Expression-based rules can be harder to debug than imperative code, especially for complex conditions.

6. **Maintenance Burden**: More code to maintain, test, and document compared to the current schema-only approach.

7. **Rule Proliferation**: Without governance, rule sets can grow unmanageably large, requiring rule organization and lifecycle management.

### 3.3 Neutral Consequences

1. **Dependency-Free**: The rule engine uses only .NET BCL types (expression trees, generics), adding no external dependencies.

2. **Backward Compatible**: Existing schema validation continues to work unchanged; the rule engine is an additive feature.

3. **Extensible Design**: The interface-based design allows for future rule types (e.g., NRules integration, DSL-based rules) without breaking changes.

4. **Versioning Overhead**: Rule versioning adds metadata management but enables important capabilities like migration validation and deprecation tracking.

---

## 4. Alternatives Considered

### 4.1 Alternative A: NRules Integration

**Description**: Use NRules, a production-ready Rete-based rule engine.

**Rejected Because**:
- Significant complexity overhead for our use case
- Rete algorithm is optimized for large rule sets with complex matching
- Steep learning curve for rule DSL
- Additional dependency with its own lifecycle
- Overkill for Phenotype's current validation needs
- Better suited for future phase if rule complexity grows significantly

### 4.2 Alternative B: FluentValidation Integration

**Description**: Use FluentValidation as the rule engine.

**Deferred Because**:
- FluentValidation is excellent for domain object validation
- However, it is not designed for document/schema validation
- Could be integrated in a future phase for domain-level validation
- Current focus is on schema-based validation with rule engine extension

### 4.3 Alternative C: DSL-Based Rules

**Description**: Define rules in a domain-specific language (YAML/JSON config).

**Rejected Because**:
- Loss of compile-time type safety
- Runtime parsing and validation of rules adds complexity
- Debugging DSL-based rules is significantly harder
- No IntelliSense or IDE support
- Better suited for business-user-configurable rules (future consideration)

### 4.4 Alternative D: Custom Attribute-Based Rules

**Description**: Define rules using custom attributes on properties.

**Rejected Because**:
- Same limitations as Data Annotations (poor composability, testability)
- Cannot express complex conditional logic easily
- No async support
- Runtime-only discovery of rules

---

## 5. Implementation Notes

### 5.1 Expression Tree Compilation

Rules should compile expressions once and cache the delegates:

```csharp
public class CompiledRule<T>
{
    private readonly Func<T, bool> _compiledCondition;
    
    public CompiledRule(Expression<Func<T, bool>> expression)
    {
        _compiledCondition = expression.Compile();
    }
    
    public bool Evaluate(T instance) => _compiledCondition(instance);
}
```

### 5.2 Rule Caching Strategy

```csharp
public class RuleCache<T>
{
    private readonly ConcurrentDictionary<string, IValidationRule<T>> _cache = new();
    
    public IValidationRule<T> GetOrAdd(string ruleId, Func<IValidationRule<T>> factory)
    {
        return _cache.GetOrAdd(ruleId, _ => factory());
    }
}
```

### 5.3 Error Context Enrichment

Rules should provide rich error context:

```csharp
public record RuleError(
    string RuleId,
    string RuleName,
    string Message,
    RuleSeverity Severity,
    string? PropertyName = null,
    object? AttemptedValue = null,
    Dictionary<string, object>? Metadata = null);
```

### 5.4 Rule Versioning

```csharp
public class VersionedRule<T> : IValidationRule<T>
{
    public Version Version { get; set; }
    public DateTime EffectiveDate { get; set; }
    public DateTime? DeprecationDate { get; set; }
    public string? SupersededBy { get; set; }
    
    public ValidationResult Validate(T instance)
    {
        if (DeprecationDate.HasValue && DateTime.UtcNow > DeprecationDate.Value)
        {
            // Return warning about deprecated rule
        }
        // ... normal validation
    }
}
```

---

## 6. Cross-References

| Document | Relationship | Description |
|----------|-------------|-------------|
| ADR-001 | Depends | Builds on the schema-based validation approach |
| ADR-003 | Feeds | Rule engine produces errors consumed by aggregation strategy |
| VALIDATION_FRAMEWORKS_SOTA | Informs | SOTA research on rule engines informed this decision |
| SPEC.md | Specifies | Full specification of the rule engine |

---

*This ADR was accepted by the Phenotype Architecture Team on 2026-04-03.*
