using RspsItemStudio.Core.Json;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class StudioJsonTests
{
    private sealed record Sample(string Name, int SchemaVersion);

    [Fact]
    public void RoundTrips_camelCase_and_indented()
    {
        var json = StudioJson.Serialize(new Sample("Blade", 1));
        Assert.Contains("\"name\"", json);
        Assert.Contains("\n", json);
        var back = StudioJson.Deserialize<Sample>(json);
        Assert.Equal("Blade", back.Name);
        Assert.Equal(1, back.SchemaVersion);
    }
}
