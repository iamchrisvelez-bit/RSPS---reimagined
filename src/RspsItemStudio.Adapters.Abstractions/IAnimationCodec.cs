using RspsItemStudio.Core.Animations;

namespace RspsItemStudio.Adapters.Abstractions;

public interface IAnimationCodec
{
    AdapterResult<byte[]> EncodeBindings(AnimationBindingsDocument bindings);
}
