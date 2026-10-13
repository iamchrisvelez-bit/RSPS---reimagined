using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Adapters.OpenRune.Osrs;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneDefinitionCodec : IDefinitionCodec
{
    public AdapterResult<byte[]> Encode(ItemDefinitionDocument definition)
    {
        try
        {
            var extras = OsrsItemDefinitionExtras.FromExtensions(definition.Extensions);
            var bytes = OsrsItemDefinitionBinary.Encode(definition, extras);
            return AdapterResult<byte[]>.Ok(bytes);
        }
        catch (Exception ex)
        {
            return AdapterResult<byte[]>.Fail("Failed to encode OpenRune/OSRS item definition: " + ex.Message);
        }
    }

    public AdapterResult<ItemDefinitionDocument> Decode(byte[] data)
    {
        try
        {
            var (definition, extras) = OsrsItemDefinitionBinary.Decode(data);
            if (extras.InventoryModelId is int inv)
                definition.Extensions["inventoryModel"] = inv.ToString();
            if (extras.Cost is int cost)
                definition.Extensions["cost"] = cost.ToString();
            if (extras.MaleModel0 is int male)
                definition.Extensions["maleModel0"] = male.ToString();
            if (extras.FemaleModel0 is int female)
                definition.Extensions["femaleModel0"] = female.ToString();
            if (extras.WeightUnits is int weight)
                definition.Extensions["weightUnits"] = weight.ToString();
            return AdapterResult<ItemDefinitionDocument>.Ok(definition);
        }
        catch (Exception ex)
        {
            return AdapterResult<ItemDefinitionDocument>.Fail(
                "Failed to decode OpenRune/OSRS item definition: " + ex.Message);
        }
    }
}
