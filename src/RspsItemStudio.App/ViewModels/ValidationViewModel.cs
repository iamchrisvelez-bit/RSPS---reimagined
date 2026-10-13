using System.Collections.ObjectModel;
using RspsItemStudio.Validation;

namespace RspsItemStudio.App.ViewModels;

/// <summary>
/// Placeholder for validation report UI (Task 8 wires <see cref="ItemProjectValidator"/>).
/// </summary>
public sealed class ValidationViewModel : ViewModelBase
{
    public ObservableCollection<string> IssueSummaries { get; } = new();

    private string _summaryText = "Run Validate to check the project.";

    public string SummaryText
    {
        get => _summaryText;
        private set => SetProperty(ref _summaryText, value);
    }

    public void Clear()
    {
        IssueSummaries.Clear();
        SummaryText = "Run Validate to check the project.";
    }

    public void SetPlaceholder(string message)
    {
        IssueSummaries.Clear();
        SummaryText = message;
    }
}
