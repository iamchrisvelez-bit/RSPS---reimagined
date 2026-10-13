namespace RspsItemStudio.Adapters.Abstractions;

/// <summary>
/// Resolves export staging paths confined under an item project root.
/// </summary>
public static class StagingDirectoryResolver
{
    public const string DefaultRelative = "export/staging";

    public static string ResolveRelative(string? stagingRelative)
    {
        if (string.IsNullOrWhiteSpace(stagingRelative))
            return DefaultRelative;

        var normalized = stagingRelative.Replace('\\', '/').Trim();
        if (Path.IsPathRooted(normalized))
            return DefaultRelative;

        var segments = normalized.Split('/', StringSplitOptions.RemoveEmptyEntries);
        if (segments.Length == 0 || segments.Any(s => s == ".."))
            return DefaultRelative;

        return string.Join(Path.DirectorySeparatorChar, segments);
    }

    public static string ResolveFullPath(string projectRoot, string? stagingRelative)
    {
        var relative = ResolveRelative(stagingRelative);
        var rootFull = Path.GetFullPath(projectRoot);
        var full = Path.GetFullPath(Path.Combine(rootFull, relative));

        if (!IsUnderRoot(full, rootFull))
        {
            relative = DefaultRelative;
            full = Path.GetFullPath(Path.Combine(rootFull, relative));
        }

        return full;
    }

    private static bool IsUnderRoot(string fullPath, string rootFull)
    {
        var root = rootFull.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        if (string.Equals(fullPath, root, StringComparison.OrdinalIgnoreCase))
            return true;

        var prefix = root + Path.DirectorySeparatorChar;
        return fullPath.StartsWith(prefix, StringComparison.OrdinalIgnoreCase);
    }
}
