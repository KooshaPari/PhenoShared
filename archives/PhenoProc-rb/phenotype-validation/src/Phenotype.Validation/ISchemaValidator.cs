namespace Phenotype.Validation;

public interface ISchemaValidator<TSchema, TDocument>
{
    ValidationResult Validate(TSchema schema, TDocument document);
    Task<ValidationResult> ValidateAsync(TDocument document, TSchema schema, CancellationToken ct = default);
}

public interface IJsonSchemaValidator : ISchemaValidator<string, string>
{
    void AddSchema(string name, string schemaContent);
    Task<ValidationResult> ValidateAgainstNamedSchemaAsync(string document, string schemaName, CancellationToken ct = default);
}
