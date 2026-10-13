using RspsItemStudio.Core.Meshes;

namespace RspsItemStudio.Modeling;

public sealed class MeshImportResult
{
    public required StudioMesh Mesh { get; init; }
    public IReadOnlyList<string> Warnings { get; init; } = Array.Empty<string>();
}
