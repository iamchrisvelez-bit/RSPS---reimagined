using RspsItemStudio.Core.Colors;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class JagexColorTests
{
    [Fact]
    public void Pack_unpack_roundTrip()
    {
        var packed = JagexColor.PackHsl(33, 3, 40);
        JagexColor.UnpackHsl(packed, out var h, out var s, out var l);
        Assert.Equal(33, h);
        Assert.Equal(3, s);
        Assert.Equal(40, l);
    }

    [Fact]
    public void ToRgb_returns_bytes_in_range()
    {
        var (r, g, b) = JagexColor.ToRgb(JagexColor.PackHsl(0, 0, 64));
        Assert.InRange(r, (byte)0, (byte)255);
        Assert.InRange(g, (byte)0, (byte)255);
        Assert.InRange(b, (byte)0, (byte)255);
    }
}
