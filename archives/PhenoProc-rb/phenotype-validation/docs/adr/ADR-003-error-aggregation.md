# ADR-003: Error Aggregation Strategy

**Document ID:** PHENOTYPE_VALIDATION_ADR_003  
**Status:** Proposed  
**Last Updated:** 2026-04-03  
**Author:** Phenotype Architecture Team  
**Supersedes:** N/A  
**Related:** ADR-001, ADR-002, VALIDATION_FRAMEWORKS_SOTA

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

The current `ValidationResult` in Phenotype.Validation uses a simple flat list of strings for errors and warnings:

```csharp
public class ValidationResult
{
    public bool IsValid { get; set; }
    public List<string> Errors { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
}
```

This approach has significant limitations:

- **No structure**: Errors are unstructured strings, making programmatic handling difficult
- **No correlation**: Cannot correlate errors to specific document paths or properties
- **No severity levels**: All errors are treated equally, no distinction between warnings and critical errors
- **No deduplication**: Identical errors from multiple validators are not deduplicated
- **No grouping**: Cannot group errors by category, path, or validator
- **No metadata**: Cannot attach additional context to errors (rule ID, attempted value, suggestions)
- **No sorting**: Errors are returned in arbitrary order, not prioritized by importance

### 1.2 Current Error Format

Current error messages follow a convention but lack structure:

```
[properties.email] Format: Value does not match email format
[properties.age] Type: Expected integer but found string
Invalid YAML: while parsing a block mapping at line 3, column 5
Schema 'user' not found
```

### 1.3 Requirements

The error aggregation strategy must:

1. Provide structured error objects with typed fields
2. Support error grouping by path, category, or validator
3. Enable error deduplication across multiple validators
4. Support severity levels (info, warning, error, critical)
5. Allow error sorting and prioritization
6. Provide error metadata for programmatic handling
7. Support error formatting for different output formats (JSON, console, HTML)
8. Maintain backward compatibility with existing string-based errors
9. Support error aggregation from multiple validation sources (schema + rules)
10. Enable error filtering and querying

### 1.4 Use Cases

| Use Case | Error Aggregation Need |
|----------|----------------------|
| CI/CD pipeline validation | Group errors by file, sort by severity |
| API error responses | Format errors as RFC 7807 Problem Details |
| Developer tooling | Rich error metadata with suggestions |
| User-facing validation | Human-readable grouped errors |
| Batch processing | Deduplicated error counts per document |
| Audit logging | Structured errors with full context |

---

## 2. Decision

### 2.1 Primary Decision: Structured Error Aggregation

We **propose** a structured error aggregation strategy that introduces typed error objects, grouping, deduplication, and formatting capabilities while maintaining backward compatibility with the existing string-based `ValidationResult`.

### 2.2 Error Type Hierarchy

```
+--------------------------------------------------------------+
|                    Error Type Hierarchy                       |
+--------------------------------------------------------------+
|                                                              |
|  +------------------------------------------------------+  |
|  | IValidationIssue (interface)                         |  |
|  |                                                      |  |
|  | - IssueId: string                                    |  |
|  | - Message: string                                    |  |
|  | - Severity: IssueSeverity                            |  |
|  | - Path: string?                                      |  |
|  | - Code: string?                                      |  |
|  +------------------------------------------------------+  |
|           |                                                |
|           | implements                                     |
|           v                                                |
|  +------------------+    +-------------------------------+  |
|  | ValidationError  |    | ValidationWarning             |  |
|  |                  |    |                               |  |
|  | - PropertyName   |    | - PropertyName                |  |
|  | - AttemptedValue |    | - AttemptedValue              |  |
|  | - ExpectedValue  |    | - Suggestion                  |  |
|  | - Metadata       |    | - Metadata                    |  |
|  +------------------+    +-------------------------------+  |
|                                                              |
|  +------------------------------------------------------+  |
|  | IssueSeverity (enum)                                 |  |
|  |                                                      |  |
|  | - Info (0)                                           |  |
|  | - Warning (1)                                        |  |
|  | - Error (2)                                          |  |
|  | - Critical (3)                                       |  |
|  +------------------------------------------------------+  |
+--------------------------------------------------------------+
```

### 2.3 Structured Error Definition

