# Phase 1 Data Model — Interior Contoured Fittings

Additive, defaulted, validated fields on the furniture dataclasses (mm units).
`contoured=True` default; `False` reproduces the spec 012/013 box.

## BerthParameters (+)
| Field | Default | Rule |
|---|---|---|
| `contoured` | `True` | — |
| `cushion_segments` | `2` | `>= 1` |
| `seam_gap` | `15.0` | `>= 0` |
| `cushion_fillet` | `25.0` | `> 0` |
| `buttons_per_row` | `4` | `>= 0` |
| `button_rows` | `2` | `>= 0` |
| `button_radius` | `35.0` | `> 0` |
| `piping` | `True` | — |
| `piping_radius` | `12.0` | `> 0` |
| `fold_creases` | `2` | `>= 0` |

## SalonParameters (+)
| `contoured` `True`; `seat_fillet` `25.0` (`>0`); plus the same fabric fields
(`buttons_per_row` 6, `button_rows` 1, `button_radius` 35, `piping` True,
`piping_radius` 12, `fold_creases` 2). |

## HeadParameters (+)
| `contoured` `True`; `toilet_fillet` `30.0` (`>0`); `bowl_radius` `170.0` (`>0`);
`faucet` `True`; `faucet_height` `200.0` (`>0`). |

## GalleyParameters (+)
| `contoured` `True`; `edge_fillet` `12.0` (`>0`); `fascia` `True`;
`fascia_thickness` `18.0` (`>0`). |

## BulkheadParameters (+)
| `contoured` `True`; `corner_fillet` `40.0` (`>0`); `doorway` `True`;
`doorway_width` `600.0` (`>0`); `doorway_height` `1500.0` (`>0`). |

## Helpers (interior.py)
- `_rounded_box_shape(dx, dy, dz, origin, radius, edges="vertical"|"all")` → filleted Part shape (clamped radius, fallback to un-filleted on failure).
- `_cushion_shape(dx, dy, dz, origin, params)` → rounded box + cut-sphere buttons + fused piping welt + cut fold grooves; returns a single-solid shape or the plain box on gate failure.
- `_finalize(target_doc, added, name, shape, fallback_box_args)` → wrap as Part::Feature; if `len(shape.Solids)!=1 or not isValid()`, build the fallback box instead (FR-007).

## Invariants
- Each contoured piece `Solids == 1 && isValid()` or deterministic box fallback (FR-007).
- `contoured=False` byte-identical to specs 012/013 (FR-008).
- All ops byte-reproducible (FR-011).
