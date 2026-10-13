using RspsItemStudio.Core.Projects;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class ItemProjectFactoryTests
{
    [Fact]
    public void Create_writes_required_documents()
    {
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            var project = ItemProjectFactory.Create(root, "Test Scimitar");
            Assert.True(File.Exists(Path.Combine(root, "itemstudio.json")));
            Assert.True(File.Exists(Path.Combine(root, "meta", "item.json")));
            Assert.True(File.Exists(Path.Combine(root, "colors", "recolor.json")));
            Assert.True(File.Exists(Path.Combine(root, "materials", "materials.json")));
            Assert.True(File.Exists(Path.Combine(root, "animations", "bindings.json")));
            Assert.True(File.Exists(Path.Combine(root, "effects", "effects.json")));
            Assert.True(File.Exists(Path.Combine(root, "export", "presets.json")));
            Assert.Equal("Test Scimitar", project.Definition.Name);
            Assert.Equal(1, project.Manifest.SchemaVersion);
        }
        finally
        {
            if (Directory.Exists(root)) Directory.Delete(root, true);
        }
    }
}
