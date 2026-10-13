namespace RspsItemStudio.Adapters.Abstractions;

public sealed class AdapterResult<T>
{
    public bool Success { get; init; }
    public bool IsNotSupported { get; init; }
    public string? Message { get; init; }
    public T? Value { get; init; }

    public static AdapterResult<T> Ok(T value) => new() { Success = true, Value = value };

    public static AdapterResult<T> NotSupported(string message) =>
        new() { Success = false, IsNotSupported = true, Message = message };

    public static AdapterResult<T> Fail(string message) =>
        new() { Success = false, Message = message };
}
