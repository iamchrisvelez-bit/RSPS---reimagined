using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.OpenRune.Osrs;

/// <summary>
/// Partial OSRS item-definition opcode stream matching OpenRune <c>ItemCodec</c>
/// for the fields Item Studio maps in Milestone 2. Does not claim full opcode coverage.
/// </summary>
public static class OsrsItemDefinitionBinary
{
    public const int OpcodeInventoryModel = 1;
    public const int OpcodeName = 2;
    public const int OpcodeExamine = 3;
    public const int OpcodeStackable = 11;
    public const int OpcodeCost = 12;
    public const int OpcodeEquipSlot = 13;
    public const int OpcodeNotTradeable = 15;
    public const int OpcodeMembers = 16;
    public const int OpcodeMaleModel0 = 23;
    public const int OpcodeFemaleModel0 = 25;
    public const int OpcodeWeight = 75;
    public const int OpcodeEnd = 0;

    public static byte[] Encode(ItemDefinitionDocument definition, OsrsItemDefinitionExtras extras)
    {
        using var stream = new MemoryStream();
        using var writer = new BinaryWriter(stream);

        if (extras.InventoryModelId is > 0)
        {
            writer.Write((byte)OpcodeInventoryModel);
            writer.Write((ushort)extras.InventoryModelId.Value);
        }

        if (!string.IsNullOrWhiteSpace(definition.Name) &&
            !definition.Name.Equals("null", StringComparison.OrdinalIgnoreCase))
        {
            writer.Write((byte)OpcodeName);
            JagexStrings.Write(writer, definition.Name);
        }

        if (!string.IsNullOrWhiteSpace(definition.Examine) &&
            !definition.Examine.Equals("null", StringComparison.OrdinalIgnoreCase))
        {
            writer.Write((byte)OpcodeExamine);
            JagexStrings.Write(writer, definition.Examine);
        }

        if (definition.Flags.Stackable)
            writer.Write((byte)OpcodeStackable);

        if (extras.Cost is int cost && cost != 1)
        {
            writer.Write((byte)OpcodeCost);
            writer.Write(cost);
        }

        var wearPos = OsrsEquipSlotMap.ToWearPos(definition.Slot);
        if (wearPos is int slot)
        {
            writer.Write((byte)OpcodeEquipSlot);
            writer.Write((byte)slot);
        }

        if (!definition.Flags.Tradeable)
            writer.Write((byte)OpcodeNotTradeable);

        if (definition.Flags.Members)
            writer.Write((byte)OpcodeMembers);

        if (extras.MaleModel0 is > 0)
        {
            writer.Write((byte)OpcodeMaleModel0);
            writer.Write((ushort)extras.MaleModel0.Value);
            writer.Write((byte)extras.MaleOffset);
        }

        if (extras.FemaleModel0 is > 0)
        {
            writer.Write((byte)OpcodeFemaleModel0);
            writer.Write((ushort)extras.FemaleModel0.Value);
            writer.Write((byte)extras.FemaleOffset);
        }

        // OpenRune writes weight as ushort via opcode 75 (game units, not kg).
        var weightUnits = extras.WeightUnits ?? (int)Math.Round(definition.WeightKg * 1000.0);
        if (weightUnits != 0)
        {
            writer.Write((byte)OpcodeWeight);
            writer.Write((ushort)Math.Clamp(weightUnits, 0, ushort.MaxValue));
        }

        writer.Write((byte)OpcodeEnd);
        return stream.ToArray();
    }

    public static (ItemDefinitionDocument Definition, OsrsItemDefinitionExtras Extras) Decode(byte[] data)
    {
        var definition = new ItemDefinitionDocument
        {
            Name = "null",
            Examine = "null",
            Flags = new ItemFlags { Tradeable = true }
        };
        var extras = new OsrsItemDefinitionExtras();

        using var stream = new MemoryStream(data);
        using var reader = new BinaryReader(stream);

        while (stream.Position < stream.Length)
        {
            var opcode = reader.ReadByte();
            if (opcode == OpcodeEnd)
                break;

            switch (opcode)
            {
                case OpcodeInventoryModel:
                    extras.InventoryModelId = reader.ReadUInt16();
                    break;
                case OpcodeName:
                    definition.Name = JagexStrings.Read(reader);
                    break;
                case OpcodeExamine:
                    definition.Examine = JagexStrings.Read(reader);
                    break;
                case OpcodeStackable:
                    definition.Flags.Stackable = true;
                    break;
                case OpcodeCost:
                    extras.Cost = reader.ReadInt32();
                    break;
                case OpcodeEquipSlot:
                    definition.Slot = OsrsEquipSlotMap.FromWearPos(reader.ReadByte());
                    definition.Flags.Equipable = definition.Slot != EquipmentSlot.None;
                    break;
                case OpcodeNotTradeable:
                    definition.Flags.Tradeable = false;
                    break;
                case OpcodeMembers:
                    definition.Flags.Members = true;
                    break;
                case OpcodeMaleModel0:
                    extras.MaleModel0 = reader.ReadUInt16();
                    extras.MaleOffset = reader.ReadByte();
                    break;
                case OpcodeFemaleModel0:
                    extras.FemaleModel0 = reader.ReadUInt16();
                    extras.FemaleOffset = reader.ReadByte();
                    break;
                case OpcodeWeight:
                    extras.WeightUnits = reader.ReadUInt16();
                    definition.WeightKg = extras.WeightUnits.Value / 1000.0;
                    break;
                default:
                    throw new InvalidOperationException(
                        $"Unsupported OSRS item opcode {opcode} in Milestone 2 partial codec.");
            }
        }

        return (definition, extras);
    }
}

public sealed class OsrsItemDefinitionExtras
{
    public int? InventoryModelId { get; set; }
    public int? Cost { get; set; }
    public int? MaleModel0 { get; set; }
    public int MaleOffset { get; set; }
    public int? FemaleModel0 { get; set; }
    public int FemaleOffset { get; set; }
    public int? WeightUnits { get; set; }

    public static OsrsItemDefinitionExtras FromExtensions(IReadOnlyDictionary<string, string> extensions)
    {
        var extras = new OsrsItemDefinitionExtras();
        if (TryInt(extensions, "inventoryModel", out var inv))
            extras.InventoryModelId = inv;
        if (TryInt(extensions, "cost", out var cost))
            extras.Cost = cost;
        if (TryInt(extensions, "maleModel0", out var male))
            extras.MaleModel0 = male;
        if (TryInt(extensions, "maleOffset", out var maleOff))
            extras.MaleOffset = maleOff;
        if (TryInt(extensions, "femaleModel0", out var female))
            extras.FemaleModel0 = female;
        if (TryInt(extensions, "femaleOffset", out var femaleOff))
            extras.FemaleOffset = femaleOff;
        if (TryInt(extensions, "weightUnits", out var weight))
            extras.WeightUnits = weight;
        return extras;
    }

    private static bool TryInt(IReadOnlyDictionary<string, string> extensions, string key, out int value)
    {
        value = 0;
        return extensions.TryGetValue(key, out var raw) && int.TryParse(raw, out value);
    }
}
