# Spec register

Order of execution. Tick when done. Append new specs to the end unless renumbering is justified.

## Specs

- [x] 001 — hull-module — full track — Parametric Storebro hull geometry (LOA, beam, draft, deadrise, sheer, transom) as a FreeCAD Body
- [x] 002 — export-module — full track — Deterministic .FCStd / STEP / STL / BREP writers with byte-identical reproducibility
- [x] 003 — deck-module — full track — Deck plate, cabin trunk, windshield, hardtop, railings mounted on the hull
- [x] 004 — interior-module — full track — Cabins, galley, heads, salon driven by canonical Alternativ1–5 YAML fixtures
- [x] 005 — cli-module — full track — `storebro build/list-layouts/info` CLI composing hull + deck + interior + export
- [ ] 006 — partdesign-hull-upgrade — full track — Refactor hull from `Part::Loft` + `Part::Mirroring` into a clean `PartDesign Body` with editable `Pad/Loft` feature stack (closes v0.1.0-alpha caveat from spec 001)

## Register history

- 2026-05-17 — initial register, 5 modules from PROJECT-BRIEF.md / constitution v1.0.0; order = build-dependency order (hull blocks deck/interior; export unblocks visual verification of hull alpha; cli composes everything last)
- 2026-05-17 — register complete; spec 005 closes the v1.0.0 milestone (all four library modules + CLI composer)
- 2026-05-17 — register extended for v1.1+: spec 006 added (PartDesign hull upgrade) as the highest-value follow-on; addresses the v0.1.0-alpha geometry caveat that has been tracked since spec 001
