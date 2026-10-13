using RspsItemStudio.Core.Meshes;
using RspsItemStudio.Rendering;

namespace RspsItemStudio.App.ViewModels;

public sealed class ViewportViewModel : ViewModelBase
{
    private ViewportDisplayMode _displayMode = ViewportDisplayMode.Solid;
    private StudioMesh? _pendingMesh;

    internal VeldridViewportController? Controller { get; private set; }

    public ViewportDisplayMode DisplayMode
    {
        get => _displayMode;
        set
        {
            if (SetProperty(ref _displayMode, value))
                Controller?.SetDisplayMode(value);
        }
    }

    public Array DisplayModes => Enum.GetValues(typeof(ViewportDisplayMode));

    public void LoadMesh(StudioMesh mesh)
    {
        if (Controller is not null)
            Controller.LoadMesh(mesh);
        else
            _pendingMesh = mesh;
    }

    internal void BindController(VeldridViewportController controller)
    {
        Controller = controller;
        controller.SetDisplayMode(DisplayMode);
        if (_pendingMesh is not null)
        {
            controller.LoadMesh(_pendingMesh);
            _pendingMesh = null;
        }
    }

    internal void ReleaseController()
    {
        Controller = null;
    }
}
