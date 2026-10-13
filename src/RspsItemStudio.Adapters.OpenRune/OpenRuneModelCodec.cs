using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Core.Meshes;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneModelCodec : IModelCodec
{
    private const string Message = "OpenRune model codec not verified for this revision yet.";

    public AdapterResult<byte[]> Encode(StudioMesh mesh) =>
        AdapterResult<byte[]>.NotSupported(Message);

    public AdapterResult<StudioMesh> Decode(byte[] data) =>
        AdapterResult<StudioMesh>.NotSupported(Message);
}
