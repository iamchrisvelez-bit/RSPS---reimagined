using System.IO;
using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Core.Json;
using RspsItemStudio.Core.Projects;

namespace RspsItemStudio.App.Services;

public static class IntegrationReportWriter
{
    public const string RelativePath = "export/last-integration-report.json";

    public static void Save(ItemProject project, IntegrationReport report)
    {
        var fullPath = Path.Combine(project.RootDirectory, RelativePath);
        var directory = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(directory))
            Directory.CreateDirectory(directory);
        File.WriteAllText(fullPath, StudioJson.Serialize(report));
    }
}
