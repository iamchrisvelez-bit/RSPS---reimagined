using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Projects;

namespace RspsItemStudio.Adapters.Abstractions;

public sealed class ExportStagingRequest
{
    public required ItemProject Project { get; init; }
    public required ExportPreset Preset { get; init; }
}
