using System.IO;
using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Adapters.OpenRune;
using RspsItemStudio.App.Services;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Json;
using RspsItemStudio.Core.Meshes;
using RspsItemStudio.Core.Projects;
using RspsItemStudio.Modeling;
using RspsItemStudio.Validation;

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
                TryLoadInventoryMeshIntoViewport();
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
        if (CurrentProject is null)
            return;

        if (!_dialogs.TryPickObjFile(out var objPath) || objPath is null)
            return;

        try
        {
            var result = ObjMeshImporter.Import(objPath);
            CurrentProject.AttachInventoryMesh(result.Mesh, objPath);
            Viewport.LoadMesh(result.Mesh);

            var warningText = result.Warnings.Count > 0
                ? $" Warnings: {string.Join("; ", result.Warnings)}"
                : string.Empty;
            StatusText =
                $"Imported \"{result.Mesh.Name}\" ({result.Mesh.Vertices.Count} verts, {result.Mesh.Triangles.Count} tris).{warningText}";
        }
        catch (Exception ex)
        {
            StatusText = $"OBJ import failed: {ex.Message}";
        }
    }

    private void TryLoadInventoryMeshIntoViewport()
    {
        if (CurrentProject is null)
            return;

        var meshPath = Path.Combine(CurrentProject.RootDirectory, ItemProjectPaths.InventoryMesh);
        if (!File.Exists(meshPath))
            return;

        try
        {
            var mesh = StudioJson.Deserialize<StudioMesh>(File.ReadAllText(meshPath));
            if (mesh is not null)
                Viewport.LoadMesh(mesh);
        }
        catch
        {
            // Viewport preview is best-effort when opening a project.
        }
    }

    private void Validate()
    {
        if (CurrentProject is null)
            return;

        Validation.Run(CurrentProject);

        StatusText = Validation.ErrorCount > 0
            ? $"Validation finished with {Validation.ErrorCount} error(s). See Validation tab."
            : "Validation finished. See Validation tab for details.";
        OnPropertyChanged(nameof(ProjectDisplayName));
    }

    private void ExportStaging()
    {
        if (CurrentProject is null)
            return;

        var project = CurrentProject;
        var report = ItemProjectValidator.Validate(project);
        project.SaveValidationReport(report);
        Validation.ShowValidationReport(report);

        if (report.HasErrors)
        {
            StatusText = "Export blocked by validation errors.";
            return;
        }

        try
        {
            var adapter = new OpenRuneAdapter();
            var result = adapter.Cache.PackToStaging(new ExportStagingRequest
            {
                Project = project,
                Preset = project.ExportPresets.Presets.FirstOrDefault() ?? new ExportPreset()
            });

            if (!result.Success)
            {
                StatusText = result.Message ?? "Staging export failed.";
                return;
            }

            if (result.Value is not null)
            {
                IntegrationReportWriter.Save(project, result.Value);
                Validation.ShowIntegrationReport(result.Value);
            }

            StatusText = result.Message ?? (result.Value?.Summary ?? "Export finished.");
        }
        catch (Exception ex)
        {
            StatusText = $"Staging export failed: {ex.Message}";
        }
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
