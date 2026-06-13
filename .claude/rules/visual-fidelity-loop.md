# Visual fidelity loop rule (build → screenshot → compare → fix → repeat)

FreeCAD 1.1.1 **is installed on this machine** (`/Applications/FreeCAD.app`). Therefore geometry is
**not** "the maintainer's problem to eyeball later" — Claude builds the model, opens it in FreeCAD,
screenshots it, and compares it against the reference Storebro images itself. A spec that changes
visible geometry is **not done** until the screenshot visually matches the reference.

## The contract (BLOCKING — for any spec that changes visible geometry)

After implementation and the normal gates (pytest / ruff / mypy), and before the spec is declared
done / committed / register-ticked, Claude MUST run the visual loop:

1. **Build the model in FreeCAD** headlessly via `freecadcmd` (see "How to drive FreeCAD" below) —
   the actual `.FCStd`, the variant/layout the spec touched.
2. **Open it in the FreeCAD GUI and screenshot it** — a side elevation AND a 3/4 (axonometric)
   view, exterior silhouette (hide construction geometry + interior for the silhouette shot).
3. **Compare against the reference images** in `docs/references/` — primarily
   `storo34_side_lines.png` (side line drawing) and `Alternativ1–5.JPG` (layout photos). Look at the
   actual pixels: hull shape/sheer/flare, superstructure proportions, window layout, stance.
4. **If it does not look right, fix the geometry and repeat from step 1.** "Right" means the
   silhouette and proportions read as the reference Storebro RC34, not an estimate-grade placeholder.
   Keep iterating until the screenshot matches or until a genuine architecture decision/blocker
   needs the user (then surface it with `AskUserQuestion`).
5. **Only then run the `requires_freecad` test tier** (`uv run` can't import FreeCAD — run pytest
   under FreeCAD's bundled Python, see below) and proceed to commit / register tick.

This loop is part of the per-spec pipeline, alongside `/tla` and the other gates. It does not replace
the unit gates — it is the visual-truth gate on top of them.

## How to drive FreeCAD (this machine)

FreeCAD's bundled Python is separate from the project `.venv` — that is why `uv run python -c
"import FreeCAD"` fails. Use the bundled interpreter:

- **Headless build / library calls / geometry logic:**
  `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd <script.py>`
  with `sys.path.insert(0, "<repo>/src")` at the top of the script. PyYAML is present in the bundle.
  Pass arguments via environment variables (`freecadcmd` does not forward `argv` reliably).
- **GUI screenshot:** `/Applications/FreeCAD.app/Contents/MacOS/FreeCAD <script.py>`. The script must
  defer the capture into the event loop and force-exit, or the app hangs / captures a blank frame:
  - open the doc, set `ViewObject.Visibility` (show only the solids you want; hide
    `Sketcher::SketchObject`, `PartDesign::Plane`, `App::Origin*`, and `Interior*` for a clean
    silhouette),
  - schedule the capture with `QtCore.QTimer.singleShot(~5000, shot)` so it runs after the 3D view
    has rendered (a capture fired immediately returns a blank white PNG),
  - inside `shot()`: set the view (`viewFront` / `viewAxonometric`), `fitAll()`, call
    `FreeCADGui.updateGui()` a few times (warm-up), then `view.saveImage(png, w, h, "White")`,
  - end with `os._exit(0)` (a normal close pops a "save changes?" dialog and hangs to timeout).
  - Wrap the launch in `timeout 90 ...`. The `3DconnexionNavlib` dlopen error in the log is benign.
- **`requires_freecad` tests:** run pytest under the bundled Python (install pytest into it once, or
  invoke `freecadcmd` with a script that calls `pytest.main([...])`). These are no longer deferred —
  run them and report real pass/fail.

## What this rule forbids

- Declaring a geometry spec "done" or "ready to tag" having only run unit tests, with the visual
  check deferred to "the maintainer's pre-tag step." FreeCAD is here; do the check.
- Claiming a render succeeded without actually looking at the PNG (a blank white frame is the default
  failure mode — open the image and verify there is geometry in it).
- Calling the model faithful when the screenshot plainly does not match the reference. Report the gap
  honestly and keep fixing.

## Honesty clause

Visual fidelity is iterative and the current model is far from the reference. This rule does not
require reaching 100% in one pass — it requires **running the loop every time, looking at the
result, and continuing to close the gap** rather than declaring victory on green unit tests alone.
When the remaining gap needs a structural decision (hull reshape, superstructure redesign), surface
it; do not silently ship a placeholder as if it were faithful.

## Why this rule exists

The whole project exists to produce a *reference-faithful* (constitution IV) parametric RC34. For 31
specs the visual check was deferred because FreeCAD was assumed unavailable in the agent
environment. It is available. Deferring the one check that actually measures the project's reason for
existing is the single biggest quality hole — this rule closes it.
