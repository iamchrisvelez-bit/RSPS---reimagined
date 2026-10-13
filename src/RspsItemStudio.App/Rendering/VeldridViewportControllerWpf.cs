using System.Windows.Interop;
using RspsItemStudio.Rendering;

namespace RspsItemStudio.App.Rendering;

public static class VeldridViewportControllerWpf
{
    public static void Attach(this VeldridViewportController controller, HwndSource hwndSource, int width, int height) =>
        controller.Attach(hwndSource.Handle, width, height);
}
