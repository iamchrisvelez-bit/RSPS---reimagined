namespace RspsItemStudio.Core.Export;

public sealed class ExportPresetsDocument
{
    public List<ExportPreset> Presets { get; set; } = new();
}

public sealed class ExportPreset
{
    public string AdapterId { get; set; } = "openrune";
    public int? ItemId { get; set; }
    public string StagingDirectory { get; set; } = "export/staging";
}
