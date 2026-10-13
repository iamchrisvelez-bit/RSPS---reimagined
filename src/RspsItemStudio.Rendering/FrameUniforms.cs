using System.Numerics;
using System.Runtime.InteropServices;

namespace RspsItemStudio.Rendering;

[StructLayout(LayoutKind.Sequential)]
internal struct FrameUniforms
{
    public Matrix4x4 View;
    public Matrix4x4 Projection;
    public Vector4 LightAndMode;
}
