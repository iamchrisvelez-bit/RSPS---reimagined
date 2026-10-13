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
        Directory.CreateDirectory(Path.Combine(rootDirectory, "meta"));
        Directory.CreateDirectory(Path.Combine(rootDirectory, ItemProjectPaths.SourceDir));
        Directory.CreateDirectory(Path.Combine(rootDirectory, ItemProjectPaths.TexturesDir));
        Directory.CreateDirectory(Path.Combine(rootDirectory, "colors"));
        Directory.CreateDirectory(Path.Combine(rootDirectory, "animations", "clips"));
        Directory.CreateDirectory(Path.Combine(rootDirectory, "effects"));
        Directory.CreateDirectory(Path.Combine(rootDirectory, "export"));
        Directory.CreateDirectory(Path.Combine(rootDirectory, "validation"));

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
}
