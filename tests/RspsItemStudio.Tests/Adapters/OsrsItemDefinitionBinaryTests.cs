using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Adapters.OpenRune;
using RspsItemStudio.Adapters.OpenRune.Osrs;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Projects;
using RspsItemStudio.Definitions;
using Xunit;

namespace RspsItemStudio.Tests.Adapters;

public class OsrsItemDefinitionBinaryTests
{
    [Fact]
    public void Encode_decode_roundTrips_core_fields()
    {
        var definition = new ItemDefinitionDocument
        {
            Name = "Test Scimitar",
            Examine = "A sharp blade.",
            Slot = EquipmentSlot.Weapon,
            WeightKg = 1.5,
            Flags = new ItemFlags
            {
                Tradeable = false,
                Stackable = false,
                Members = true,
                Equipable = true
            },
            Extensions = new Dictionary<string, string>
            {
                ["inventoryModel"] = "1234",
                ["cost"] = "50",
                ["maleModel0"] = "200",
                ["femaleModel0"] = "201"
            }
        };

        var extras = OsrsItemDefinitionExtras.FromExtensions(definition.Extensions);
        var bytes = OsrsItemDefinitionBinary.Encode(definition, extras);
        var (decoded, decodedExtras) = OsrsItemDefinitionBinary.Decode(bytes);

        Assert.Equal("Test Scimitar", decoded.Name);
        Assert.Equal("A sharp blade.", decoded.Examine);
        Assert.Equal(EquipmentSlot.Weapon, decoded.Slot);
        Assert.True(decoded.Flags.Members);
        Assert.False(decoded.Flags.Tradeable);
        Assert.Equal(1234, decodedExtras.InventoryModelId);
        Assert.Equal(50, decodedExtras.Cost);
        Assert.Equal(200, decodedExtras.MaleModel0);
        Assert.Equal(201, decodedExtras.FemaleModel0);
        Assert.Equal(1500, decodedExtras.WeightUnits);
    }

    [Fact]
    public void Toml_exporter_includes_openrune_pack_fields()
    {
        var definition = new ItemDefinitionDocument
        {
            Name = "WowCoins",
            Examine = "Shiny.",
            Flags = new ItemFlags { Stackable = true, Tradeable = true }
        };
        var toml = OpenRuneItemTomlExporter.Export(3434, definition, new OsrsItemDefinitionExtras
        {
            InventoryModelId = 100,
            Cost = 1
        });

        Assert.Contains("id= 3434", toml);
        Assert.Contains("name = \"WowCoins\"", toml);
        Assert.Contains("inventoryModel = 100", toml);
        Assert.Contains("stacks = 1", toml);
    }

    [Fact]
    public void PackToStaging_with_item_id_writes_toml_and_bin()
    {
        var adapter = new OpenRuneAdapter();
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            var project = ItemProjectFactory.Create(root, "Staged Blade");
            project.Definition.Flags.Members = true;
            project.Definition.Extensions["inventoryModel"] = "42";
            var result = adapter.Cache.PackToStaging(new ExportStagingRequest
            {
                Project = project,
                Preset = new ExportPreset
                {
                    AdapterId = "openrune",
                    ItemId = 9001,
                    StagingDirectory = "export/staging"
                }
            });

            Assert.True(result.Success, result.Message);
            Assert.Contains(result.Value!.Entries, e => e.Status == IntegrationEntryStatus.Written);
            Assert.True(File.Exists(Path.Combine(root, "export/staging/openrune-items/9001.toml")));
            Assert.True(File.Exists(Path.Combine(root, "export/staging/openrune-items/9001.obj.bin")));
            var toml = File.ReadAllText(Path.Combine(root, "export/staging/openrune-items/9001.toml"));
            Assert.Contains("id= 9001", toml);
            Assert.Contains("inventoryModel = 42", toml);
        }
        finally
        {
            if (Directory.Exists(root))
                Directory.Delete(root, true);
        }
    }
}
