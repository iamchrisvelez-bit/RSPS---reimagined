# Milestone 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Windows .NET 8 Item Studio foundation: portable item projects, OBJ→studio mesh import, WPF shell with stats editor and validation, Veldrid viewport, and honest OpenRune adapter stubs (no fake cache export).

**Architecture:** Revision-neutral `ItemProject` in Core; Modeling imports meshes; Definitions/Validation operate on project documents; Adapters.Abstractions define codecs; Adapters.OpenRune returns explicit `NotSupported` until formats are verified; WPF App hosts editors + Veldrid viewport.

**Tech Stack:** .NET 8, WPF (`net8.0-windows`), Veldrid + Veldrid.StartupUtilities, System.Text.Json, xUnit, coverlet (optional)

**Spec:** `docs/superpowers/specs/2026-10-13-rsps-item-studio-design.md`

## Global Constraints

- Target platform: Windows only for the WPF app (`net8.0-windows`)
- Class libraries (Core, Modeling, Definitions, Validation, Adapters.*) target `net8.0` so unit tests run on Linux CI / cloud agents
- Never invent OpenRune/OSRS cache bytes; unimplemented adapter ops return `AdapterResult.NotSupported(...)`
- Never write into live client/server/cache paths in M1; export stages to a folder under the project or a user-chosen staging directory and writes an integration report only
- Destructive game-tree writes are out of scope for M1 (interfaces may exist; implementations must refuse)
- Prefer small focused files; no monolithic god-classes
- TDD: failing test → implement → pass → commit per task
- Keep `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md` accurate after scaffolding

---

## File structure (create)

```
/
  RSPS.ItemStudio.sln
  DIRECTORY.md                          # optional pointer; skip if unused
  PROJECT_ROADMAP.md
  ARCHITECTURE.md
  COMPATIBILITY.md
  README.md                             # replace stub with run instructions
  src/
    RspsItemStudio.Core/
      RspsItemStudio.Core.csproj
      Projects/
        ItemProject.cs
        ItemProjectPaths.cs
        ItemStudioManifest.cs
        ItemProjectLoader.cs
        ItemProjectFactory.cs
      Colors/
        RecolorDocument.cs
        JagexColor.cs
      Materials/
        MaterialsDocument.cs
      Animations/
        AnimationBindingsDocument.cs
      Effects/
        EffectsDocument.cs
      Export/
        ExportPresetsDocument.cs
      Meshes/
        StudioMesh.cs
        StudioVertex.cs
        StudioTriangle.cs
      Json/
        StudioJson.cs
    RspsItemStudio.Definitions/
      RspsItemStudio.Definitions.csproj
      ItemDefinitionDocument.cs
      EquipmentSlot.cs
      CombatBonuses.cs
      LevelRequirements.cs
      ItemFlags.cs
    RspsItemStudio.Modeling/
      RspsItemStudio.Modeling.csproj
      ObjMeshImporter.cs
      MeshImportResult.cs
      MeshTransform.cs
    RspsItemStudio.Validation/
      RspsItemStudio.Validation.csproj
      ValidationSeverity.cs
      ValidationIssue.cs
      ValidationReport.cs
      ItemProjectValidator.cs
    RspsItemStudio.Adapters.Abstractions/
      RspsItemStudio.Adapters.Abstractions.csproj
      AdapterCapability.cs
      AdapterResult.cs
      IRevisionAdapter.cs
      IModelCodec.cs
      IAnimationCodec.cs
      IDefinitionCodec.cs
      ICachePacker.cs
      IRevisionPreview.cs
      ExportStagingRequest.cs
      IntegrationReport.cs
    RspsItemStudio.Adapters.OpenRune/
      RspsItemStudio.Adapters.OpenRune.csproj
      OpenRuneAdapter.cs
      OpenRuneModelCodec.cs
      OpenRuneDefinitionCodec.cs
      OpenRuneAnimationCodec.cs
      OpenRuneCachePacker.cs
    RspsItemStudio.Adapters.Rev317/
      RspsItemStudio.Adapters.Rev317.csproj
      Rev317Adapter.cs
    RspsItemStudio.Rendering/
      RspsItemStudio.Rendering.csproj   # net8.0-windows
      ViewportCamera.cs
      ViewportScene.cs
      MeshGpuUpload.cs
      VeldridViewportController.cs
    RspsItemStudio.App/
      RspsItemStudio.App.csproj         # net8.0-windows WPF
      App.xaml
      App.xaml.cs
      MainWindow.xaml
      MainWindow.xaml.cs
      ViewModels/
        MainViewModel.cs
        ItemDefinitionViewModel.cs
        ValidationViewModel.cs
        ViewportViewModel.cs
      Views/
        StatEditorView.xaml
        StatEditorView.xaml.cs
        ValidationReportView.xaml
        ValidationReportView.xaml.cs
        ViewportHost.xaml
        ViewportHost.xaml.cs
      Services/
        ProjectDialogService.cs
        RelayCommand.cs
  tests/
    RspsItemStudio.Tests/
      RspsItemStudio.Tests.csproj
      Core/
        ItemProjectFactoryTests.cs
        ItemProjectLoaderTests.cs
        JagexColorTests.cs
      Definitions/
        ItemDefinitionDocumentTests.cs
      Modeling/
        ObjMeshImporterTests.cs
      Validation/
        ItemProjectValidatorTests.cs
      Adapters/
        OpenRuneAdapterTests.cs
      Fixtures/
        cube.obj
```

