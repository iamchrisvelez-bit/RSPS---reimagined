namespace RspsItemStudio.Definitions;

public sealed class ItemDefinitionDocument
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = "New Item";
    public string Examine { get; set; } = "It's an item.";
    public EquipmentSlot Slot { get; set; } = EquipmentSlot.None;
    public CombatBonuses Bonuses { get; set; } = new();
    public LevelRequirements Requirements { get; set; } = new();
    public double WeightKg { get; set; }
    public ItemFlags Flags { get; set; } = new();
    public Dictionary<string, string> Extensions { get; set; } = new();
}
