using RspsItemStudio.Adapters.Abstractions;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneAdapter : IRevisionAdapter
{
    public string Id => "openrune";
    public string DisplayName => "OpenRune";
    public IReadOnlyCollection<AdapterCapability> Capabilities { get; } =
    [
        new AdapterCapability(
            "definition.partial",
            "Partial OSRS item-definition opcode encode/decode + OpenRune Pack Items TOML staging."),
        new AdapterCapability(
            "staging.toml",
            "Writes OpenRune itemDirectory TOML under staging/openrune-items for PackConfig ITEMS.")
    ];
    public IModelCodec Models { get; } = new OpenRuneModelCodec();
    public IAnimationCodec Animations { get; } = new OpenRuneAnimationCodec();
    public IDefinitionCodec Definitions { get; } = new OpenRuneDefinitionCodec();
    public ICachePacker Cache { get; } = new OpenRuneCachePacker();
}
