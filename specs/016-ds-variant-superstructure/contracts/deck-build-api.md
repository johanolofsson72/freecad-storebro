# Contract — Deck build API (DS variant)

The public contract this feature adds/changes. Library API + CLI command schema.

## Library: `storebro.build_deck`

### New input

- `superstructure_variant: Literal["standard", "ds"] = "standard"` (keyword-only).
- `parameters_deckhouse: DeckhouseParameters | None = None` (keyword-only).

### Behavior contract

| Input | Guarantee |
|---|---|
| `superstructure_variant` omitted / `"standard"` | Output byte-identical to the pre-feature deck build. `deckhouse is None`; `cabin_trunk`/`windshield`/`hardtop`/`hardtop_pillars` populated. |
| `superstructure_variant="ds"` | Builds one `Deckhouse` solid; `cabin_trunk`/`windshield`/`hardtop`/`hardtop_pillars`/`cabin_windows` are `None`; `deckhouse` populated, `Solids==1`, `isValid()`. Deck plate, railings, all hardware populated. |
| `superstructure_variant="ds"` + `parameters_superstructure=...` | Raises `DeckParameterError` before any FreeCAD call (contradictory). |
| `superstructure_variant` not in `{standard, ds}` | Raises `DeckParameterError` before any FreeCAD call. |
| `parameters_deckhouse` invalid (any field/cross-field) | Raises `DeckParameterError` before any FreeCAD call. |
| `parameters_deckhouse` exceeds hull (length>LOA, width>beam) | Raises `DeckParameterError` before any FreeCAD call. |
| FreeCAD failure mid-DS-build | Full rollback (zero residual bodies); raises `DeckConstructionError`. |
| hull is None / null Shape | Raises `DeckParameterError` (unchanged). |

### Return contract (`Deck`)

- `deck.superstructure_variant` == the resolved variant string.
- Exactly one of (`deck.deckhouse`) xor (the four open-flybridge slots) is populated, per variant.
- `deck.railings` and all five hardware wrappers are non-None in both variants.
- The hull passed in is unchanged (no boolean mutation): `hull.body.Shape` identity/volume preserved.

## CLI: `storebro build`

### New flag

```
--superstructure {standard,ds}   Superstructure variant. Default: standard.
```

### Command contract

| Invocation | Result |
|---|---|
| `storebro build --layout 3 --out boat.FCStd` | Standard variant (default), exit 0. |
| `storebro build --superstructure standard ...` | Standard variant, exit 0. |
| `storebro build --superstructure ds ...` | DS variant deckhouse, exit 0. |
| `storebro build --superstructure bogus ...` | argparse error, exit != 0, usage message names valid choices. |

The flag composes with existing flags (`--layout`, `--engine-count`, `--no-colors`, `--no-propulsion`). DS variant + any interior layout is valid (interior is variant-agnostic this spec).

## Backward compatibility

- All existing positional/keyword `build_deck` call sites compile and produce identical output (new params are keyword-only with defaults).
- `Deck` field-type widening (four slots → Optional) is source-compatible for standard-mode readers (slots remain populated in standard mode).
- Public surface grows by three names (`DeckhouseParameters`, `DsWindowParameters`, `Deckhouse`) → MINOR version bump, no migration needed.
