namespace RspsItemStudio.Core.Projects;

public sealed class ItemStudioManifest
{
    public int SchemaVersion { get; set; } = 1;
    public Guid ProjectId { get; set; } = Guid.NewGuid();
    public string DisplayName { get; set; } = "New Item";
    public List<string> EnabledAdapters { get; set; } = new() { "openrune" };
}
