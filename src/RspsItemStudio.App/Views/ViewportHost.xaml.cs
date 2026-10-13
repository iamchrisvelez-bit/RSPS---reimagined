using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
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
        _hwndHost.NativeMouse += OnNativeMouse;
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
        if (_hwndHost is not null)
        {
            _hwndHost.Ready -= OnHostReady;
            _hwndHost.NativeMouse -= OnNativeMouse;
            ViewportGrid.Children.Remove(_hwndHost);
            _hwndHost.Dispose();
            _hwndHost = null;
        }

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

    private void OnNativeMouse(object? sender, NativeMouseEventArgs e)
    {
        if (_controller is null)
            return;

        switch (e.Kind)
        {
            case NativeMouseKind.LeftDown:
                _orbitDrag = true;
                _panDrag = false;
                _lastMouse = e.Position;
                break;
            case NativeMouseKind.RightDown:
                _panDrag = true;
                _orbitDrag = false;
                _lastMouse = e.Position;
                break;
            case NativeMouseKind.LeftUp:
                _orbitDrag = false;
                break;
            case NativeMouseKind.RightUp:
                _panDrag = false;
                break;
            case NativeMouseKind.Move:
                var dx = (float)(e.Position.X - _lastMouse.X);
                var dy = (float)(e.Position.Y - _lastMouse.Y);
                _lastMouse = e.Position;
                if (_orbitDrag)
                    _controller.Camera.Orbit(dx * 0.01f, dy * 0.01f);
                else if (_panDrag)
                    _controller.Camera.Pan(dx, dy);
                break;
            case NativeMouseKind.Wheel:
                _controller.Camera.Zoom(e.WheelDelta > 0 ? 0.1f : -0.1f);
                break;
        }
    }

    private void OnPreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e) =>
        BeginOrbit(e.GetPosition(this));

    private void OnPreviewMouseRightButtonDown(object sender, MouseButtonEventArgs e) =>
        BeginPan(e.GetPosition(this));

    private void OnPreviewMouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        _orbitDrag = false;
        if (!_panDrag)
            ReleaseMouseCapture();
    }

    private void OnPreviewMouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        _panDrag = false;
        if (!_orbitDrag)
            ReleaseMouseCapture();
    }

    private void OnPreviewMouseMove(object sender, MouseEventArgs e)
    {
        if (_controller is null || (!_orbitDrag && !_panDrag))
            return;

        var pos = e.GetPosition(this);
        var dx = (float)(pos.X - _lastMouse.X);
        var dy = (float)(pos.Y - _lastMouse.Y);
        _lastMouse = pos;

        if (_orbitDrag)
            _controller.Camera.Orbit(dx * 0.01f, dy * 0.01f);
        else
            _controller.Camera.Pan(dx, dy);
    }

    private void OnPreviewMouseWheel(object sender, MouseWheelEventArgs e) =>
        _controller?.Camera.Zoom(e.Delta > 0 ? 0.1f : -0.1f);

    private void BeginOrbit(Point position)
    {
        _orbitDrag = true;
        _panDrag = false;
        _lastMouse = position;
        CaptureMouse();
    }

    private void BeginPan(Point position)
    {
        _panDrag = true;
        _orbitDrag = false;
        _lastMouse = position;
        CaptureMouse();
    }

    private enum NativeMouseKind
    {
        LeftDown,
        LeftUp,
        RightDown,
        RightUp,
        Move,
        Wheel
    }

    private sealed class NativeMouseEventArgs : EventArgs
    {
        public required NativeMouseKind Kind { get; init; }
        public Point Position { get; init; }
        public int WheelDelta { get; init; }
    }

    private sealed class VeldridHwndHost : HwndHost
    {
        public event EventHandler? Ready;
        public event EventHandler<NativeMouseEventArgs>? NativeMouse;
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

        protected override IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            switch (msg)
            {
                case WmLButtonDown:
                    SetCapture(hwnd);
                    RaiseMouse(NativeMouseKind.LeftDown, lParam);
                    handled = true;
                    return IntPtr.Zero;
                case WmRButtonDown:
                    SetCapture(hwnd);
                    RaiseMouse(NativeMouseKind.RightDown, lParam);
                    handled = true;
                    return IntPtr.Zero;
                case WmLButtonUp:
                    ReleaseCapture();
                    RaiseMouse(NativeMouseKind.LeftUp, lParam);
                    handled = true;
                    return IntPtr.Zero;
                case WmRButtonUp:
                    ReleaseCapture();
                    RaiseMouse(NativeMouseKind.RightUp, lParam);
                    handled = true;
                    return IntPtr.Zero;
                case WmMouseMove:
                    RaiseMouse(NativeMouseKind.Move, lParam);
                    handled = true;
                    return IntPtr.Zero;
                case WmMouseWheel:
                    var delta = (short)((wParam.ToInt64() >> 16) & 0xFFFF);
                    NativeMouse?.Invoke(this, new NativeMouseEventArgs
                    {
                        Kind = NativeMouseKind.Wheel,
                        Position = PointFromLParam(lParam),
                        WheelDelta = delta
                    });
                    handled = true;
                    return IntPtr.Zero;
            }

            return base.WndProc(hwnd, msg, wParam, lParam, ref handled);
        }

        private void RaiseMouse(NativeMouseKind kind, IntPtr lParam) =>
            NativeMouse?.Invoke(this, new NativeMouseEventArgs
            {
                Kind = kind,
                Position = PointFromLParam(lParam)
            });

        private static Point PointFromLParam(IntPtr lParam)
        {
            var value = lParam.ToInt32();
            var x = (short)(value & 0xFFFF);
            var y = (short)((value >> 16) & 0xFFFF);
            return new Point(x, y);
        }

        private const int WsChild = 0x40000000;
        private const int WsVisible = 0x10000000;
        private const int WsClipChildren = 0x02000000;
        private const int WsClipsiblings = 0x04000000;
        private const int WmMouseMove = 0x0200;
        private const int WmLButtonDown = 0x0201;
        private const int WmLButtonUp = 0x0202;
        private const int WmRButtonDown = 0x0204;
        private const int WmRButtonUp = 0x0205;
        private const int WmMouseWheel = 0x020A;

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

        [DllImport("user32.dll")]
        private static extern IntPtr SetCapture(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool ReleaseCapture();
    }
}
