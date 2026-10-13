using System.Globalization;
using RspsItemStudio.Core.Meshes;

namespace RspsItemStudio.Modeling;

public static class ObjMeshImporter
{
    public static MeshImportResult Import(string objPath)
    {
        var positions = new List<(float X, float Y, float Z)>();
        var texCoords = new List<(float U, float V)>();
        var warnings = new List<string>();
        var mesh = new StudioMesh
        {
            Name = Path.GetFileNameWithoutExtension(objPath)
        };

        var vertexCache = new Dictionary<(int V, int Vt), int>();

        foreach (var rawLine in File.ReadLines(objPath))
        {
            var line = rawLine.Trim();
            if (line.Length == 0 || line.StartsWith('#'))
                continue;

            var parts = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 0)
                continue;

            switch (parts[0])
            {
                case "o":
                case "g":
                    if (parts.Length > 1)
                        mesh.Name = parts[1];
                    break;
                case "v":
                    if (parts.Length >= 4)
                    {
                        positions.Add((
                            ParseFloat(parts[1]),
                            ParseFloat(parts[2]),
                            ParseFloat(parts[3])));
                    }
                    break;
                case "vt":
                    if (parts.Length >= 3)
                    {
                        texCoords.Add((
                            ParseFloat(parts[1]),
                            ParseFloat(parts[2])));
                    }
                    break;
                case "f":
                    if (parts.Length < 4)
                        break;

                    var cornerIndices = new List<int>();
                    for (var i = 1; i < parts.Length; i++)
                        cornerIndices.Add(ResolveCorner(parts[i], positions, texCoords, mesh, vertexCache, warnings));

                    for (var t = 1; t < cornerIndices.Count - 1; t++)
                    {
                        mesh.Triangles.Add(new StudioTriangle
                        {
                            A = cornerIndices[0],
                            B = cornerIndices[t],
                            C = cornerIndices[t + 1]
                        });
                    }
                    break;
            }
        }

        return new MeshImportResult
        {
            Mesh = mesh,
            Warnings = warnings
        };
    }

    private static int ResolveCorner(
        string token,
        List<(float X, float Y, float Z)> positions,
        List<(float U, float V)> texCoords,
        StudioMesh mesh,
        Dictionary<(int V, int Vt), int> vertexCache,
        List<string> warnings)
    {
        var segments = token.Split('/');
        var vIndex = ParseIndex(segments[0], positions.Count);
        var vtIndex = 0;
        var hasVt = false;

        if (segments.Length > 1 && segments[1].Length > 0)
        {
            vtIndex = ParseIndex(segments[1], texCoords.Count);
            hasVt = true;
        }

        if (!hasVt && !warnings.Contains("Face corner missing UV coordinates; using (0,0)."))
            warnings.Add("Face corner missing UV coordinates; using (0,0).");

        var key = (vIndex, hasVt ? vtIndex : 0);
        if (vertexCache.TryGetValue(key, out var existing))
            return existing;

        var pos = positions[vIndex - 1];
        float u = 0, v = 0;
        if (hasVt && vtIndex > 0 && vtIndex <= texCoords.Count)
        {
            var tc = texCoords[vtIndex - 1];
            u = tc.U;
            v = tc.V;
        }

        var index = mesh.Vertices.Count;
        mesh.Vertices.Add(new StudioVertex
        {
            X = pos.X,
            Y = pos.Y,
            Z = pos.Z,
            U = u,
            V = v
        });
        vertexCache[key] = index;
        return index;
    }

    private static int ParseIndex(string text, int count)
    {
        var index = int.Parse(text, CultureInfo.InvariantCulture);
        if (index < 0)
            index = count + index + 1;
        return index;
    }

    private static float ParseFloat(string text) =>
        float.Parse(text, CultureInfo.InvariantCulture);
}
