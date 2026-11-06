using YamlDotNet.Serialization;
using Newtonsoft.Json;

namespace Phenotype.Validation;

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
    
    public Task<ValidationResult> ValidateAsync(string document, string schema, CancellationToken ct = default)
    {
        return Task.FromResult(Validate(schema, document));
    }
}
