using System.IO;
using RspsItemStudio.App.Services;
using RspsItemStudio.Core.Projects;

namespace RspsItemStudio.App.ViewModels;

public sealed class MainViewModel : ViewModelBase
{
    private readonly ProjectDialogService _dialogs;

    private ItemProject? _currentProject;
    private string _statusText = "Create or open an item project to begin.";
    private string _projectSummary = "No project loaded.";

    public MainViewModel()
        : this(new ProjectDialogService())
    {
    }

    public MainViewModel(ProjectDialogService dialogs)
    {
        _dialogs = dialogs;

        NewProjectCommand = new RelayCommand(NewProject, () => true);
        OpenProjectCommand = new RelayCommand(OpenProject, () => true);
        SaveProjectCommand = new RelayCommand(SaveProject, () => CurrentProject is not null);
        ImportObjCommand = new RelayCommand(ImportObj, () => CurrentProject is not null);
        ValidateCommand = new RelayCommand(Validate, () => CurrentProject is not null);
        ExportStagingCommand = new RelayCommand(ExportStaging, () => CurrentProject is not null);

        Definition = new ItemDefinitionViewModel();
        Validation = new ValidationViewModel();
        Viewport = new ViewportViewModel();
    }

    public ItemProject? CurrentProject
    {
        get => _currentProject;
        private set
        {
            if (SetProject(ref _currentProject, value))
            {
                OnPropertyChanged(nameof(ProjectDisplayName));
                OnPropertyChanged(nameof(HasProject));
                RefreshProjectSummary();
                Definition.Attach(value?.Definition);
                Validation.Clear();
                SaveProjectCommand.RaiseCanExecuteChanged();
                ImportObjCommand.RaiseCanExecuteChanged();
                ValidateCommand.RaiseCanExecuteChanged();
                ExportStagingCommand.RaiseCanExecuteChanged();
            }
        }
    }

    public string ProjectDisplayName =>
        CurrentProject?.Manifest.DisplayName ?? CurrentProject?.Definition.Name ?? "Untitled";

    public bool HasProject => CurrentProject is not null;

    public string StatusText
    {
        get => _statusText;
        private set => SetProperty(ref _statusText, value);
    }

    public string ProjectSummary
    {
        get => _projectSummary;
        private set => SetProperty(ref _projectSummary, value);
    }

    public ItemDefinitionViewModel Definition { get; }
    public ValidationViewModel Validation { get; }
    public ViewportViewModel Viewport { get; }

    public RelayCommand NewProjectCommand { get; }
    public RelayCommand OpenProjectCommand { get; }
    public RelayCommand SaveProjectCommand { get; }
    public RelayCommand ImportObjCommand { get; }
    public RelayCommand ValidateCommand { get; }
    public RelayCommand ExportStagingCommand { get; }

    private void NewProject()
    {
        if (!_dialogs.TryPickNewProjectLocation(out var root, out var displayName) ||
            root is null ||
            displayName is null)
            return;

        if (Directory.Exists(root) && Directory.EnumerateFileSystemEntries(root).Any())
        {
            StatusText = $"Cannot create project: folder already exists and is not empty ({root}).";
            return;
        }

        try
        {
            CurrentProject = ItemProjectFactory.Create(root, displayName);
            StatusText = $"Created project \"{displayName}\" at {root}.";
        }
        catch (Exception ex)
        {
            StatusText = $"Failed to create project: {ex.Message}";
        }
    }

    private void OpenProject()
    {
        if (!_dialogs.TryPickExistingProjectRoot(out var root) || root is null)
            return;

        try
        {
            CurrentProject = ItemProjectLoader.Load(root);
            StatusText = $"Opened project at {root}.";
        }
        catch (Exception ex)
        {
            StatusText = $"Failed to open project: {ex.Message}";
        }
    }

    private void SaveProject()
    {
        if (CurrentProject is null)
            return;

        try
        {
            CurrentProject.Save();
            StatusText = $"Saved project at {CurrentProject.RootDirectory}.";
        }
        catch (Exception ex)
        {
            StatusText = $"Failed to save project: {ex.Message}";
        }
    }

    private void ImportObj()
    {
        StatusText = "Import OBJ — coming in Task 9.";
    }

    private void Validate()
    {
        Validation.SetPlaceholder("Validation UI — coming in Task 8.");
        StatusText = "Validate — coming in Task 8.";
    }

    private void ExportStaging()
    {
        StatusText = "Export staging — coming in Task 10.";
    }

    private void RefreshProjectSummary()
    {
        if (CurrentProject is null)
        {
            ProjectSummary = "No project loaded.";
            return;
        }

        ProjectSummary =
            $"Name: {ProjectDisplayName}\nRoot: {CurrentProject.RootDirectory}\nManifest: {ItemProjectPaths.Manifest}";
    }

    private bool SetProject(ref ItemProject? field, ItemProject? value)
    {
        if (ReferenceEquals(field, value))
            return false;
        field = value;
        OnPropertyChanged(nameof(CurrentProject));
        return true;
    }
}
