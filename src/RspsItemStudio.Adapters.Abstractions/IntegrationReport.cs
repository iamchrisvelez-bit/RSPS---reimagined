namespace RspsItemStudio.Adapters.Abstractions;

public enum IntegrationEntryStatus
{
    Skipped,
    NotPacked,
    WouldWrite,
    Written
}

public sealed class IntegrationReportEntry
{
    public required string Category { get; init; }
    public IntegrationEntryStatus Status { get; init; }
    public required string Message { get; init; }
}

public sealed class IntegrationReport
{
    public DateTimeOffset GeneratedAt { get; init; } = DateTimeOffset.UtcNow;
    public required string AdapterId { get; init; }
    public string? StagingDirectory { get; init; }
    public string Summary { get; init; } = "";
    public List<IntegrationReportEntry> Entries { get; init; } = new();
}
