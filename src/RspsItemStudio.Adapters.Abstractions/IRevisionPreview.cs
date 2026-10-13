namespace RspsItemStudio.Adapters.Abstractions;

/// <summary>
/// Revision-accurate preview hints (palette, equip pose) when an adapter can supply them.
/// </summary>
public interface IRevisionPreview
{
    bool IsAvailable { get; }
}
