using System.Collections.ObjectModel;
using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Core.Projects;
using RspsItemStudio.Validation;

namespace RspsItemStudio.App.ViewModels;

public sealed class ValidationViewModel : ViewModelBase
{
    public ObservableCollection<string> IssueSummaries { get; } = new();

    private string _summaryText = "Run Validate to check the project.";

    public string SummaryText
    {
        get => _summaryText;
        private set => SetProperty(ref _summaryText, value);
    }

    public int ErrorCount { get; private set; }

    public void Clear()
    {
        IssueSummaries.Clear();
        ErrorCount = 0;
        SummaryText = "Run Validate to check the project.";
    }

    public void Run(ItemProject project)
    {
        var report = ItemProjectValidator.Validate(project);
        project.SaveValidationReport(report);
        ShowValidationReport(report);
    }

    public void ShowValidationReport(ValidationReport report)
    {
        IssueSummaries.Clear();
        foreach (var issue in report.Issues)
            IssueSummaries.Add(FormatIssue(issue));

        ErrorCount = report.Issues.Count(i => i.Severity == ValidationSeverity.Error);
        var warnings = report.Issues.Count(i => i.Severity == ValidationSeverity.Warning);
        var infos = report.Issues.Count(i => i.Severity == ValidationSeverity.Info);

        SummaryText = report.Issues.Count == 0
            ? "No issues found."
            : $"{report.Issues.Count} issue(s): {ErrorCount} error(s), {warnings} warning(s), {infos} info.";
    }

    public void ShowIntegrationReport(IntegrationReport report)
    {
        IssueSummaries.Clear();
        ErrorCount = 0;

        if (!string.IsNullOrEmpty(report.StagingDirectory))
            IssueSummaries.Add($"Staging directory: {report.StagingDirectory}");

        foreach (var entry in report.Entries)
            IssueSummaries.Add($"[{entry.Status}] {entry.Category}: {entry.Message}");

        SummaryText = string.IsNullOrWhiteSpace(report.Summary)
            ? $"Staging export ({report.AdapterId}) — see entries below."
            : report.Summary;
    }

    private static string FormatIssue(ValidationIssue issue)
    {
        var path = string.IsNullOrEmpty(issue.Path) ? "" : $" [{issue.Path}]";
        return $"[{issue.Severity}] {issue.Code}: {issue.Message}{path}";
    }
}
