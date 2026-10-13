using RspsItemStudio.Definitions;

namespace RspsItemStudio.App.ViewModels;

/// <summary>
/// Placeholder wrapper for stat editor binding (Task 8 expands this).
/// </summary>
public sealed class ItemDefinitionViewModel : ViewModelBase
{
    private ItemDefinitionDocument? _document;

    public ItemDefinitionDocument? Document
    {
        get => _document;
        private set => SetProperty(ref _document, value);
    }

    public string? DisplayName => Document?.Name;

    public void Attach(ItemDefinitionDocument? document)
    {
        Document = document;
        OnPropertyChanged(nameof(DisplayName));
    }
}
