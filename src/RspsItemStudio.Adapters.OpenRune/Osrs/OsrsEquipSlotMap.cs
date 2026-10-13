using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.OpenRune.Osrs;

/// <summary>
/// Maps studio <see cref="EquipmentSlot"/> to OSRS wear-position bytes used by OpenRune opcode 13.
/// Values follow common OSRS client wearPos conventions; confirm against your pinned revision.
/// </summary>
internal static class OsrsEquipSlotMap
{
    public static int? ToWearPos(EquipmentSlot slot) =>
        slot switch
        {
            EquipmentSlot.None => null,
            EquipmentSlot.Helmet => 0,
            EquipmentSlot.Cape => 1,
            EquipmentSlot.Amulet => 2,
            EquipmentSlot.Weapon => 3,
            EquipmentSlot.Body => 4,
            EquipmentSlot.Shield => 5,
            EquipmentSlot.Legs => 7,
            EquipmentSlot.Hands => 9,
            EquipmentSlot.Feet => 10,
            EquipmentSlot.Ring => 12,
            EquipmentSlot.Ammo => 13,
            _ => null
        };

    public static EquipmentSlot FromWearPos(int wearPos) =>
        wearPos switch
        {
            0 => EquipmentSlot.Helmet,
            1 => EquipmentSlot.Cape,
            2 => EquipmentSlot.Amulet,
            3 => EquipmentSlot.Weapon,
            4 => EquipmentSlot.Body,
            5 => EquipmentSlot.Shield,
            7 => EquipmentSlot.Legs,
            9 => EquipmentSlot.Hands,
            10 => EquipmentSlot.Feet,
            12 => EquipmentSlot.Ring,
            13 => EquipmentSlot.Ammo,
            _ => EquipmentSlot.None
        };
}
