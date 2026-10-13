using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Projects;
using RspsItemStudio.Definitions;
using RspsItemStudio.Validation;
using Xunit;

namespace RspsItemStudio.Tests.Validation;

public class ItemProjectValidatorTests
{
    [Fact]
    public void Validate_reports_NAME_EMPTY_when_name_is_whitespace()
    {
        using var fixture = new ProjectFixture();
        fixture.Project.Definition.Name = "   ";

        var report = ItemProjectValidator.Validate(fixture.Project);

        Assert.Contains(report.Issues, i => i.Code == "NAME_EMPTY" && i.Severity == ValidationSeverity.Error);
    }

    [Fact]
    public void Validate_reports_MODEL_MISSING_when_inventory_mesh_absent()
    {
        using var fixture = new ProjectFixture();

        var report = ItemProjectValidator.Validate(fixture.Project);

        Assert.Contains(report.Issues, i => i.Code == "MODEL_MISSING" && i.Severity == ValidationSeverity.Error);
    }

    [Fact]
    public void Validate_reports_EQUIP_SLOT_MISSING_when_equipable_without_slot()
    {
        using var fixture = new ProjectFixture();
        fixture.Project.Definition.Flags.Equipable = true;
        fixture.Project.Definition.Slot = EquipmentSlot.None;

        var report = ItemProjectValidator.Validate(fixture.Project);

        Assert.Contains(report.Issues, i => i.Code == "EQUIP_SLOT_MISSING" && i.Severity == ValidationSeverity.Error);
    }

    [Fact]
    public void Validate_reports_DUPLICATE_ITEM_ID_for_same_adapter_and_item_id()
    {
        using var fixture = new ProjectFixture();
        fixture.Project.ExportPresets.Presets.Add(new ExportPreset { AdapterId = "openrune", ItemId = 12345 });
        fixture.Project.ExportPresets.Presets.Add(new ExportPreset { AdapterId = "openrune", ItemId = 12345 });

        var report = ItemProjectValidator.Validate(fixture.Project);

        Assert.Contains(report.Issues, i => i.Code == "DUPLICATE_ITEM_ID" && i.Severity == ValidationSeverity.Error);
    }

    [Fact]
    public void SaveValidationReport_writes_validation_last_report_json()
    {
        using var fixture = new ProjectFixture();
        var report = ItemProjectValidator.Validate(fixture.Project);

        fixture.Project.SaveValidationReport(report);

        var path = Path.Combine(fixture.Root, ItemProjectPaths.ValidationReport);
        Assert.True(File.Exists(path));
        Assert.Contains("issues", File.ReadAllText(path), StringComparison.OrdinalIgnoreCase);
    }

    private sealed class ProjectFixture : IDisposable
    {
        public string Root { get; }
        public ItemProject Project { get; }

        public ProjectFixture()
        {
            Root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
            Project = ItemProjectFactory.Create(Root, "Valid Item");
        }

        public void Dispose()
        {
            if (Directory.Exists(Root))
                Directory.Delete(Root, true);
        }
    }
}
