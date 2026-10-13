using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneDefinitionCodec : IDefinitionCodec
{
    private const string Message = "OpenRune definition codec not verified for this revision yet.";

    public AdapterResult<byte[]> Encode(ItemDefinitionDocument definition) =>
        AdapterResult<byte[]>.NotSupported(Message);

    public AdapterResult<ItemDefinitionDocument> Decode(byte[] data) =>
        AdapterResult<ItemDefinitionDocument>.NotSupported(Message);
}
