namespace RspsItemStudio.Adapters.Abstractions;

/// <summary>
/// Declares a verified adapter feature. Stubs may expose an empty capability set.
/// </summary>
public sealed record AdapterCapability(string Id, string Description);
