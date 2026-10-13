using RspsItemStudio.Core.Projects;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class ItemProjectLoaderTests
{
    [Fact]
    public void Load_roundTrips_factory_project()
    {
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            ItemProjectFactory.Create(root, "Round Trip");
            var loaded = ItemProjectLoader.Load(root);
            Assert.Equal("Round Trip", loaded.Definition.Name);
            Assert.Contains("openrune", loaded.Manifest.EnabledAdapters);
        }
        finally
        {
            if (Directory.Exists(root)) Directory.Delete(root, true);
        }
    }
}
