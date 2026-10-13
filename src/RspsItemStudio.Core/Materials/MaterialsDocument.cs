namespace RspsItemStudio.Core.Materials;

public sealed class MaterialsDocument
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Dictionary<string, string> Slots { get; set; } = new();
}
