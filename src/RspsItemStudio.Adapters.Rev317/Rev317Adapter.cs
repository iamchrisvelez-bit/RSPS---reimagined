using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Core.Animations;
using RspsItemStudio.Core.Meshes;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.Rev317;

public sealed class Rev317Adapter : IRevisionAdapter
{
    public string Id => "rev317";
    public string DisplayName => "Revision 317";
    public IReadOnlyCollection<AdapterCapability> Capabilities { get; } = Array.Empty<AdapterCapability>();
    public IModelCodec Models { get; } = new Rev317ModelCodec();
    public IAnimationCodec Animations { get; } = new Rev317AnimationCodec();
    public IDefinitionCodec Definitions { get; } = new Rev317DefinitionCodec();
    public ICachePacker Cache { get; } = new Rev317CachePacker();

    private sealed class Rev317ModelCodec : IModelCodec
    {
        private const string Message = "Rev317 model codec not verified for this revision yet.";

        public AdapterResult<byte[]> Encode(StudioMesh mesh) =>
            AdapterResult<byte[]>.NotSupported(Message);

        public AdapterResult<StudioMesh> Decode(byte[] data) =>
            AdapterResult<StudioMesh>.NotSupported(Message);
    }

    private sealed class Rev317DefinitionCodec : IDefinitionCodec
    {
        private const string Message = "Rev317 definition codec not verified for this revision yet.";

        public AdapterResult<byte[]> Encode(ItemDefinitionDocument definition) =>
            AdapterResult<byte[]>.NotSupported(Message);

        public AdapterResult<ItemDefinitionDocument> Decode(byte[] data) =>
            AdapterResult<ItemDefinitionDocument>.NotSupported(Message);
    }

    private sealed class Rev317AnimationCodec : IAnimationCodec
    {
        private const string Message = "Rev317 animation codec not verified for this revision yet.";

        public AdapterResult<byte[]> EncodeBindings(AnimationBindingsDocument bindings) =>
            AdapterResult<byte[]>.NotSupported(Message);
    }

    private sealed class Rev317CachePacker : ICachePacker
    {
        private const string AdapterId = "rev317";
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
                    "Staging folder created. No cache bytes were written — all export steps were skipped until Rev317 formats are verified.",
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
                        Message = "No Rev317 cache archives were produced in staging."
                    }
                ]
            };

            return AdapterResult<IntegrationReport>.Ok(report);
        }

        public AdapterResult<IntegrationReport> PackToLiveTree(ExportStagingRequest request) =>
            AdapterResult<IntegrationReport>.Fail(LiveWriteDisabledMessage);
    }
}
