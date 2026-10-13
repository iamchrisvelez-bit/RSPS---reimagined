# RSPS Item Studio

Windows desktop suite for authoring custom RuneScape private-server items: model/import, materials, animations, effects, definitions, validation, and revision-specific export. **OpenRune-first** with pluggable adapters for other revisions.

## Requirements

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- Windows (WPF shell; Milestone 1+)

## Build and test

From the repository root on **Linux or macOS** (libraries and tests only):

```bash
dotnet test
```

On **Windows**, build and run the WPF shell as well:

```bash
dotnet build src/RspsItemStudio.App/RspsItemStudio.App.csproj
dotnet test
```

Run a single test project:

```bash
dotnet test tests/RspsItemStudio.Tests/RspsItemStudio.Tests.csproj
```

## Run the application (Windows)

```bash
dotnet run --project src/RspsItemStudio.App
```

## Documentation

- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) — milestones and status
- [ARCHITECTURE.md](ARCHITECTURE.md) — modules and data flow
- [COMPATIBILITY.md](COMPATIBILITY.md) — OpenRune focus, Rev317 stub, known limits

Design spec: [docs/superpowers/specs/2026-10-13-rsps-item-studio-design.md](docs/superpowers/specs/2026-10-13-rsps-item-studio-design.md)
