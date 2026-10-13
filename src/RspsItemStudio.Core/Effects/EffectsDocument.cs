namespace RspsItemStudio.Core.Effects;

public sealed class EffectsDocument
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public List<string> Attachments { get; set; } = new();
}
