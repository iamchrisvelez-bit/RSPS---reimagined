namespace RspsItemStudio.App.ViewModels;

/// <summary>
/// Placeholder for Veldrid viewport state (Task 9).
/// </summary>
public sealed class ViewportViewModel : ViewModelBase
{
    private string _placeholderText = "3D viewport will host here (Task 9).";

    public string PlaceholderText
    {
        get => _placeholderText;
        set => SetProperty(ref _placeholderText, value);
    }
}
