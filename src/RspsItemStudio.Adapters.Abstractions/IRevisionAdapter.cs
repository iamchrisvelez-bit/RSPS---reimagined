namespace RspsItemStudio.Adapters.Abstractions;

public interface IRevisionAdapter
{
    string Id { get; }
    string DisplayName { get; }
    IReadOnlyCollection<AdapterCapability> Capabilities { get; }
    IModelCodec Models { get; }
    IAnimationCodec Animations { get; }
    IDefinitionCodec Definitions { get; }
    ICachePacker Cache { get; }
}
