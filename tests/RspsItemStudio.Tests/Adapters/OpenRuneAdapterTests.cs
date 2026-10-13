using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Adapters.OpenRune;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Meshes;
using RspsItemStudio.Core.Projects;
using Xunit;

namespace RspsItemStudio.Tests.Adapters;

public class OpenRuneAdapterTests
{
    [Fact]
    public void Model_encode_returns_not_supported()
    {
        var adapter = new OpenRuneAdapter();
        var result = adapter.Models.Encode(new StudioMesh { Name = "inventory" });

        Assert.False(result.Success);
        Assert.True(result.IsNotSupported);
        Assert.Contains("OpenRune", result.Message);
        Assert.Contains("model", result.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void PackToLiveTree_always_fails()
    {
        var adapter = new OpenRuneAdapter();
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            var project = ItemProjectFactory.Create(root, "Export Test");
            var result = adapter.Cache.PackToLiveTree(new ExportStagingRequest
            {
                Project = project,
                Preset = new ExportPreset()
            });

            Assert.False(result.Success);
            Assert.False(result.IsNotSupported);
            Assert.Contains("Live cache", result.Message);
        }
        finally
        {
            if (Directory.Exists(root))
                Directory.Delete(root, true);
        }
    }

    [Fact]
    public void PackToStaging_rejects_escape_staging_paths()
    {
        var adapter = new OpenRuneAdapter();
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            var project = ItemProjectFactory.Create(root, "Staging Escape Test");
            var outside = Path.Combine(Path.GetTempPath(), "itemstudio-outside-" + Guid.NewGuid().ToString("N"));
            var result = adapter.Cache.PackToStaging(new ExportStagingRequest
            {
                Project = project,
                Preset = new ExportPreset { StagingDirectory = "../../../" + Path.GetFileName(outside) }
            });

            Assert.True(result.Success);
            Assert.Equal(StagingDirectoryResolver.DefaultRelative, result.Value!.StagingDirectory);
            Assert.True(Directory.Exists(Path.Combine(root, StagingDirectoryResolver.DefaultRelative)));
            Assert.False(Directory.Exists(outside));
        }
        finally
        {
            if (Directory.Exists(root))
                Directory.Delete(root, true);
        }
    }

    [Fact]
    public void PackToStaging_succeeds_with_skipped_report_entries()
    {
        var adapter = new OpenRuneAdapter();
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            var project = ItemProjectFactory.Create(root, "Staging Test");
            var preset = new ExportPreset { StagingDirectory = "export/staging-test" };
            var result = adapter.Cache.PackToStaging(new ExportStagingRequest
            {
                Project = project,
                Preset = preset
            });

            Assert.True(result.Success);
            Assert.NotNull(result.Value);
            Assert.NotEmpty(result.Value!.Entries);
            Assert.All(result.Value.Entries, e =>
                Assert.True(
                    e.Status is IntegrationEntryStatus.Skipped or IntegrationEntryStatus.NotPacked,
                    $"Unexpected status {e.Status} for {e.Category}"));
            var stagingPath = Path.Combine(root, preset.StagingDirectory);
            Assert.True(Directory.Exists(stagingPath));
        }
        finally
        {
            if (Directory.Exists(root))
                Directory.Delete(root, true);
        }
    }
}
