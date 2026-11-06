using Newtonsoft.Json.Linq;
using NJsonSchema;

namespace Phenotype.Validation;

public class JsonSchemaValidator : IJsonSchemaValidator
{
    private readonly Dictionary<string, JsonSchema> _schemaCache = new();
    
    public ValidationResult Validate(string schema, string document)
    {
        return ValidateAsync(document, schema).GetAwaiter().GetResult();
    }
    
    public async Task<ValidationResult> ValidateAsync(string document, string schema, CancellationToken ct = default)
    {
        try
        {
            var jsonSchema = await JsonSchema.FromJsonAsync(schema, ct);
            var errors = jsonSchema.Validate(document);
            
            if (!errors.Any())
                return ValidationResult.Success();
                
            return ValidationResult.Failure(errors.Select(e => $"[{e.Path}] {e.Kind}: {e.Property}"));
        }
        catch (Exception ex)
        {
            return ValidationResult.Failure(new[] { ex.Message });
        }
    }
    
    public void AddSchema(string name, string schemaContent)
    {
        var schema = JsonSchema.FromJsonAsync(schemaContent).GetAwaiter().GetResult();
        _schemaCache[name] = schema;
    }
    
    public async Task<ValidationResult> ValidateAgainstNamedSchemaAsync(string document, string schemaName, CancellationToken ct = default)
    {
        if (!_schemaCache.TryGetValue(schemaName, out var schema))
            return ValidationResult.Failure(new[] { $"Schema '{schemaName}' not found" });
            
        var errors = schema.Validate(document);
        if (!errors.Any()) return ValidationResult.Success();
        return ValidationResult.Failure(errors.Select(e => $"[{e.Path}] {e.Kind}"));
    }
}
