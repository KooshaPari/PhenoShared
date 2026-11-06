namespace Phenotype.Validation;

public class ValidationResult
{
    public bool IsValid { get; set; }
    public List<string> Errors { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
    
    public static ValidationResult Success() => new() { IsValid = true };
    public static ValidationResult Failure(IEnumerable<string> errors) => 
        new() { IsValid = false, Errors = errors.ToList() };
}
