namespace RspsItemStudio.Core.Animations;

public sealed class AnimationBindingsDocument
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string? Idle { get; set; }
    public string? Walk { get; set; }
    public string? Attack { get; set; }
    public string? SpecialAttack { get; set; }
    public string? Equip { get; set; }
}
