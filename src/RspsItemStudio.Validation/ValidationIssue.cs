namespace RspsItemStudio.Validation;

public sealed class ValidationIssue
{
    public ValidationSeverity Severity { get; init; }
    public string Code { get; init; } = "";
    public string Message { get; init; } = "";
    public string? Path { get; init; }
}
