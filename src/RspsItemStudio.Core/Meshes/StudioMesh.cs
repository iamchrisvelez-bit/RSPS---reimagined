namespace RspsItemStudio.Core.Meshes;

public sealed class StudioMesh
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = "mesh";
    public List<StudioVertex> Vertices { get; set; } = new();
    public List<StudioTriangle> Triangles { get; set; } = new();
}
