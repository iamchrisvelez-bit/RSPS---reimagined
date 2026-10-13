namespace RspsItemStudio.Core.Colors;

public sealed class RecolorDocument
{
    public int? PrimaryHsl { get; set; }
    public int? SecondaryHsl { get; set; }
    public int? DetailHsl { get; set; }
    public string? PrimaryRgb { get; set; }
    public string? SecondaryRgb { get; set; }
    public string? DetailRgb { get; set; }
    public Dictionary<string, int> Presets { get; set; } = new();
}
