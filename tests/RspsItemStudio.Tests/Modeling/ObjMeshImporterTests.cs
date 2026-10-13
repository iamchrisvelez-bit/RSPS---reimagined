using RspsItemStudio.Modeling;
using Xunit;

namespace RspsItemStudio.Tests.Modeling;

public class ObjMeshImporterTests
{
    [Fact]
    public void Import_cube_obj_produces_triangles()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "cube.obj");
        var result = ObjMeshImporter.Import(path);
        Assert.True(result.Mesh.Vertices.Count >= 8);
        Assert.True(result.Mesh.Triangles.Count >= 12);
    }
}
