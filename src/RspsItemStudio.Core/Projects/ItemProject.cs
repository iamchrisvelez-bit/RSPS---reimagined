using RspsItemStudio.Core.Animations;
using RspsItemStudio.Core.Colors;
using RspsItemStudio.Core.Effects;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Json;
using RspsItemStudio.Core.Materials;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Core.Projects;

public sealed class ItemProject
{
    public required string RootDirectory { get; init; }
    public required ItemStudioManifest Manifest { get; init; }
    public required ItemDefinitionDocument Definition { get; init; }
    public required RecolorDocument Recolor { get; init; }
    public required MaterialsDocument Materials { get; init; }
    public required AnimationBindingsDocument Animations { get; init; }
    public required EffectsDocument Effects { get; init; }
    public required ExportPresetsDocument ExportPresets { get; init; }

    public void Save()
    {
        WriteJson(ItemProjectPaths.Manifest, Manifest);
        WriteJson(ItemProjectPaths.Definition, Definition);
        WriteJson(ItemProjectPaths.Recolor, Recolor);
        WriteJson(ItemProjectPaths.Materials, Materials);
        WriteJson(ItemProjectPaths.Animations, Animations);
        WriteJson(ItemProjectPaths.Effects, Effects);
        WriteJson(ItemProjectPaths.ExportPresets, ExportPresets);
    }

    public void SaveValidationReport<T>(T report) =>
        WriteJson(ItemProjectPaths.ValidationReport, report);

    private void WriteJson<T>(string relativePath, T value)
    {
        var fullPath = Path.Combine(RootDirectory, relativePath);
        var directory = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(directory))
            Directory.CreateDirectory(directory);
        File.WriteAllText(fullPath, StudioJson.Serialize(value));
    }
}
