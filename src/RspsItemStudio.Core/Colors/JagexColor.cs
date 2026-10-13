namespace RspsItemStudio.Core.Colors;

/// <summary>
/// Jagex packed 16-bit HSL (6-bit hue, 3-bit saturation, 7-bit lightness).
/// </summary>
public static class JagexColor
{
    public static int PackHsl(int hue, int saturation, int lightness)
    {
        hue = Clamp(hue, 0, 63);
        saturation = Clamp(saturation, 0, 7);
        lightness = Clamp(lightness, 0, 127);
        return (hue << 10) | (saturation << 7) | lightness;
    }

    public static void UnpackHsl(int packed, out int h, out int s, out int l)
    {
        l = packed & 0x7F;
        s = (packed >> 7) & 0x7;
        h = (packed >> 10) & 0x3F;
    }

    /// <summary>
    /// Converts packed Jagex HSL to RGB.
    /// <para>
    /// Unpacks hue/saturation/lightness, maps to standard HSL degrees and percentages
    /// (hue° = h/63×360, sat% = s/7×100, lum% = 100 when l=127 else l/170×100),
    /// then applies the usual HSL→RGB piecewise linear approximation:
    /// a = s×(1−|2L−1|), c = L−a/2, sector RGB from hue/60, R/G/B = floor(255×(channel+c)).
    /// </para>
    /// </summary>
    public static (byte r, byte g, byte b) ToRgb(int packedHsl)
    {
        UnpackHsl(packedHsl, out var hue, out var sat, out var lum);

        var hueDegrees = hue / 63.0 * 360.0;
        var satPercent = sat / 7.0 * 100.0;
        var lumPercent = lum == 127 ? 100.0 : lum / 170.0 * 100.0;

        return HslPercentToRgb(hueDegrees, satPercent, lumPercent);
    }

    private static (byte r, byte g, byte b) HslPercentToRgb(double hueDegrees, double satPercent, double lumPercent)
    {
        var s = satPercent / 100.0;
        var l = lumPercent / 100.0;
        var a = s * (1.0 - Math.Abs(2.0 * l - 1.0));
        var c = l - a / 2.0;
        var hueMod = hueDegrees % 360.0;
        if (hueMod < 0)
            hueMod += 360.0;

        double r1;
        double g1;
        double b1;
        if (hueMod < 60)
        {
            r1 = a;
            g1 = a * (1.0 - Math.Abs(hueMod / 60.0 % 2.0 - 1.0));
            b1 = 0;
        }
        else if (hueMod < 120)
        {
            g1 = a;
            r1 = a * (1.0 - Math.Abs(hueMod / 60.0 % 2.0 - 1.0));
            b1 = 0;
        }
        else if (hueMod < 180)
        {
            g1 = a;
            b1 = a * (1.0 - Math.Abs(hueMod / 60.0 % 2.0 - 1.0));
            r1 = 0;
        }
        else if (hueMod < 240)
        {
            b1 = a;
            g1 = a * (1.0 - Math.Abs(hueMod / 60.0 % 2.0 - 1.0));
            r1 = 0;
        }
        else if (hueMod < 300)
        {
            b1 = a;
            r1 = a * (1.0 - Math.Abs(hueMod / 60.0 % 2.0 - 1.0));
            g1 = 0;
        }
        else
        {
            r1 = a;
            b1 = a * (1.0 - Math.Abs(hueMod / 60.0 % 2.0 - 1.0));
            g1 = 0;
        }

        var r = Math.Max(0, (int)Math.Floor(255.0 * (r1 + c)));
        var g = Math.Max(0, (int)Math.Floor(255.0 * (g1 + c)));
        var b = Math.Max(0, (int)Math.Floor(255.0 * (b1 + c)));
        return ((byte)Math.Min(255, r), (byte)Math.Min(255, g), (byte)Math.Min(255, b));
    }

    private static int Clamp(int value, int min, int max) =>
        value < min ? min : value > max ? max : value;
}
