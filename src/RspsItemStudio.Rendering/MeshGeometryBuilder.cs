using System.Numerics;
using RspsItemStudio.Core.Meshes;

namespace RspsItemStudio.Rendering;

internal static class MeshGeometryBuilder
{
    public readonly record struct Vertex(float X, float Y, float Z, float Nx, float Ny, float Nz, float U, float V);

    public static (Vertex[] Vertices, uint[] Indices, Vector3 Min, Vector3 Max) Build(StudioMesh mesh)
    {
        if (mesh.Vertices.Count == 0 || mesh.Triangles.Count == 0)
            return (Array.Empty<Vertex>(), Array.Empty<uint>(), Vector3.Zero, Vector3.Zero);

        var normals = new Vector3[mesh.Vertices.Count];
        foreach (var tri in mesh.Triangles)
        {
            var a = ToVector3(mesh.Vertices[tri.A]);
            var b = ToVector3(mesh.Vertices[tri.B]);
            var c = ToVector3(mesh.Vertices[tri.C]);
            var faceNormal = Vector3.Normalize(Vector3.Cross(b - a, c - a));
            if (float.IsNaN(faceNormal.X))
                continue;

            normals[tri.A] += faceNormal;
            normals[tri.B] += faceNormal;
            normals[tri.C] += faceNormal;
        }

        var vertices = new Vertex[mesh.Vertices.Count];
        var min = new Vector3(float.MaxValue);
        var max = new Vector3(float.MinValue);

        for (var i = 0; i < mesh.Vertices.Count; i++)
        {
            var v = mesh.Vertices[i];
            var pos = new Vector3(v.X, v.Y, v.Z);
            min = Vector3.Min(min, pos);
            max = Vector3.Max(max, pos);

            var n = normals[i];
            if (n.LengthSquared() < 1e-8f)
                n = Vector3.UnitY;
            else
                n = Vector3.Normalize(n);

            vertices[i] = new Vertex(v.X, v.Y, v.Z, n.X, n.Y, n.Z, v.U, v.V);
        }

        var indices = new uint[mesh.Triangles.Count * 3];
        var index = 0;
        foreach (var tri in mesh.Triangles)
        {
            indices[index++] = (uint)tri.A;
            indices[index++] = (uint)tri.B;
            indices[index++] = (uint)tri.C;
        }

        return (vertices, indices, min, max);
    }

    public static (Vertex[] Vertices, uint[] Indices) BuildGrid(int halfExtent = 10, float step = 1f)
    {
        var lines = new List<Vertex>();
        var indices = new List<uint>();
        uint next = 0;

        for (var i = -halfExtent; i <= halfExtent; i++)
        {
            var x = i * step;
            var z0 = -halfExtent * step;
            var z1 = halfExtent * step;
            lines.Add(new Vertex(x, 0, z0, 0, 1, 0, 0, 0));
            lines.Add(new Vertex(x, 0, z1, 0, 1, 0, 0, 0));
            indices.Add(next++);
            indices.Add(next++);

            var z = i * step;
            var x0 = -halfExtent * step;
            var x1 = halfExtent * step;
            lines.Add(new Vertex(x0, 0, z, 0, 1, 0, 0, 0));
            lines.Add(new Vertex(x1, 0, z, 0, 1, 0, 0, 0));
            indices.Add(next++);
            indices.Add(next++);
        }

        return (lines.ToArray(), indices.ToArray());
    }

    private static Vector3 ToVector3(StudioVertex v) => new(v.X, v.Y, v.Z);
}
