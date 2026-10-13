using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Core.Animations;

namespace RspsItemStudio.Adapters.OpenRune;

public sealed class OpenRuneAnimationCodec : IAnimationCodec
{
    private const string Message = "OpenRune animation codec not verified for this revision yet.";

    public AdapterResult<byte[]> EncodeBindings(AnimationBindingsDocument bindings) =>
        AdapterResult<byte[]>.NotSupported(Message);
}
