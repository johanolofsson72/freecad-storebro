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

## Output verbosity (token discipline)

Default `dotnet` output is chatty — every test name, every restore step, every assembly load. The model pays for all of it. Use quiet flags by default and only escalate when debugging:

- `dotnet test --logger "console;verbosity=minimal"` — prints only failed tests + summary
- `dotnet test --logger "console;verbosity=normal"` — escalate when a specific test needs investigation
- `dotnet build --verbosity quiet` (or `-v q`) — only warnings and errors
- `dotnet restore --verbosity quiet`
- For Playwright via `dotnet test`: combine with `--logger` above; Playwright traces are independent and stay verbose unless `PWDEBUG=0` and `--reporter=line` are passed to the underlying runner.

When a test fails and the minimal output doesn't show enough context, re-run only the failing test with normal verbosity: `dotnet test --filter "FullyQualifiedName~ClassName.TestName" --logger "console;verbosity=normal"`. Do not rerun the entire suite at higher verbosity to investigate one failure.
