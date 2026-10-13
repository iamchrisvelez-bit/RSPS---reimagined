using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Adapters.OpenRune.Osrs;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneCachePacker : ICachePacker
{
    private const string AdapterId = "openrune";
    private const string LiveWriteDisabledMessage =
        "Live cache/server writes are disabled until formats are verified and backup flow ships.";

    private readonly OpenRuneDefinitionCodec _definitions = new();

    public AdapterResult<IntegrationReport> PackToStaging(ExportStagingRequest request)
    {
        var stagingRelative = StagingDirectoryResolver.ResolveRelative(request.Preset.StagingDirectory);
        var stagingPath = StagingDirectoryResolver.ResolveFullPath(
            request.Project.RootDirectory,
            request.Preset.StagingDirectory);
        Directory.CreateDirectory(stagingPath);

        var report = new IntegrationReport
        {
            AdapterId = AdapterId,
            StagingDirectory = stagingRelative,
            Entries = []
        };

        if (request.Preset.StagingDirectory != stagingRelative &&
            !string.Equals(request.Preset.StagingDirectory?.Trim(), stagingRelative, StringComparison.OrdinalIgnoreCase))
        {
            report.Entries.Add(new IntegrationReportEntry
            {
                Category = "staging",
                Status = IntegrationEntryStatus.Skipped,
                Message =
                    $"Configured staging path was unsafe or outside the project; used '{stagingRelative}' instead."
            });
        }

        if (request.Preset.ItemId is not int itemId)
        {
            report.Summary = "Staging created, but no item ID is set on the export preset — definition files were not written.";
            report.Entries.Add(new IntegrationReportEntry
            {
                Category = "definition",
                Status = IntegrationEntryStatus.Skipped,
                Message = "Set ExportPreset.ItemId before staging OpenRune item definitions."
            });
            report.Entries.Add(ModelSkipped());
            report.Entries.Add(AnimationSkipped());
            report.Entries.Add(new IntegrationReportEntry
            {
                Category = "cache",
                Status = IntegrationEntryStatus.NotPacked,
                Message = "No JS5/cache archives were packed. Copy TOML into OpenRune itemDirectory and run Pack Items."
            });
            return AdapterResult<IntegrationReport>.Ok(report);
        }

        var definition = request.Project.Definition;
        var encode = _definitions.Encode(definition);
        if (!encode.Success || encode.Value is null)
        {
            return AdapterResult<IntegrationReport>.Fail(
                encode.Message ?? "Definition encode failed.");
        }

        var extras = OsrsItemDefinitionExtras.FromExtensions(definition.Extensions);
        var toml = OpenRuneItemTomlExporter.Export(itemId, definition, extras);
        var itemsDir = Path.Combine(stagingPath, "openrune-items");
        Directory.CreateDirectory(itemsDir);

        var tomlPath = Path.Combine(itemsDir, itemId + ".toml");
        var binPath = Path.Combine(itemsDir, itemId + ".obj.bin");
        File.WriteAllText(tomlPath, toml);
        File.WriteAllBytes(binPath, encode.Value);

        report.Entries.Add(new IntegrationReportEntry
        {
            Category = "definition",
            Status = IntegrationEntryStatus.Written,
            Path = Path.Combine(stagingRelative, "openrune-items", itemId + ".toml"),
            Message =
                "OpenRune Pack Items TOML written. Copy into your OpenRune itemDirectory and run packConfig(PackMode.ITEMS, …)."
        });
        report.Entries.Add(new IntegrationReportEntry
        {
            Category = "definition",
            Status = IntegrationEntryStatus.Written,
            Path = Path.Combine(stagingRelative, "openrune-items", itemId + ".obj.bin"),
            Message =
                "Partial OSRS opcode stream (OpenRune ItemCodec subset). Not a full JS5 archive — for inspection/fixtures only."
        });
        report.Entries.Add(ModelSkipped());
        report.Entries.Add(AnimationSkipped());
        report.Entries.Add(new IntegrationReportEntry
        {
            Category = "cache",
            Status = IntegrationEntryStatus.NotPacked,
            Message =
                "No live cache/JS5 write. Use OpenRune FileStore Pack Items on the staged TOML, or integrate the binary via your verified packing toolchain."
        });

        report.Summary =
            $"Staged OpenRune item {itemId} as TOML + partial obj.bin under '{stagingRelative}/openrune-items'. Models/animations/cache archives not packed.";

        return AdapterResult<IntegrationReport>.Ok(report);
    }

    public AdapterResult<IntegrationReport> PackToLiveTree(ExportStagingRequest request) =>
        AdapterResult<IntegrationReport>.Fail(LiveWriteDisabledMessage);

    private static IntegrationReportEntry ModelSkipped() =>
        new()
        {
            Category = "model",
            Status = IntegrationEntryStatus.Skipped,
            Message = "Inventory/equip model cache packing is not verified yet (Milestone 2 model codec pending)."
        };

    private static IntegrationReportEntry AnimationSkipped() =>
        new()
        {
            Category = "animation",
            Status = IntegrationEntryStatus.Skipped,
            Message = "Animation bindings were not packed (codec not verified)."
        };
}
