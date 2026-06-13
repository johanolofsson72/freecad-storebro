# Public API Contract Delta — windshield crown

The library's public surface for the windshield is the `WindshieldParameters` dataclass (exported in
`deck.py.__all__`). This spec makes a single **additive, backward-compatible** change.

## Added

```python
@dataclass(frozen=True)
class WindshieldParameters:
    ...
    crown_height: float = 60.0   # NEW — mm, rise of the top edge at the centerline (Y=0).
                                 #       0.0 = flat top (pre-030 byte-identical). Valid: [0, top_width/2).
```

- **Default 60.0**: the windshield ships crowned. This changes the default windshield geometry
  (and therefore default-build signoff hashes) — expected for a geometry spec, as with specs
  007/008/020. Documented in the CHANGELOG as a MINOR (additive field) with a visible-geometry note.
- **`crown_height=0.0`**: reproduces the pre-030 flat-top windshield byte-for-byte.

## Unchanged (no breaking change)

- All existing `WindshieldParameters` fields, names, defaults, and validation.
- The `Windshield` wrapper type: `body`, `rake_degrees`, `glass_pane` — same shape, same labels.
- `WindshieldGlazingParameters`, the frame opening, and the glass pane behaviour.
- `_build_windshield` signature (internal) — only its body changes.
- Render role / material assignment (spec 015).

## Versioning

MINOR bump (additive optional field with a back-compat sentinel). Per the project's semver
discipline: `1.13.2 → 1.14.0`.

## Construction errors (fail-fast)

`WindshieldParameters(crown_height=<bad>)` raises `DeckParameterError` when `crown_height` is:

- negative, or
- `≥ top_width / 2`, or
- non-finite (NaN / ±inf — via the spec 029 `_reject_nonfinite_floats` guard).
