using RspsItemStudio.Core.Animations;
using RspsItemStudio.Core.Colors;
using RspsItemStudio.Core.Effects;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Materials;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Core.Projects;

public static class ItemProjectFactory
{
    public static ItemProject Create(string rootDirectory, string displayName)
    {
        Directory.CreateDirectory(rootDirectory);
        EnsureDocumentDirectory(rootDirectory, ItemProjectPaths.Definition);
        Directory.CreateDirectory(Path.Combine(rootDirectory, ItemProjectPaths.SourceDir));
        Directory.CreateDirectory(Path.Combine(rootDirectory, ItemProjectPaths.TexturesDir));
        EnsureDocumentDirectory(rootDirectory, ItemProjectPaths.Recolor);
        EnsureDocumentDirectory(rootDirectory, ItemProjectPaths.Animations);
        var animationsDir = Path.GetDirectoryName(Path.Combine(rootDirectory, ItemProjectPaths.Animations))!;
        Directory.CreateDirectory(Path.Combine(animationsDir, "clips"));
        EnsureDocumentDirectory(rootDirectory, ItemProjectPaths.Effects);
        EnsureDocumentDirectory(rootDirectory, ItemProjectPaths.ExportPresets);
        EnsureDocumentDirectory(rootDirectory, ItemProjectPaths.ValidationReport);

        var project = new ItemProject
        {
            RootDirectory = rootDirectory,
            Manifest = new ItemStudioManifest { DisplayName = displayName },
            Definition = new ItemDefinitionDocument { Name = displayName },
            Recolor = new RecolorDocument(),
            Materials = new MaterialsDocument(),
            Animations = new AnimationBindingsDocument(),
            Effects = new EffectsDocument(),
            ExportPresets = new ExportPresetsDocument()
        };

        project.Save();
        return project;
    }

    private static void EnsureDocumentDirectory(string rootDirectory, string relativeDocumentPath)
    {
        var directory = Path.GetDirectoryName(Path.Combine(rootDirectory, relativeDocumentPath));
        if (!string.IsNullOrEmpty(directory))
            Directory.CreateDirectory(directory);
    }
}