```csharp
public interface IValidationIssue
{
    string IssueId { get; }
    string Message { get; }
    IssueSeverity Severity { get; }
    string? Path { get; }
    string? Code { get; }
}

public enum IssueSeverity
{
    Info = 0,
    Warning = 1,
    Error = 2,
    Critical = 3
}

public record ValidationError : IValidationIssue
{
    public string IssueId { get; init; } = Guid.NewGuid().ToString("N")[..8];
    public string Message { get; init; } = string.Empty;
    public IssueSeverity Severity => IssueSeverity.Error;
    public string? Path { get; init; }
    public string? Code { get; init; }
    public string? PropertyName { get; init; }
    public object? AttemptedValue { get; init; }
    public object? ExpectedValue { get; init; }
    public string? RuleId { get; init; }
    public IReadOnlyDictionary<string, object> Metadata { get; init; } 
        = new Dictionary<string, object>();
}

public record ValidationWarning : IValidationIssue
{
    public string IssueId { get; init; } = Guid.NewGuid().ToString("N")[..8];
    public string Message { get; init; } = string.Empty;
    public IssueSeverity Severity => IssueSeverity.Warning;
    public string? Path { get; init; }
    public string? Code { get; init; }
    public string? PropertyName { get; init; }
    public string? Suggestion { get; init; }
    public IReadOnlyDictionary<string, object> Metadata { get; init; } 
        = new Dictionary<string, object>();
}
```

### 2.4 Enhanced ValidationResult

```csharp
public class ValidationResult
{
    // Current (backward compatible)
    public bool IsValid => Errors.Count == 0;
    public List<string> Errors { get; } = new();
    public List<string> Warnings { get; } = new();
    
    // New structured issues
    public IReadOnlyList<IValidationIssue> Issues { get; } = new List<IValidationIssue>();
    
    // Convenience accessors
    public IReadOnlyList<ValidationError> ValidationErrors => 
        Issues.OfType<ValidationError>().ToList();
    public IReadOnlyList<ValidationWarning> ValidationWarnings => 
        Issues.OfType<ValidationWarning>().ToList();
    
    // Query methods
    public IReadOnlyList<IValidationIssue> GetIssuesForPath(string path) =>
        Issues.Where(i => i.Path?.StartsWith(path, StringComparison.Ordinal) == true).ToList();
    
    public IReadOnlyList<IValidationIssue> GetIssuesByCode(string code) =>
        Issues.Where(i => i.Code == code).ToList();
    
    public IReadOnlyList<IValidationIssue> GetIssuesBySeverity(IssueSeverity severity) =>
        Issues.Where(i => i.Severity == severity).ToList();
    
    // Factory methods
    public static ValidationResult Success() => new();
    
    public static ValidationResult Failure(IEnumerable<string> errors)
    {
        var result = new ValidationResult();
        foreach (var error in errors)
        {
            result.Errors.Add(error);
        }
        return result;
    }
    
    public static ValidationResult Failure(IEnumerable<ValidationError> errors)
    {
        var result = new ValidationResult();
        foreach (var error in errors)
        {
            result.Errors.Add(FormatError(error));
        }
        result.Issues = errors.ToList();
        return result;
    }
    
    private static string FormatError(ValidationError error)
    {
        var parts = new List<string>();
        if (!string.IsNullOrEmpty(error.Path))
            parts.Add($"[{error.Path}]");
        if (!string.IsNullOrEmpty(error.Code))
            parts.Add($"{error.Code}:");
        parts.Add(error.Message);
        return string.Join(" ", parts);
    }
}
```

### 2.5 Error Aggregation Pipeline

```
  Validator 1    Validator 2    Validator N
  +---------+    +---------+    +---------+
  | Schema  |    | Rule    |    | Custom  |
  | Errors  |    | Errors  |    | Errors  |
  +----+----+    +----+----+    +----+----+
       |              |              |
       v              v              v
  +----------------------------------------+
  |         Error Aggregator               |
  |                                        |
  |  1. Collect all issues                 |
  |  2. Deduplicate by (code, path, msg)   |
  |  3. Group by path/category             |
  |  4. Sort by severity                   |
  |  5. Format output                      |
  +----------------+-----------------------+
                   |
                   v
  +----------------------------------------+
  |         Aggregated Result              |
  |                                        |
  |  - Structured issues                   |
  |  - Grouped errors                      |
  |  - Summary statistics                  |
  |  - Formatted output                    |
  +----------------------------------------+
```

### 2.6 Error Grouping

