using System.Reflection;
using RspsItemStudio.Core.Projects;
using RspsItemStudio.Definitions;

namespace RspsItemStudio.Validation;

public static class ItemProjectValidator
{
    private const int BonusMin = -200;
    private const int BonusMax = 200;

    public static ValidationReport Validate(ItemProject project)
    {
        var issues = new List<ValidationIssue>();

        ValidateName(project, issues);
        ValidateInventoryMesh(project, issues);
        ValidateMaterialTextures(project, issues);
        ValidateEquipSlot(project, issues);
        ValidateBonuses(project, issues);
        ValidateDuplicateItemIds(project, issues);
        EmitAdapterNotImplemented(issues);

        return new ValidationReport
        {
            GeneratedAt = DateTimeOffset.UtcNow,
            Issues = issues
        };
    }

    private static void ValidateName(ItemProject project, List<ValidationIssue> issues)
    {
        if (string.IsNullOrWhiteSpace(project.Definition.Name))
        {
            issues.Add(new ValidationIssue
            {
                Severity = ValidationSeverity.Error,
                Code = "NAME_EMPTY",
                Message = "Item name is required.",
                Path = "Definition.Name"
            });
        }
    }

    private static void ValidateInventoryMesh(ItemProject project, List<ValidationIssue> issues)
    {
        var meshPath = Path.Combine(project.RootDirectory, ItemProjectPaths.InventoryMesh);
        if (!File.Exists(meshPath))
        {
            issues.Add(new ValidationIssue
            {
                Severity = ValidationSeverity.Error,
                Code = "MODEL_MISSING",
                Message = $"Inventory mesh file is missing ({ItemProjectPaths.InventoryMesh}).",
                Path = ItemProjectPaths.InventoryMesh
            });
        }
    }

    private static void ValidateMaterialTextures(ItemProject project, List<ValidationIssue> issues)
    {
        // MaterialsDocument.Slots maps material slot names to texture paths relative to the project root.
        foreach (var (slot, texturePath) in project.Materials.Slots)
        {
            if (string.IsNullOrWhiteSpace(texturePath))
                continue;

            var fullPath = Path.IsPathRooted(texturePath)
                ? texturePath
                : Path.Combine(project.RootDirectory, texturePath);

            if (!File.Exists(fullPath))
            {
                issues.Add(new ValidationIssue
                {
                    Severity = ValidationSeverity.Warning,
                    Code = "TEXTURE_MISSING",
                    Message = $"Texture file for material slot '{slot}' was not found.",
                    Path = $"Materials.Slots.{slot}"
                });
            }
        }
    }

    private static void ValidateEquipSlot(ItemProject project, List<ValidationIssue> issues)
    {
        if (project.Definition.Flags.Equipable && project.Definition.Slot == EquipmentSlot.None)
        {
            issues.Add(new ValidationIssue
            {
                Severity = ValidationSeverity.Error,
                Code = "EQUIP_SLOT_MISSING",
                Message = "Equipable items must specify an equipment slot.",
                Path = "Definition.Slot"
            });
        }
    }

    private static void ValidateBonuses(ItemProject project, List<ValidationIssue> issues)
    {
        foreach (var property in typeof(CombatBonuses).GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            if (property.PropertyType != typeof(int))
                continue;

            var value = (int)(property.GetValue(project.Definition.Bonuses) ?? 0);
            if (value < BonusMin || value > BonusMax)
            {
                issues.Add(new ValidationIssue
                {
                    Severity = ValidationSeverity.Warning,
                    Code = "BONUS_OUT_OF_RANGE",
                    Message = $"Bonus {property.Name} ({value}) is outside the allowed range {BonusMin}..{BonusMax}.",
                    Path = $"Definition.Bonuses.{property.Name}"
                });
            }
        }
    }

    private static void ValidateDuplicateItemIds(ItemProject project, List<ValidationIssue> issues)
    {
        var seen = new HashSet<(string AdapterId, int ItemId)>();
        for (var index = 0; index < project.ExportPresets.Presets.Count; index++)
        {
            var preset = project.ExportPresets.Presets[index];
            if (preset.ItemId is not int itemId)
                continue;

            var key = (preset.AdapterId, itemId);
            if (!seen.Add(key))
            {
                issues.Add(new ValidationIssue
                {
                    Severity = ValidationSeverity.Error,
                    Code = "DUPLICATE_ITEM_ID",
                    Message = $"Duplicate export preset item id {itemId} for adapter '{preset.AdapterId}'.",
                    Path = $"ExportPresets.Presets[{index}]"
                });
            }
        }
    }

    private static void EmitAdapterNotImplemented(List<ValidationIssue> issues)
    {
        issues.Add(new ValidationIssue
        {
            Severity = ValidationSeverity.Info,
            Code = "ADAPTER_NOT_IMPLEMENTED",
            Message = "OpenRune export codecs are not fully implemented in this milestone.",
            Path = null
        });
    }
}