---

### Task 1: Solution scaffold + living docs + JSON helpers

**Files:**
- Create: `RSPS.ItemStudio.sln`
- Create: `src/RspsItemStudio.Core/RspsItemStudio.Core.csproj`
- Create: `src/RspsItemStudio.Core/Json/StudioJson.cs`
- Create: `tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj`
- Create: `tests/RspsItemStudio.Tests/Core/StudioJsonTests.cs`
- Create: `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: none
- Produces: `StudioJson.Options` (`JsonSerializerOptions`), `StudioJson.Serialize<T>(T value)`, `StudioJson.Deserialize<T>(string json)`

- [ ] **Step 1: Install .NET 8 SDK if missing**

```bash
dotnet --version || (curl -fsSL https://dot.net/v1/dotnet-install.sh | bash /dev/stdin --channel 8.0 && export DOTNET_ROOT=$HOME/.dotnet && export PATH=$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools)
dotnet --version
```

Expected: prints `8.x.x`

- [ ] **Step 2: Write the failing test**

Create `tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />
    <ProjectReference Include="..\..\src\RspsItemStudio.Core\RspsItemStudio.Core.csproj" />
  </ItemGroup>
</Project>
```

Create `tests/RspsItemStudio.Tests/Core/StudioJsonTests.cs`:

```csharp
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
```

- [ ] **Step 3: Run test to verify it fails**

```bash
dotnet test tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj --filter FullyQualifiedName~StudioJsonTests
```

Expected: FAIL (project or type missing)

- [ ] **Step 4: Create Core project + StudioJson**

`src/RspsItemStudio.Core/RspsItemStudio.Core.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```

`src/RspsItemStudio.Core/Json/StudioJson.cs`:

```csharp
using System.Text.Json;
using System.Text.Json.Serialization;

namespace RspsItemStudio.Core.Json;

public static class StudioJson
{
    public static JsonSerializerOptions Options { get; } = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) }
    };

    public static string Serialize<T>(T value) =>
        JsonSerializer.Serialize(value, Options);

    public static T Deserialize<T>(string json) =>
        JsonSerializer.Deserialize<T>(json, Options)
        ?? throw new InvalidOperationException($"Failed to deserialize {typeof(T).Name}.");
}
```

Create solution and add projects:

```bash
dotnet new sln -n RSPS.ItemStudio -o .
dotnet sln RSPS.ItemStudio.sln add src/RspsItemStudio.Core/RspsItemStudio.Core.csproj
dotnet sln RSPS.ItemStudio.sln add tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
dotnet test tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj --filter FullyQualifiedName~StudioJsonTests
```

Expected: PASS

- [ ] **Step 6: Seed living docs + README**

Write `PROJECT_ROADMAP.md` with M1 in progress and M2–M6 from the spec.  
Write `ARCHITECTURE.md` summarizing modules from the spec.  
Write `COMPATIBILITY.md` stating OpenRune-first, Rev317 stub, unknowns from spec §12.  
Replace `README.md` with build/run instructions (`dotnet test`, `dotnet run --project src/RspsItemStudio.App` on Windows).

- [ ] **Step 7: Commit**

```bash
git add RSPS.ItemStudio.sln src/RspsItemStudio.Core tests/RspsItemStudio.Tests PROJECT_ROADMAP.md ARCHITECTURE.md COMPATIBILITY.md README.md
git commit -m "chore: scaffold solution, StudioJson, and living docs"
```

---

### Task 2: Item project factory, paths, and loader

**Files:**
- Create: `src/RspsItemStudio.Core/Projects/ItemStudioManifest.cs`
- Create: `src/RspsItemStudio.Core/Projects/ItemProjectPaths.cs`
- Create: `src/RspsItemStudio.Core/Projects/ItemProject.cs`
- Create: `src/RspsItemStudio.Core/Projects/ItemProjectFactory.cs`
- Create: `src/RspsItemStudio.Core/Projects/ItemProjectLoader.cs`
- Create: `src/RspsItemStudio.Core/Colors/RecolorDocument.cs`
- Create: `src/RspsItemStudio.Core/Materials/MaterialsDocument.cs`
- Create: `src/RspsItemStudio.Core/Animations/AnimationBindingsDocument.cs`
- Create: `src/RspsItemStudio.Core/Effects/EffectsDocument.cs`
- Create: `src/RspsItemStudio.Core/Export/ExportPresetsDocument.cs`
- Create: `src/RspsItemStudio.Definitions/*` (minimal docs referenced by Core — see Step 4)
- Create: `tests/RspsItemStudio.Tests/Core/ItemProjectFactoryTests.cs`
- Create: `tests/RspsItemStudio.Tests/Core/ItemProjectLoaderTests.cs`

**Interfaces:**
- Consumes: `StudioJson`
- Produces:
  - `ItemProjectFactory.Create(string rootDirectory, string displayName) -> ItemProject`
  - `ItemProjectLoader.Load(string rootDirectory) -> ItemProject`
  - `ItemProject.Save()`
  - `ItemProjectPaths` relative path constants

- [ ] **Step 1: Write failing factory test**

```csharp
using RspsItemStudio.Core.Projects;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class ItemProjectFactoryTests
{
    [Fact]
    public void Create_writes_required_documents()
    {
        var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
        try
        {
            var project = ItemProjectFactory.Create(root, "Test Scimitar");
            Assert.True(File.Exists(Path.Combine(root, "itemstudio.json")));
            Assert.True(File.Exists(Path.Combine(root, "meta", "item.json")));
            Assert.True(File.Exists(Path.Combine(root, "colors", "recolor.json")));
            Assert.True(File.Exists(Path.Combine(root, "materials", "materials.json")));
            Assert.True(File.Exists(Path.Combine(root, "animations", "bindings.json")));
            Assert.True(File.Exists(Path.Combine(root, "effects", "effects.json")));
            Assert.True(File.Exists(Path.Combine(root, "export", "presets.json")));
            Assert.Equal("Test Scimitar", project.Definition.Name);
            Assert.Equal(1, project.Manifest.SchemaVersion);
        }
        finally
        {
            if (Directory.Exists(root)) Directory.Delete(root, true);
        }
    }
}
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
dotnet test tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj --filter FullyQualifiedName~ItemProjectFactoryTests
```

- [ ] **Step 3: Add Definitions project (minimal) referenced by Core**

Create `src/RspsItemStudio.Definitions/RspsItemStudio.Definitions.csproj` (`net8.0`).

`EquipmentSlot.cs`:

```csharp
namespace RspsItemStudio.Definitions;

public enum EquipmentSlot
{
    None = 0,
    Weapon = 1,
    Shield = 2,
    Helmet = 3,
    Cape = 4,
    Amulet = 5,
    Body = 6,
    Legs = 7,
    Hands = 8,
    Feet = 9,
    Ring = 10,
    Ammo = 11
}
```

`CombatBonuses.cs`, `LevelRequirements.cs`, `ItemFlags.cs`, `ItemDefinitionDocument.cs`:

```csharp
namespace RspsItemStudio.Definitions;

public sealed class CombatBonuses
{
    public int AttackStab { get; set; }
    public int AttackSlash { get; set; }
    public int AttackCrush { get; set; }
    public int AttackMagic { get; set; }
    public int AttackRanged { get; set; }
    public int DefenceStab { get; set; }
    public int DefenceSlash { get; set; }
    public int DefenceCrush { get; set; }
    public int DefenceMagic { get; set; }
    public int DefenceRanged { get; set; }
    public int MeleeStrength { get; set; }
    public int RangedStrength { get; set; }
    public int MagicDamage { get; set; }
    public int Prayer { get; set; }
}

public sealed class LevelRequirements
{
    public int Attack { get; set; }
    public int Strength { get; set; }
    public int Defence { get; set; }
    public int Hitpoints { get; set; }
    public int Ranged { get; set; }
    public int Prayer { get; set; }
    public int Magic { get; set; }
}

public sealed class ItemFlags
{
    public bool Tradeable { get; set; } = true;
    public bool Stackable { get; set; }
    public bool Noted { get; set; }
    public bool Members { get; set; }
    public bool Equipable { get; set; }
}

public sealed class ItemDefinitionDocument
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = "New Item";
    public string Examine { get; set; } = "It's an item.";
    public EquipmentSlot Slot { get; set; } = EquipmentSlot.None;
    public CombatBonuses Bonuses { get; set; } = new();
    public LevelRequirements Requirements { get; set; } = new();
    public double WeightKg { get; set; }
    public ItemFlags Flags { get; set; } = new();
    public Dictionary<string, string> Extensions { get; set; } = new();
}
```

Add project reference Core → Definitions. Add Definitions to solution and test project references.

- [ ] **Step 4: Implement Core project documents + factory/loader**

`ItemStudioManifest.cs`:

```csharp
namespace RspsItemStudio.Core.Projects;

public sealed class ItemStudioManifest
{
    public int SchemaVersion { get; set; } = 1;
    public Guid ProjectId { get; set; } = Guid.NewGuid();
    public string DisplayName { get; set; } = "New Item";
    public List<string> EnabledAdapters { get; set; } = new() { "openrune" };
}
```

`ItemProjectPaths.cs` — constants: `Manifest = "itemstudio.json"`, `Definition = "meta/item.json"`, `Recolor = "colors/recolor.json"`, `Materials = "materials/materials.json"`, `Animations = "animations/bindings.json"`, `Effects = "effects/effects.json"`, `ExportPresets = "export/presets.json"`, `InventoryMesh = "models/inventory.mesh.json"`, `SourceDir = "models/source"`, `TexturesDir = "materials/textures"`, `ValidationReport = "validation/last-report.json"`.

Stub documents (`RecolorDocument`, `MaterialsDocument`, `AnimationBindingsDocument`, `EffectsDocument`, `ExportPresetsDocument`) with `Guid Id` and empty lists/dicts as needed — include:

```csharp
public sealed class RecolorDocument
{
    public int? PrimaryHsl { get; set; }
    public int? SecondaryHsl { get; set; }
    public int? DetailHsl { get; set; }
    public string? PrimaryRgb { get; set; }
    public string? SecondaryRgb { get; set; }
    public string? DetailRgb { get; set; }
    public Dictionary<string, int> Presets { get; set; } = new();
}

public sealed class ExportPresetsDocument
{
    public List<ExportPreset> Presets { get; set; } = new();
}

public sealed class ExportPreset
{
    public string AdapterId { get; set; } = "openrune";
    public int? ItemId { get; set; }
    public string StagingDirectory { get; set; } = "export/staging";
}
```

`AnimationBindingsDocument` must include string nullable properties: `Idle`, `Walk`, `Attack`, `SpecialAttack`, `Equip` (game IDs later).

`ItemProject` holds `RootDirectory`, `Manifest`, `Definition`, and the documents above; `Save()` writes all JSON via `StudioJson`.

`ItemProjectFactory.Create` creates directories (`meta`, `models/source`, `materials/textures`, `colors`, `animations/clips`, `effects`, `export`, `validation`), initializes documents (`Definition.Name = displayName`, `Manifest.DisplayName = displayName`), calls `Save()`, returns project.

`ItemProjectLoader.Load` reads manifest + documents (missing optional mesh files are OK).

- [ ] **Step 5: Write loader round-trip test**

```csharp
[Fact]
public void Load_roundTrips_factory_project()
{
    var root = Path.Combine(Path.GetTempPath(), "itemstudio-" + Guid.NewGuid().ToString("N"));
    try
    {
        ItemProjectFactory.Create(root, "Round Trip");
        var loaded = ItemProjectLoader.Load(root);
        Assert.Equal("Round Trip", loaded.Definition.Name);
        Assert.Contains("openrune", loaded.Manifest.EnabledAdapters);
    }
    finally
    {
        if (Directory.Exists(root)) Directory.Delete(root, true);
    }
}
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
dotnet test tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj --filter "FullyQualifiedName~ItemProjectFactoryTests|FullyQualifiedName~ItemProjectLoaderTests"
```

- [ ] **Step 7: Commit**

```bash
git add src/RspsItemStudio.Core src/RspsItemStudio.Definitions tests/RspsItemStudio.Tests
git commit -m "feat: item project factory, paths, and loader"
```

---

### Task 3: Jagex color helpers

**Files:**
- Create: `src/RspsItemStudio.Core/Colors/JagexColor.cs`
- Create: `tests/RspsItemStudio.Tests/Core/JagexColorTests.cs`

**Interfaces:**
- Consumes: none
- Produces: `JagexColor.PackHsl(int hue, int saturation, int lightness) -> int`, `JagexColor.UnpackHsl(int packed, out int h, out int s, out int l)`, `JagexColor.ToRgb(int packedHsl) -> (byte r, byte g, byte b)`

- [ ] **Step 1: Write failing tests**

```csharp
using RspsItemStudio.Core.Colors;
using Xunit;

namespace RspsItemStudio.Tests.Core;

public class JagexColorTests
{
    [Fact]
    public void Pack_unpack_roundTrip()
    {
        var packed = JagexColor.PackHsl(33, 3, 40);
        JagexColor.UnpackHsl(packed, out var h, out var s, out var l);
        Assert.Equal(33, h);
        Assert.Equal(3, s);
        Assert.Equal(40, l);
    }

    [Fact]
    public void ToRgb_returns_bytes_in_range()
    {
        var (r, g, b) = JagexColor.ToRgb(JagexColor.PackHsl(0, 0, 64));
        Assert.InRange(r, (byte)0, (byte)255);
        Assert.InRange(g, (byte)0, (byte)255);
        Assert.InRange(b, (byte)0, (byte)255);
    }
}
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `JagexColor`**

Use classic RS packed HSL layout: `hue << 10 | saturation << 7 | lightness` with hue 0–63, saturation 0–7, lightness 0–127. Implement `ToRgb` with the standard RS HSL→RGB approximation (document formula in XML comment). Clamp inputs.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: Jagex packed HSL color helpers"
```

---

### Task 4: OBJ importer → StudioMesh

**Files:**
- Create: `src/RspsItemStudio.Core/Meshes/StudioVertex.cs`
- Create: `src/RspsItemStudio.Core/Meshes/StudioTriangle.cs`
- Create: `src/RspsItemStudio.Core/Meshes/StudioMesh.cs`
- Create: `src/RspsItemStudio.Modeling/RspsItemStudio.Modeling.csproj`
- Create: `src/RspsItemStudio.Modeling/ObjMeshImporter.cs`
- Create: `src/RspsItemStudio.Modeling/MeshImportResult.cs`
- Create: `tests/RspsItemStudio.Tests/Fixtures/cube.obj`
- Create: `tests/RspsItemStudio.Tests/Modeling/ObjMeshImporterTests.cs`

**Interfaces:**
- Consumes: `StudioMesh`, `StudioJson`
- Produces: `ObjMeshImporter.Import(string objPath) -> MeshImportResult` where `MeshImportResult` has `StudioMesh Mesh`, `IReadOnlyList<string> Warnings`

`StudioMesh`:

```csharp
public sealed class StudioMesh
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = "mesh";
    public List<StudioVertex> Vertices { get; set; } = new();
    public List<StudioTriangle> Triangles { get; set; } = new();
}

public sealed class StudioVertex
{
    public float X { get; set; }
    public float Y { get; set; }
    public float Z { get; set; }
    public float U { get; set; }
    public float V { get; set; }
}

public sealed class StudioTriangle
{
    public int A { get; set; }
    public int B { get; set; }
    public int C { get; set; }
}
```

- [ ] **Step 1: Add fixture `cube.obj`** (unit cube with UVs and triangulated faces)

- [ ] **Step 2: Write failing test**

```csharp
[Fact]
public void Import_cube_obj_produces_triangles()
{
    var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "cube.obj");
    var result = ObjMeshImporter.Import(path);
    Assert.True(result.Mesh.Vertices.Count >= 8);
    Assert.True(result.Mesh.Triangles.Count >= 12);
}
```

Ensure csproj copies Fixtures to output:

```xml
<ItemGroup>
  <None Include="Fixtures\**\*" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```

Add Modeling project reference to Tests.

- [ ] **Step 3: Run — expect FAIL**

- [ ] **Step 4: Implement `ObjMeshImporter`**

Parse `v`, `vt`, `f` lines. Support `f v/vt/vn` and `f v//vn` and `f v`. Triangulate fan for n-gons. Missing UVs → `(0,0)` + warning. Ignore `vn` in M1 (viewport can flat-shade).

Add `ItemProject.AttachInventoryMesh(StudioMesh mesh)` helper that writes `models/inventory.mesh.json` and sets an in-memory reference — or keep attach logic in App; for tests, serialize mesh with `StudioJson` to the path.

- [ ] **Step 5: Run — expect PASS**

- [ ] **Step 6: Commit**

```bash
git add src/RspsItemStudio.Core/Meshes src/RspsItemStudio.Modeling tests/RspsItemStudio.Tests
git commit -m "feat: OBJ importer and StudioMesh format"
```

---

### Task 5: Validation engine

**Files:**
- Create: `src/RspsItemStudio.Validation/*`
- Create: `tests/RspsItemStudio.Tests/Validation/ItemProjectValidatorTests.cs`

**Interfaces:**
- Consumes: `ItemProject`, `ItemDefinitionDocument`, `ExportPresetsDocument`
- Produces: `ItemProjectValidator.Validate(ItemProject project) -> ValidationReport`

```csharp
public enum ValidationSeverity { Info, Warning, Error }

public sealed class ValidationIssue
{
    public ValidationSeverity Severity { get; init; }
    public string Code { get; init; } = "";
    public string Message { get; init; } = "";
    public string? Path { get; init; }
}

public sealed class ValidationReport
{
    public DateTimeOffset GeneratedAt { get; init; }
    public List<ValidationIssue> Issues { get; init; } = new();
    public bool HasErrors => Issues.Any(i => i.Severity == ValidationSeverity.Error);
}
```

Rules (M1):

| Code | Severity | Condition |
|------|----------|-----------|
| `NAME_EMPTY` | Error | name null/whitespace |
| `MODEL_MISSING` | Error | `models/inventory.mesh.json` missing |
| `TEXTURE_MISSING` | Warning | materials reference texture file that does not exist |
| `EQUIP_SLOT_MISSING` | Error | `Flags.Equipable && Slot == None` |
| `BONUS_OUT_OF_RANGE` | Warning | any bonus outside `-200..200` (document chosen clamp) |
| `DUPLICATE_ITEM_ID` | Error | two presets same adapter+itemId |
| `ADAPTER_NOT_IMPLEMENTED` | Info | always emit info that OpenRune export codecs are not fully implemented |

- [ ] **Step 1: Write failing tests** for empty name, missing model, equipable without slot, duplicate item ids

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement validator + `ValidationReport` JSON save to `validation/last-report.json` via `ItemProject.SaveValidationReport(ValidationReport)`**

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: item project validation report"
```

---

### Task 6: Adapter abstractions + OpenRune / Rev317 stubs

**Files:**
- Create: all under `src/RspsItemStudio.Adapters.Abstractions/`
- Create: `src/RspsItemStudio.Adapters.OpenRune/*`
- Create: `src/RspsItemStudio.Adapters.Rev317/Rev317Adapter.cs`
- Create: `tests/RspsItemStudio.Tests/Adapters/OpenRuneAdapterTests.cs`

**Interfaces:**
- Produces:

```csharp
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

public interface IRevisionAdapter
{
    string Id { get; }
    string DisplayName { get; }
    IReadOnlyCollection<AdapterCapability> Capabilities { get; }
    IModelCodec Models { get; }
    IAnimationCodec Animations { get; }
    IDefinitionCodec Definitions { get; }
    ICachePacker Cache { get; }
}

public interface IDefinitionCodec
{
    AdapterResult<byte[]> Encode(ItemDefinitionDocument definition);
    AdapterResult<ItemDefinitionDocument> Decode(byte[] data);
}

public interface IModelCodec
{
    AdapterResult<byte[]> Encode(StudioMesh mesh);
    AdapterResult<StudioMesh> Decode(byte[] data);
}

public interface IAnimationCodec
{
    AdapterResult<byte[]> EncodeBindings(AnimationBindingsDocument bindings);
}

public interface ICachePacker
{
    AdapterResult<IntegrationReport> PackToStaging(ExportStagingRequest request);
    AdapterResult<IntegrationReport> PackToLiveTree(ExportStagingRequest request);
}
```

`OpenRuneAdapter`: `Id = "openrune"`, `Capabilities` empty or documentation-only flags. Every codec method returns `NotSupported("OpenRune <X> codec not verified for this revision yet.")`.  
`PackToLiveTree` always `Fail("Live cache/server writes are disabled until formats are verified and backup flow ships.")`.  
`PackToStaging` may create an empty staging folder + `IntegrationReport` explaining nothing was packed (still Success with clear messages) **or** return NotSupported — prefer **Success with report entries stating skipped** so the UI can show an integration report without faking files.

`Rev317Adapter`: same NotSupported pattern, `Id = "rev317"`.

- [ ] **Step 1: Write failing tests** asserting OpenRune model encode is NotSupported and live pack fails

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement abstractions + adapters**

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Update `COMPATIBILITY.md`** with adapter status table

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: revision adapter contracts and OpenRune/317 stubs"
```

---

### Task 7: WPF application shell + project workspace

**Files:**
- Create: `src/RspsItemStudio.App/**` (as listed in file structure)
- Modify: `RSPS.ItemStudio.sln`, `README.md`, `PROJECT_ROADMAP.md`

**Interfaces:**
- Consumes: `ItemProjectFactory`, `ItemProjectLoader`, `ItemProject.Save`
- Produces: runnable WPF app with Create / Open / Save

**Note:** Cloud/Linux agents cannot run WPF. Implement App on `net8.0-windows`. Verify compile with:

```bash
dotnet build src/RspsItemStudio.App/RspsItemStudio.App.csproj
```

On non-Windows, if SDK lacks targeting pack, install windows pack or document that App build is Windows-only; still keep libraries tested on Linux.

- [ ] **Step 1: Create WPF project**

```bash
dotnet new wpf -n RspsItemStudio.App -o src/RspsItemStudio.App -f net8.0
dotnet sln add src/RspsItemStudio.App/RspsItemStudio.App.csproj
```

Retarget to `net8.0-windows`, add references to Core, Definitions, Modeling, Validation, Adapters.*.

- [ ] **Step 2: Implement `RelayCommand`, `ProjectDialogService` (OpenFileDialog/Save folder picker via `Microsoft.Win32` and `FolderBrowser` or `Ookii.Dialogs.Wpf` if needed — prefer built-in `OpenFolderDialog` on .NET 8 WPF if available, else WinForms folder dialog reference)**

- [ ] **Step 3: `MainViewModel`**

Properties: `CurrentProject`, `StatusText`, `Definition` VM, `Validation` VM.  
Commands: `NewProjectCommand`, `OpenProjectCommand`, `SaveProjectCommand`, `ImportObjCommand`, `ValidateCommand`, `ExportStagingCommand`.

`NewProject`: pick folder + name → `ItemProjectFactory.Create`.  
`OpenProject`: pick folder containing `itemstudio.json` → `Load`.  
`SaveProject`: `CurrentProject.Save()`.

- [ ] **Step 4: `MainWindow.xaml` layout**

Simple non-dashboard layout: top menu (File), left tool strip, center viewport host placeholder, right tabs (Stats / Validation / Project). Brand the window title **RSPS Item Studio**.

- [ ] **Step 5: Build App (Windows) / build libraries (Linux)**

```bash
dotnet test
dotnet build src/RspsItemStudio.App/RspsItemStudio.App.csproj || true
```

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: WPF shell with create/open/save project workspace"
```

---

### Task 8: Stat editor + validation report UI

**Files:**
- Create: `src/RspsItemStudio.App/Views/StatEditorView.xaml(+cs)`
- Create: `src/RspsItemStudio.App/Views/ValidationReportView.xaml(+cs)`
- Create: `src/RspsItemStudio.App/ViewModels/ItemDefinitionViewModel.cs`
- Create: `src/RspsItemStudio.App/ViewModels/ValidationViewModel.cs`

**Interfaces:**
- Consumes: `ItemDefinitionDocument`, `ItemProjectValidator`
- Produces: two-way bound stats editor; Validate button fills issue list and writes `last-report.json`

- [ ] **Step 1: `ItemDefinitionViewModel` wraps `ItemDefinitionDocument` with `INotifyPropertyChanged` for Name, Examine, Slot, Flags, Bonuses, Requirements, WeightKg**

- [ ] **Step 2: XAML form** — text fields + combo for slot + checkboxes for flags + numeric fields for bonuses (GroupBox sections: Identity, Flags, Offensive, Defensive, Other)

- [ ] **Step 3: `ValidationViewModel.Run()` calls validator, maps issues to ObservableCollection, calls `SaveValidationReport`

- [ ] **Step 4: Wire tabs into `MainWindow`

- [ ] **Step 5: Manual test checklist (document in PR): New project → leave name empty → Validate → see `NAME_EMPTY`; set name → Validate → error cleared; missing model still errors

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: item stat editor and validation report UI"
```

---

### Task 9: Veldrid viewport + mesh preview

**Files:**
- Create: `src/RspsItemStudio.Rendering/**`
- Create: `src/RspsItemStudio.App/Views/ViewportHost.xaml(+cs)`
- Modify: `MainWindow.xaml`, `MainViewModel` import command

**Interfaces:**
- Consumes: `StudioMesh`
- Produces: `VeldridViewportController.Attach(HwndSource hwnd)`, `LoadMesh(StudioMesh)`, `SetDisplayMode(...)`, camera orbit/pan/zoom via mouse

- [ ] **Step 1: Add Rendering project `net8.0-windows`; package references `Veldrid`, `Veldrid.StartupUtilities`, `Veldrid.SPIRV` (or hardcoded GL shaders if SPIR-V toolchain is heavy — prefer simple GLES/GL backend with GLSL)**

- [ ] **Step 2: Implement `ViewportCamera` (orbit yaw/pitch/distance, pan, view/proj matrices)

- [ ] **Step 3: Implement `VeldridViewportController` rendering grid + mesh with basic directional light; modes: Solid, SolidUntextured, Wireframe

- [ ] **Step 4: `ViewportHost` — `HwndHost` child; on Loaded create controller; forward mouse wheel/drag

- [ ] **Step 5: `ImportObjCommand` — `OpenFileDialog` filter `*.obj` → `ObjMeshImporter.Import` → write `inventory.mesh.json` + copy source to `models/source/` → `LoadMesh` on viewport → show import warnings in StatusText

- [ ] **Step 6: Build on Windows; on Linux skip with note in COMPATIBILITY.md

- [ ] **Step 7: Commit**

```bash
git commit -am "feat: Veldrid viewport with OBJ preview and camera controls"
```

---

### Task 10: Export staging command + M1 acceptance wiring

**Files:**
- Modify: `MainViewModel.cs` (`ExportStagingCommand`)
- Create: `src/RspsItemStudio.App/Services/IntegrationReportWriter.cs` (optional thin wrapper)
- Modify: `PROJECT_ROADMAP.md` (mark M1 tasks done/partial)
- Modify: `COMPATIBILITY.md`

**Interfaces:**
- Consumes: `ItemProjectValidator`, `OpenRuneAdapter.Cache.PackToStaging`
- Produces: blocked export when `HasErrors`; otherwise staging report shown in Validation tab / dialog

- [ ] **Step 1: Implement export flow**

```csharp
var report = _validator.Validate(project);
project.SaveValidationReport(report);
if (report.HasErrors) { StatusText = "Export blocked by validation errors."; return; }
var adapter = new OpenRuneAdapter();
var result = adapter.Cache.PackToStaging(new ExportStagingRequest {
    Project = project,
    Preset = project.ExportPresets.Presets.FirstOrDefault() ?? new ExportPreset()
});
StatusText = result.Message ?? (result.Value?.Summary ?? "Export finished.");
```

- [ ] **Step 2: Ensure `PackToLiveTree` is unreachable from UI in M1** (no menu item)

- [ ] **Step 3: Run full `dotnet test`**

- [ ] **Step 4: Update roadmap** — M1 foundation complete; next = Milestone 2 OpenRune definition/model verification

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: staging export gate with validation and OpenRune stub report"
```

---

## Milestone 1 acceptance checklist

- [ ] `dotnet test` passes for Core/Modeling/Definitions/Validation/Adapters
- [ ] On Windows: create project, import OBJ, see mesh in viewport, edit stats, validate, export staging shows honest OpenRune not-implemented/skipped report
- [ ] No live cache writes possible from UI
- [ ] `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md` present and accurate
- [ ] Spec M1 items 1–8 each map to completed tasks above

---

## Plan self-review

**Spec coverage (M1):**
1. App shell + workspace → Tasks 7–8  
2. 3D viewport → Task 9  
3. OBJ import → Tasks 4, 9  
4. Project structure → Task 2  
5. Stat editor → Tasks 2–3 defs + Task 8  
6. Validation report → Tasks 5, 8  
7. Adapter interfaces + OpenRune skeleton → Task 6  
8. Living docs → Tasks 1, 6, 10  

**Deferred (explicit in spec):** glTF, vertex editing, real OpenRune codecs, animation/effects editors, live cache pack.

**Placeholder scan:** none remaining; Veldrid locked; bonus range documented as `-200..200`.

**Type consistency:** `ItemProject`, `ItemDefinitionDocument`, `StudioMesh`, `AdapterResult<T>`, `ValidationReport`, adapter id `"openrune"` used uniformly.
