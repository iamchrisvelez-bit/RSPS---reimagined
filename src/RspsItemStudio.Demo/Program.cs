using RspsItemStudio.Adapters.Abstractions;
using RspsItemStudio.Adapters.OpenRune;
using RspsItemStudio.Core.Export;
using RspsItemStudio.Core.Projects;
using RspsItemStudio.Definitions;
using RspsItemStudio.Modeling;
using RspsItemStudio.Validation;

static void Banner(string title)
{
    Console.WriteLine();
    Console.WriteLine("==== " + title + " ====");
}

var root = args.ElementAtOrDefault(0)
    ?? Path.Combine(Path.GetTempPath(), "itemstudio-demo-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
var objPath = args.ElementAtOrDefault(1)
    ?? Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "tests", "RspsItemStudio.Tests", "Fixtures", "cube.obj"));

if (!File.Exists(objPath))
{
    // Fallback: copy from known workspace path
    var fallback = "/workspace/tests/RspsItemStudio.Tests/Fixtures/cube.obj";
    if (File.Exists(fallback))
        objPath = fallback;
}

Console.WriteLine("RSPS Item Studio — Linux pipeline demo");
Console.WriteLine("(WPF UI requires Windows; this runs the same Core/Adapters libraries.)");
Console.WriteLine("Project root: " + root);
Console.WriteLine("OBJ source:   " + objPath);

Banner("1) Create item project");
if (Directory.Exists(root))
    Directory.Delete(root, true);
var project = ItemProjectFactory.Create(root, "Demo Dragon Blade");
Console.WriteLine("Created project for: " + project.Definition.Name);
Console.WriteLine("Files:");
foreach (var path in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories).OrderBy(p => p))
    Console.WriteLine("  " + Path.GetRelativePath(root, path));

Banner("2) Import OBJ → inventory mesh");
var import = ObjMeshImporter.Import(objPath);
Console.WriteLine($"Imported mesh: {import.Mesh.Vertices.Count} verts, {import.Mesh.Triangles.Count} tris");
if (import.Warnings.Count > 0)
    Console.WriteLine("Warnings: " + string.Join("; ", import.Warnings));
var attached = project.AttachInventoryMesh(import.Mesh, objPath);
Console.WriteLine("Wrote: " + Path.GetRelativePath(root, attached));

Banner("3) Configure stats + OpenRune export preset");
project.Definition.Examine = "A razor-sharp custom blade forged in Item Studio.";
project.Definition.Slot = EquipmentSlot.Weapon;
project.Definition.Flags.Equipable = true;
project.Definition.Flags.Members = true;
project.Definition.Flags.Tradeable = true;
project.Definition.Bonuses.AttackSlash = 45;
project.Definition.Bonuses.MeleeStrength = 40;
project.Definition.Requirements.Attack = 60;
project.Definition.WeightKg = 1.8;
project.Definition.Extensions["inventoryModel"] = "12345";
project.Definition.Extensions["cost"] = "85000";
project.Definition.Extensions["maleModel0"] = "23456";
project.ExportPresets.Presets[0].ItemId = 50_001;
project.Save();
Console.WriteLine($"Name={project.Definition.Name}, Slot={project.Definition.Slot}, ItemId={project.ExportPresets.Presets[0].ItemId}");

Banner("4) Validate");
var report = ItemProjectValidator.Validate(project);
project.SaveValidationReport(report);
Console.WriteLine($"Issues: {report.Issues.Count}, HasErrors={report.HasErrors}");
foreach (var issue in report.Issues)
    Console.WriteLine($"  [{issue.Severity}] {issue.Code}: {issue.Message}");

Banner("5) Export staging (OpenRune)");
var adapter = new OpenRuneAdapter();
var export = adapter.Cache.PackToStaging(new ExportStagingRequest
{
    Project = project,
    Preset = project.ExportPresets.Presets[0]
});
Console.WriteLine("Success: " + export.Success);
Console.WriteLine("Summary: " + (export.Value?.Summary ?? export.Message));
if (export.Value is not null)
{
    foreach (var entry in export.Value.Entries)
        Console.WriteLine($"  [{entry.Status}] {entry.Category}: {entry.Message}");
}

Banner("6) Staged OpenRune artifacts");
var toml = Path.Combine(root, "export/staging/openrune-items/50001.toml");
var bin = Path.Combine(root, "export/staging/openrune-items/50001.obj.bin");
if (File.Exists(toml))
{
    Console.WriteLine("--- " + Path.GetRelativePath(root, toml) + " ---");
    Console.WriteLine(File.ReadAllText(toml));
}
if (File.Exists(bin))
    Console.WriteLine($"Binary definition bytes: {new FileInfo(bin).Length} ({Path.GetRelativePath(root, bin)})");

Banner("Done");
Console.WriteLine("DEMO_PROJECT_ROOT=" + root);
