namespace RspsItemStudio.Validation;

public sealed class ValidationReport
{
    public DateTimeOffset GeneratedAt { get; init; }
    public List<ValidationIssue> Issues { get; init; } = new();
    public bool HasErrors => Issues.Any(i => i.Severity == ValidationSeverity.Error);
}