```csharp
public class ErrorGroup
{
    public string GroupKey { get; init; } = string.Empty;
    public string GroupLabel { get; init; } = string.Empty;
    public List<IValidationIssue> Issues { get; init; } = new();
    public int ErrorCount => Issues.Count(i => i.Severity >= IssueSeverity.Error);
    public int WarningCount => Issues.Count(i => i.Severity == IssueSeverity.Warning);
    public int InfoCount => Issues.Count(i => i.Severity == IssueSeverity.Info);
}

public enum GroupingStrategy
{
    None,
    ByPath,
    ByCode,
    BySeverity,
    ByValidator
}

public class GroupedValidationResult
{
    public bool IsValid => TotalErrors == 0;
    public int TotalErrors { get; init; }
    public int TotalWarnings { get; init; }
    public int TotalInfos { get; init; }
    public List<ErrorGroup> Groups { get; init; } = new();
    public IReadOnlyList<IValidationIssue> AllIssues { get; init; } 
        = new List<IValidationIssue>();
    
    public static GroupedValidationResult FromValidationResult(
        ValidationResult result, 
        GroupingStrategy strategy = GroupingStrategy.ByPath)
    {
        var grouped = new GroupedValidationResult
        {
            AllIssues = result.Issues,
            TotalErrors = result.ValidationErrors.Count,
            TotalWarnings = result.ValidationWarnings.Count,
        };
        
        grouped.Groups = strategy switch
        {
            GroupingStrategy.ByPath => GroupByPath(result.Issues),
            GroupingStrategy.ByCode => GroupByCode(result.Issues),
            GroupingStrategy.BySeverity => GroupBySeverity(result.Issues),
            _ => new List<ErrorGroup> { new() { 
                GroupKey = "all", 
                GroupLabel = "All Issues", 
                Issues = result.Issues.ToList() 
            }}
        };
        
        return grouped;
    }
    
    private static List<ErrorGroup> GroupByPath(IEnumerable<IValidationIssue> issues)
    {
        return issues
            .GroupBy(i => i.Path ?? "root")
            .Select(g => new ErrorGroup
            {
                GroupKey = g.Key,
                GroupLabel = g.Key == "root" ? "Root Level" : g.Key,
                Issues = g.ToList()
            })
            .OrderByDescending(g => g.ErrorCount)
            .ToList();
    }
    
    private static List<ErrorGroup> GroupByCode(IEnumerable<IValidationIssue> issues)
    {
        return issues
            .GroupBy(i => i.Code ?? "unknown")
            .Select(g => new ErrorGroup
            {
                GroupKey = g.Key,
                GroupLabel = g.Key == "unknown" ? "Unclassified" : g.Key,
                Issues = g.ToList()
            })
            .OrderByDescending(g => g.ErrorCount)
            .ToList();
    }
    
    private static List<ErrorGroup> GroupBySeverity(IEnumerable<IValidationIssue> issues)
    {
        return issues
            .GroupBy(i => i.Severity)
            .Select(g => new ErrorGroup
            {
                GroupKey = g.Key.ToString(),
                GroupLabel = $"{g.Key} ({g.Count()})",
                Issues = g.ToList()
            })
            .OrderByDescending(g => g.ErrorCount)
            .ToList();
    }
}
```

### 2.7 Error Deduplication

```csharp
public class ValidationErrorEqualityComparer : IEqualityComparer<IValidationIssue>
{
    public static readonly ValidationErrorEqualityComparer Instance = new();
    
    public bool Equals(IValidationIssue? x, IValidationIssue? y)
    {
        if (x is null || y is null) return x == y;
        return x.Code == y.Code 
            && x.Path == y.Path 
            && x.Message == y.Message;
    }
    
    public int GetHashCode(IValidationIssue obj)
    {
        return HashCode.Combine(obj.Code, obj.Path, obj.Message);
    }
}

public static class ErrorDeduplication
{
    public static IReadOnlyList<IValidationIssue> Deduplicate(
        IEnumerable<IValidationIssue> issues)
    {
        return issues
            .Distinct(ValidationErrorEqualityComparer.Instance)
            .ToList();
    }
}
```

### 2.8 Error Formatting

