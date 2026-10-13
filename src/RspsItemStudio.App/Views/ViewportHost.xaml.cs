using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using RspsItemStudio.App.Rendering;
using RspsItemStudio.App.ViewModels;
using RspsItemStudio.Rendering;

namespace RspsItemStudio.App.Views;

public partial class ViewportHost : UserControl
{
    private VeldridHwndHost? _hwndHost;
    private VeldridViewportController? _controller;
    private ViewportViewModel? _viewportModel;
    private Point _lastMouse;
    private bool _orbitDrag;
    private bool _panDrag;

    public ViewportHost()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Unloaded += OnUnloaded;
        DataContextChanged += (_, _) => _viewportModel = DataContext as ViewportViewModel;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        _viewportModel = DataContext as ViewportViewModel;
        _hwndHost = new VeldridHwndHost();
        _controller = new VeldridViewportController();
        _viewportModel?.BindController(_controller);

        _hwndHost.Ready += OnHostReady;
        _hwndHost.Controller = _controller;
        ViewportGrid.Children.Insert(0, _hwndHost);

        if (_hwndHost.Handle != IntPtr.Zero)
            TryAttachHost();

        CompositionTarget.Rendering += OnRendering;
        _controller.Resize((int)Math.Max(1, ActualWidth), (int)Math.Max(1, ActualHeight));
    }

    private void OnUnloaded(object sender, RoutedEventArgs e)
    {
        CompositionTarget.Rendering -= OnRendering;
        _viewportModel?.ReleaseController();
        _hwndHost?.Ready -= OnHostReady;
        _controller?.Dispose();
        _controller = null;
    }

    private void OnHostReady(object? sender, EventArgs e) => TryAttachHost();

    private void TryAttachHost()
    {
        if (_controller is null || _hwndHost is null || _hwndHost.Handle == IntPtr.Zero)
            return;

        var source = HwndSource.FromHwnd(_hwndHost.Handle);
        if (source is null)
            return;

        var width = (int)Math.Max(1, ActualWidth);
        var height = (int)Math.Max(1, ActualHeight);
        _controller.Attach(source, width, height);
    }

    private void OnRendering(object? sender, EventArgs e) =>
        _controller?.Render();

    private void OnSizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (_controller is null)
            return;

        var width = (int)Math.Max(1, ActualWidth);
        var height = (int)Math.Max(1, ActualHeight);
        _controller.Resize(width, height);
    }

    private void OnPreviewMouseLeftButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        _orbitDrag = true;
        _lastMouse = e.GetPosition(this);
        CaptureMouse();
    }

    private void OnPreviewMouseRightButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        _panDrag = true;
        _lastMouse = e.GetPosition(this);
        CaptureMouse();
    }

    private void OnPreviewMouseLeftButtonUp(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        _orbitDrag = false;
        if (!_panDrag)
            ReleaseMouseCapture();
    }

    private void OnPreviewMouseRightButtonUp(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        _panDrag = false;
        if (!_orbitDrag)
            ReleaseMouseCapture();
    }

    private void OnPreviewMouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (_controller is null)
            return;

        var pos = e.GetPosition(this);
        var dx = (float)(pos.X - _lastMouse.X);
        var dy = (float)(pos.Y - _lastMouse.Y);
        _lastMouse = pos;

        if (_orbitDrag)
            _controller.Camera.Orbit(dx * 0.01f, dy * 0.01f);
        else if (_panDrag)
            _controller.Camera.Pan(dx, dy);
    }

    private void OnPreviewMouseWheel(object sender, System.Windows.Input.MouseWheelEventArgs e)
    {
        _controller?.Camera.Zoom(e.Delta > 0 ? 0.1f : -0.1f);
    }

    private sealed class VeldridHwndHost : HwndHost
    {
        public event EventHandler? Ready;
        public VeldridViewportController? Controller { get; set; }
        public IntPtr Handle { get; private set; }

        protected override HandleRef BuildWindowCore(HandleRef hwndParent)
        {
            Handle = CreateWindowEx(
                0,
                "static",
                string.Empty,
                WsChild | WsVisible | WsClipChildren | WsClipsiblings,
                0,
                0,
                10,
                10,
                hwndParent.Handle,
                IntPtr.Zero,
                IntPtr.Zero,
                IntPtr.Zero);

            Ready?.Invoke(this, EventArgs.Empty);
            return new HandleRef(this, Handle);
        }

        protected override void DestroyWindowCore(HandleRef hwnd) =>
            DestroyWindow(hwnd.Handle);

        protected override IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled) =>
            base.WndProc(hwnd, msg, wParam, lParam, ref handled);

        private const int WsChild = 0x40000000;
        private const int WsVisible = 0x10000000;
        private const int WsClipChildren = 0x02000000;
        private const int WsClipsiblings = 0x04000000;

        [DllImport("user32.dll", EntryPoint = "CreateWindowEx", CharSet = CharSet.Unicode)]
        private static extern IntPtr CreateWindowEx(
            int exStyle,
            string lpszClassName,
            string lpszWindowName,
            int style,
            int x,
            int y,
            int width,
            int height,
            IntPtr hwndParent,
            IntPtr hMenu,
            IntPtr hInst,
            IntPtr pvParam);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool DestroyWindow(IntPtr hwnd);
    }
}
