using RspsItemStudio.Adapters.Abstractions;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneAdapter : IRevisionAdapter
{
    public string Id => "openrune";
    public string DisplayName => "OpenRune";
    public IReadOnlyCollection<AdapterCapability> Capabilities { get; } = Array.Empty<AdapterCapability>();
    public IModelCodec Models { get; } = new OpenRuneModelCodec();
    public IAnimationCodec Animations { get; } = new OpenRuneAnimationCodec();
    public IDefinitionCodec Definitions { get; } = new OpenRuneDefinitionCodec();
    public ICachePacker Cache { get; } = new OpenRuneCachePacker();
}
