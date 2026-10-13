using RspsItemStudio.Adapters.Abstractions;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneCachePacker : ICachePacker
{
    private const string AdapterId = "openrune";
    private const string LiveWriteDisabledMessage =
        "Live cache/server writes are disabled until formats are verified and backup flow ships.";

    public AdapterResult<IntegrationReport> PackToStaging(ExportStagingRequest request)
    {
        var stagingRelative = request.Preset.StagingDirectory;
        if (string.IsNullOrWhiteSpace(stagingRelative))
            stagingRelative = "export/staging";

        var stagingPath = Path.Combine(request.Project.RootDirectory, stagingRelative);
        Directory.CreateDirectory(stagingPath);

        var report = new IntegrationReport
        {
            AdapterId = AdapterId,
            StagingDirectory = stagingRelative,
            Summary =
                "Staging folder created. No cache bytes were written — all export steps were skipped until OpenRune formats are verified.",
            Entries =
            [
                new IntegrationReportEntry
                {
                    Category = "definition",
                    Status = IntegrationEntryStatus.Skipped,
                    Message = "Item definition was not packed (codec not verified)."
                },
                new IntegrationReportEntry
                {
                    Category = "model",
                    Status = IntegrationEntryStatus.Skipped,
                    Message = "Inventory/equip models were not packed (codec not verified)."
                },
                new IntegrationReportEntry
                {
                    Category = "animation",
                    Status = IntegrationEntryStatus.Skipped,
                    Message = "Animation bindings were not packed (codec not verified)."
                },
                new IntegrationReportEntry
                {
                    Category = "cache",
                    Status = IntegrationEntryStatus.NotPacked,
                    Message = "No OpenRune cache archives were produced in staging."
                }
            ]
        };

        return AdapterResult<IntegrationReport>.Ok(report);
    }

    public AdapterResult<IntegrationReport> PackToLiveTree(ExportStagingRequest request) =>
        AdapterResult<IntegrationReport>.Fail(LiveWriteDisabledMessage);
}
