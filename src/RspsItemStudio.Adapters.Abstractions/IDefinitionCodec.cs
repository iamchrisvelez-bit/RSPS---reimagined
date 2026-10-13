using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.Abstractions;

public interface IDefinitionCodec
{
    AdapterResult<byte[]> Encode(ItemDefinitionDocument definition);
    AdapterResult<ItemDefinitionDocument> Decode(byte[] data);
}