```csharp
public interface IErrorFormatter
{
    string Format(ValidationResult result);
    string Format(GroupedValidationResult result);
}

public class ConsoleErrorFormatter : IErrorFormatter
{
    public string Format(ValidationResult result)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Validation {(result.IsValid ? "PASSED" : "FAILED")}");
        
        if (!result.IsValid)
        {
            sb.AppendLine($"  {result.ValidationErrors.Count} error(s), " +
                         $"{result.ValidationWarnings.Count} warning(s)");
            sb.AppendLine();
            
            foreach (var error in result.ValidationErrors)
            {
                sb.AppendLine($"  ERROR [{error.Path ?? "root"}] {error.Message}");
            }
            
            foreach (var warning in result.ValidationWarnings)
            {
                sb.AppendLine($"  WARN  [{warning.Path ?? "root"}] {warning.Message}");
            }
        }
        
        return sb.ToString();
    }
    
    public string Format(GroupedValidationResult result)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Validation {(result.IsValid ? "PASSED" : "FAILED")}");
        sb.AppendLine($"  {result.TotalErrors} error(s), " +
                     $"{result.TotalWarnings} warning(s), " +
                     $"{result.TotalInfos} info(s)");
        sb.AppendLine();
        
        foreach (var group in result.Groups)
        {
            sb.AppendLine($"  [{group.GroupLabel}]");
            foreach (var issue in group.Issues)
            {
                var prefix = issue.Severity switch
                {
                    IssueSeverity.Critical => "CRIT ",
                    IssueSeverity.Error => "ERROR",
                    IssueSeverity.Warning => "WARN ",
                    _ => "INFO "
                };
                sb.AppendLine($"    {prefix} {issue.Message}");
            }
            sb.AppendLine();
        }
        
        return sb.ToString();
    }
}

public class JsonErrorFormatter : IErrorFormatter
{
    public string Format(ValidationResult result)
    {
        var output = new
        {
            isValid = result.IsValid,
            errors = result.ValidationErrors.Select(e => new
            {
                code = e.Code,
                path = e.Path,
                message = e.Message,
                property = e.PropertyName,
                attemptedValue = e.AttemptedValue,
                expectedValue = e.ExpectedValue,
                metadata = e.Metadata
            }),
            warnings = result.ValidationWarnings.Select(w => new
            {
                code = w.Code,
                path = w.Path,
                message = w.Message,
                suggestion = w.Suggestion
            })
        };
        
        return JsonSerializer.Serialize(output, new JsonSerializerOptions 
        { 
            WriteIndented = true 
        });
    }
    
    public string Format(GroupedValidationResult result)
    {
        var output = new
        {
            isValid = result.IsValid,
            summary = new
            {
                totalErrors = result.TotalErrors,
                totalWarnings = result.TotalWarnings,
                totalInfos = result.TotalInfos
            },
            groups = result.Groups.Select(g => new
            {
                key = g.GroupKey,
                label = g.GroupLabel,
                errorCount = g.ErrorCount,
                warningCount = g.WarningCount,
                issues = g.Issues.Select(i => new
                {
                    severity = i.Severity.ToString().ToLowerInvariant(),
                    code = i.Code,
                    path = i.Path,
                    message = i.Message
                })
            })
        };
        
        return JsonSerializer.Serialize(output, new JsonSerializerOptions 
        { 
            WriteIndented = true 
        });
    }
}
```

---

## 3. Consequences

### 3.1 Positive Consequences

1. **Structured Errors**: Typed error objects enable programmatic error handling, filtering, and transformation without string parsing.

2. **Error Grouping**: Grouping errors by path, code, or severity makes large error sets manageable and actionable.

3. **Deduplication**: Prevents duplicate errors from cluttering output when multiple validators report the same issue.

4. **Severity Levels**: Distinguishing between info, warning, error, and critical enables prioritized error handling.

5. **Rich Metadata**: Error metadata provides context for debugging, including attempted values, expected values, and suggestions.

6. **Multiple Output Formats**: Formatters enable errors to be presented appropriately for different contexts (console, JSON, HTML).

7. **Backward Compatibility**: Existing string-based `Errors` and `Warnings` lists are preserved, ensuring no breaking changes.

8. **Query Capabilities**: Methods like `GetIssuesForPath()` and `GetIssuesByCode()` enable targeted error inspection.

### 3.2 Negative Consequences

1. **Increased Complexity**: The structured error system is significantly more complex than flat string lists, requiring more code and documentation.

2. **Memory Overhead**: Structured error objects with metadata consume more memory than simple strings, especially for large error sets.

3. **Migration Effort**: Existing code that creates `ValidationResult.Failure(errors)` with strings will not benefit from structured errors without refactoring.

4. **Serialization Cost**: Serializing structured errors to JSON is more expensive than serializing string lists.

5. **Learning Curve**: Developers must understand the error type hierarchy, grouping strategies, and formatting options.

