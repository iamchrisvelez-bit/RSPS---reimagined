using RspsItemStudio.Core.Animations;
using RspsItemStudio.Core.Colors;
using RspsItemStudio.Core.Effects;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Json;
using RspsItemStudio.Core.Materials;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Core.Projects;

public static class ItemProjectLoader
{
    public static ItemProject Load(string rootDirectory)
    {
        return new ItemProject
        {
            RootDirectory = rootDirectory,
            Manifest = ReadJson<ItemStudioManifest>(rootDirectory, ItemProjectPaths.Manifest),
            Definition = ReadJson<ItemDefinitionDocument>(rootDirectory, ItemProjectPaths.Definition),
            Recolor = ReadJson<RecolorDocument>(rootDirectory, ItemProjectPaths.Recolor),
            Materials = ReadJson<MaterialsDocument>(rootDirectory, ItemProjectPaths.Materials),
            Animations = ReadJson<AnimationBindingsDocument>(rootDirectory, ItemProjectPaths.Animations),
            Effects = ReadJson<EffectsDocument>(rootDirectory, ItemProjectPaths.Effects),
            ExportPresets = ReadJson<ExportPresetsDocument>(rootDirectory, ItemProjectPaths.ExportPresets)
        };
    }

    private static T ReadJson<T>(string rootDirectory, string relativePath)
    {
        var json = File.ReadAllText(Path.Combine(rootDirectory, relativePath));
        return StudioJson.Deserialize<T>(json);
    }
}
