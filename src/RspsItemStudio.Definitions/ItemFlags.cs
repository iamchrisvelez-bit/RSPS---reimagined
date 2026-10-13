namespace RspsItemStudio.Definitions;

public sealed class ItemFlags
{
    public bool Tradeable { get; set; } = true;
    public bool Stackable { get; set; }
    public bool Noted { get; set; }
    public bool Members { get; set; }
    public bool Equipable { get; set; }
}