6. **API Surface Growth**: The expanded `ValidationResult` API increases the surface area for bugs and maintenance.

### 3.3 Neutral Consequences

1. **Immutable Records**: Using `record` types for errors ensures immutability but requires C# 9+ (already satisfied by .NET 9.0 target).

2. **Guid-Based Issue IDs**: Auto-generated issue IDs enable tracking but add minimal overhead.

3. **Dictionary Metadata**: Using `IReadOnlyDictionary<string, object>` for metadata provides flexibility but sacrifices type safety for metadata values.

4. **Extension Points**: The interface-based design enables custom formatters and grouping strategies but requires additional implementation effort.

---

## 4. Alternatives Considered

### 4.1 Alternative A: Keep String-Based Errors

**Description**: Maintain the current flat string list approach.

**Rejected Because**:
- Cannot support programmatic error handling
- No error grouping or deduplication
- No severity differentiation
- Insufficient for complex validation scenarios
- Does not scale with Phenotype ecosystem growth

### 4.2 Alternative B: Use LanguageExt Validation

**Description**: Use LanguageExt's `Validation<TSuccess, TFailure>` type.

**Rejected Because**:
- Adds significant functional programming dependency
- Steep learning curve for non-FP developers
- Incompatible with existing string-based error model
- Overkill for current needs

### 4.3 Alternative C: Use OneOf for Result Types

**Description**: Use OneOf library for discriminated union result types.

**Deferred Because**:
- Adds external dependency
- Could be adopted in future for stronger type safety
- Current approach provides sufficient structure without dependency

### 4.4 Alternative D: RFC 7807 Problem Details

**Description**: Use RFC 7807 Problem Details format directly.

**Rejected Because**:
- Designed for HTTP API responses, not general validation
- Lacks grouping and aggregation capabilities
- Too narrow in scope for Phenotype's needs
- Could be used as an output formatter (see JsonErrorFormatter)

---

## 5. Implementation Notes

### 5.1 Migration Path

```
Phase 1: Add structured types alongside existing string lists
Phase 2: Update validators to produce structured errors
Phase 3: Deprecate string-based factory methods
Phase 4: Remove string-based methods (major version bump)
```

### 5.2 Error Code Registry

Standardize error codes across the library:

```csharp
public static class ValidationCodes
{
    // Schema validation
    public const string SchemaInvalid = "SCHEMA_INVALID";
    public const string SchemaNotFound = "SCHEMA_NOT_FOUND";
    public const string TypeMismatch = "TYPE_MISMATCH";
    public const string RequiredMissing = "REQUIRED_MISSING";
    public const string FormatInvalid = "FORMAT_INVALID";
    public const string PatternMismatch = "PATTERN_MISMATCH";
    public const string RangeExceeded = "RANGE_EXCEEDED";
    public const string LengthInvalid = "LENGTH_INVALID";
    
    // YAML validation
    public const string YamlInvalid = "YAML_INVALID";
    public const string YamlParseError = "YAML_PARSE_ERROR";
    
    // Rule validation
    public const string RuleFailed = "RULE_FAILED";
    public const string RuleDeprecated = "RULE_DEPRECATED";
}
```

### 5.3 Error Suggestion Engine

```csharp
public static class ErrorSuggestions
{
    private static readonly Dictionary<string, string> Suggestions = new()
    {
        { ValidationCodes.TypeMismatch, "Check the expected type in the schema definition" },
        { ValidationCodes.RequiredMissing, "Ensure all required fields are present" },
        { ValidationCodes.FormatInvalid, "Verify the value matches the expected format" },
        { ValidationCodes.PatternMismatch, "Check the regex pattern in the schema" },
        { ValidationCodes.YamlInvalid, "Validate YAML syntax before schema validation" },
    };
    
    public static string? GetSuggestion(string code)
    {
        return Suggestions.TryGetValue(code, out var suggestion) ? suggestion : null;
    }
}
```

---

## 6. Cross-References

| Document | Relationship | Description |
|----------|-------------|-------------|
| ADR-001 | Depends | Error aggregation builds on the validation result structure |
| ADR-002 | Consumes | Rule engine produces structured errors for aggregation |
| VALIDATION_FRAMEWORKS_SOTA | Informs | SOTA research on error patterns informed this decision |
| SPEC.md | Specifies | Full specification of error handling |

---

*This ADR is proposed for review by the Phenotype Architecture Team. Review date: 2026-04-10.*
