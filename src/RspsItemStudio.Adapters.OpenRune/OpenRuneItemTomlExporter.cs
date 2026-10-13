using System.Globalization;
using System.Text;
using RspsItemStudio.Adapters.OpenRune.Osrs;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.OpenRune;

/// <summary>
/// Writes OpenRune FileStore Pack Items TOML (wiki Pack-Items schema).
/// Place the file under an OpenRune <c>itemDirectory</c> and run <c>packConfig(PackMode.ITEMS, ...)</c>.
/// </summary>
public static class OpenRuneItemTomlExporter
{
    public static string Export(int itemId, ItemDefinitionDocument definition, OsrsItemDefinitionExtras extras)
    {
        var sb = new StringBuilder();
        sb.Append("id= ").Append(itemId).AppendLine();
        sb.Append("name = ").Append(Quote(definition.Name)).AppendLine();
        sb.Append("description = ").Append(Quote(definition.Examine)).AppendLine();
        sb.Append("members = ").Append(definition.Flags.Members ? "true" : "false").AppendLine();
        sb.Append("isTradeable = ").Append(definition.Flags.Tradeable ? "true" : "false").AppendLine();
        sb.Append("stacks = ").Append(definition.Flags.Stackable ? "1" : "0").AppendLine();

        var weight = extras.WeightUnits ?? (int)Math.Round(definition.WeightKg * 1000.0);
        sb.Append("weight = ")
            .Append(weight.ToString(CultureInfo.InvariantCulture))
            .AppendLine();

        if (extras.Cost is int cost)
            sb.Append("cost = ").Append(cost).AppendLine();

        if (extras.InventoryModelId is int inv)
            sb.Append("inventoryModel = ").Append(inv).AppendLine();

        if (OsrsEquipSlotMap.ToWearPos(definition.Slot) is int wear)
            sb.Append("wearPos1 = ").Append(wear).AppendLine();

        if (extras.MaleModel0 is int male)
            sb.Append("maleModel0 = ").Append(male).AppendLine();

        if (extras.FemaleModel0 is int female)
            sb.Append("femaleModel0 = ").Append(female).AppendLine();

        return sb.ToString();
    }

    private static string Quote(string value)
    {
        var escaped = value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        return "\"" + escaped + "\"";
    }
}
