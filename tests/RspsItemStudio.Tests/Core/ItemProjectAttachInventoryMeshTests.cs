using RspsItemStudio.Core.Json;
using RspsItemStudio.Core.Meshes;
using RspsItemStudio.Core.Projects;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class ItemProjectAttachInventoryMeshTests
{
    [Fact]
    public void AttachInventoryMesh_writes_json_and_copies_source()
    {
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        var sourceObj = Path.Combine(Path.GetTempPath(), "mesh-" + Guid.NewGuid().ToString("N") + ".obj");
        File.WriteAllText(sourceObj, "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n");

        try
        {
            var project = ItemProjectFactory.Create(root, "Mesh Item");
            var mesh = new StudioMesh
            {
                Name = "test",
                Vertices =
                {
                    new StudioVertex { X = 0, Y = 0, Z = 0 },
                    new StudioVertex { X = 1, Y = 0, Z = 0 },
                    new StudioVertex { X = 0, Y = 1, Z = 0 }
                },
                Triangles = { new StudioTriangle { A = 0, B = 1, C = 2 } }
            };

            project.AttachInventoryMesh(mesh, sourceObj);

            var meshPath = Path.Combine(root, ItemProjectPaths.InventoryMesh);
            Assert.True(File.Exists(meshPath));
            var loaded = StudioJson.Deserialize<StudioMesh>(File.ReadAllText(meshPath));
            Assert.NotNull(loaded);
            Assert.Equal(3, loaded!.Vertices.Count);

            var copied = Path.Combine(root, ItemProjectPaths.SourceDir, Path.GetFileName(sourceObj));
            Assert.True(File.Exists(copied));
            Assert.Equal(File.ReadAllText(sourceObj), File.ReadAllText(copied));
        }
        finally
        {
            if (Directory.Exists(root))
                Directory.Delete(root, true);
            if (File.Exists(sourceObj))
                File.Delete(sourceObj);
        }
    }
}
