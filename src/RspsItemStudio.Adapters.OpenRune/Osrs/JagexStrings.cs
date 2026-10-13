using System.Text;

namespace RspsItemStudio.Adapters.OpenRune.Osrs;

/// <summary>
/// Null-terminated Jagex strings. ASCII/Latin-1 subset is used for M2;
/// full CP1252 parity with OpenRune's charset can be layered later.
/// </summary>
internal static class JagexStrings
{
    public static void Write(BinaryWriter writer, string value)
    {
        var bytes = Encoding.Latin1.GetBytes(value);
        writer.Write(bytes);
        writer.Write((byte)0);
    }

    public static string Read(BinaryReader reader)
    {
        var buffer = new List<byte>(32);
        while (true)
        {
            var b = reader.ReadByte();
            if (b == 0)
                break;
            buffer.Add(b);
        }

        return Encoding.Latin1.GetString(buffer.ToArray());
    }
}
