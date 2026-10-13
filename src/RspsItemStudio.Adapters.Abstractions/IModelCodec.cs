using RspsItemStudio.Core.Meshes;

namespace RspsItemStudio.Adapters.Abstractions;

public interface IModelCodec
{
    AdapterResult<byte[]> Encode(StudioMesh mesh);
    AdapterResult<StudioMesh> Decode(byte[] data);
}
