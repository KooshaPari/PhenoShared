using Xunit;

namespace Phenotype.Validation.Tests;

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
        // Schema requires array, document is object
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
