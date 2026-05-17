# Quickstart: storebro CLI

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/cli-contract.md](./contracts/cli-contract.md) | **Date**: 2026-05-17

A 5-minute walkthrough of the `storebro` command. Assumes FreeCAD 1.1+ on PATH (for `build`) and `freecad-storebro >= 1.0.0`.

---

## 1. Build a complete Storebro

```bash
storebro build --out boat.FCStd
```

Expected output:

```
wrote fcstd to /Users/you/boat.FCStd (192884 bytes, SHA-256 4a1e9b2c8d3f...)
```

Open `boat.FCStd` in FreeCAD: hull + deck + Alternativ3 interior, all parametrically editable.

---

## 2. Pick a different layout

```bash
storebro build --layout Alternativ1 --out boat_alt1.FCStd
storebro build --layout Alternativ5 --out boat_daycruiser.FCStd
```

---

## 3. Export to a non-FreeCAD format

```bash
storebro build --format step --out boat.step
storebro build --format stl --out boat.stl
storebro build --format stl --out boat_fine.stl --tessellation 0.0005
```

---

## 4. List available layouts

```bash
storebro list-layouts
```

Output (tab-separated):

```
Alternativ1	docs/references/Alternativ1.JPG	4 compartments — live-aboard
Alternativ2	docs/references/Alternativ2.JPG	4 compartments — fly-bridge access
Alternativ3	docs/references/Alternativ3.JPG	4 compartments — canonical RC34
Alternativ4	docs/references/Alternativ4.JPG	4 compartments — extended salon
Alternativ5	docs/references/Alternativ5.JPG	3 compartments — day-cruiser
```

---

## 5. Show diagnostic info

```bash
storebro info
```

Output:

```
freecad-storebro version: 1.0.0
Python version: 3.11.11
Platform: Darwin arm64
FreeCAD detected: 1.1.0
FreeCAD supported range: >=1.1,<2.0
```

---

## 6. Custom YAML layout

```bash
# my_layout.yaml as documented in spec 004
storebro build --layout ./my_layout.yaml --out custom_boat.FCStd
```

---

## 7. Error handling

```bash
storebro build --layout BogusLayout --out /tmp/x.FCStd
```

Exit code 1, stderr:

```
error: InteriorParameterError: in BogusLayout — layout: must be one of the five canonical names or a path to a valid YAML file
```

```bash
storebro build --out /tmp/x.FCStd --no-overwrite
# If /tmp/x.FCStd already exists, exit code 1:
error: ExportInputError: target_path — target exists and overwrite=False (got: /tmp/x.FCStd)
```

```bash
storebro --debug build --layout BogusLayout --out /tmp/x.FCStd
```

With `--debug`, full Python traceback on stderr; same exit code.

---

## 8. Piping and scripting

```bash
# Build all five layouts in a loop
for layout in Alternativ1 Alternativ2 Alternativ3 Alternativ4 Alternativ5; do
    storebro build --layout "$layout" --out "/tmp/boat_${layout}.FCStd"
done

# Grep the available layout names
storebro list-layouts | awk -F'\t' '{print $1}'

# Extract just the FreeCAD version
storebro info | grep '^FreeCAD detected:'
```

---

## What's NOT in this CLI (v1.0)

- `storebro import` / `validate` / `serve` / `repl` / `gui` — out of scope
- `--format all` — out of scope (run `storebro build` four times for four formats)
- Configuration files (`~/.config/storebro.toml`) — out of scope
- Hull / deck parameter overrides (`--loa`, `--beam`) — out of scope (custom-parametrize via the Python API)
- `--json` machine-parseable output — out of scope
- Auto-launching FreeCAD GUI on built files — out of scope

---

## Where to next

- **Verify your install**: `storebro info`
- **Build the canonical boat**: `storebro build --out boat.FCStd`
- **Read the full contract**: [contracts/cli-contract.md](./contracts/cli-contract.md)
- **Read the formal spec**: [spec.allium](./spec.allium)
