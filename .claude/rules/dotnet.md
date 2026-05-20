---
paths:
  - "**/*.cs"
  - "**/*.csproj"
---

# .NET code rules

- PascalCase for public members, camelCase for local variables.
- Prefix private fields with `_` (e.g., `_logger`).
- Use `var` only when the type is obvious from the right side.
- One class per file. Filename matches class name.
- File-scoped namespaces (`namespace X;`).
- Primary constructors for services with dependency injection.
- Use `record` for immutable data types.
- Never use `#region` — structure with classes and methods instead.
- Keep methods under 30 lines — extract when needed.
- Async/await: avoid async void, propagate CancellationToken.
- EF Core: avoid N+1 — use Include/ThenInclude, AsNoTracking() for reads.
- Keep `Program.cs` minimal — register services and middleware via extension methods (e.g., `AddApplicationServices()`, `UseApplicationMiddleware()`). No business logic in `Program.cs`.
- ALWAYS run `pkill -f dcpctrl || true` and `pkill -f "/absolute/path/to/src/<subproject>" || true` (one command per subproject) BEFORE `dotnet build`, `dotnet run`, or `dotnet test`. ALWAYS use full absolute paths — relative paths like `src/<subproject>` are FORBIDDEN because they can match and kill processes with the same name in other projects on the machine. Identify subprojects from the `src/` structure and `launchSettings.json` — NEVER kill all dotnet processes globally.
