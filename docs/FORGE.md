# Forge: cube models in mixed sizes, written as code

Forge is a second way to make cube models, next to the add-on. The add-on is for shaping by hand in Blender. Forge
builds a whole model from a short Python file with no Blender window open, so a full set of weapons can be made in
one go and then refined together in Blender.

Asked for by Tefa on 2026-10-19: *"use different cube sizes to really emphasize cracks and cuts but also little
screws and corners and the design of these video game weapons, so they really have distinct shapes."*

## Three cube sizes on one grid

- **Whole cubes** (`cube_size.VOXEL_M`, 3.4 mm) for the bodies.
- **Half cubes** (1.7 mm) where a surface curves or a corner is bevelled, so edges step down in finer pixels.
- **Quarter cubes** (0.85 mm) for screw heads, cut lines, cracks, scratches, stamped letters and small parts.

All three sit on one fixed grid, as in the add-on's small cubes (`edit_small.py`). Every cube has an id, and its
small brightness wobble comes from that id, so a big cube with a notch cut out of it still reads as one cube.

## Files

| File | What it does |
| --- | --- |
| `forge.py` | The model: placing cubes, shapes (`box`, `cyl`, `ball`, `prism`), surface work (`groove`, `screw`, `decal`, `crack`, `scratches`), weathering (`wear_edges`, `grime`), and the outside faces. No Blender. |
| `forge_parts.py` | Gun pieces and paints shared by every gun: barrels, triggers, guards, sights, wood grain, rust. |
| `forge_bl.py` | Turns a model into Blender objects (one per moving part, one small palette texture, unlit like every cubekit model) and renders previews. |
| `forge_run.py` | Runs inside Blender: builds one design file, saves the `.blend`, renders. |
| `forge_make.py` | The one command: `python forge_make.py <blend folder> <render folder> <design.py> ...` |
| `forge_sheet.py`, `forge_compare.py` | Put the previews on one sheet per model, or one view of several models side by side. |

## A design file

A design is a Python file with a `build()` that returns a `forge.Model`. The numbers that set its shape sit at the
top as named settings. Axes as in every cubekit gun: x runs from the back to the muzzle, y is width (+ is the gun's
left side), z is up. Positions are in whole cubes and may be fractions.

The weapon designs live in their game's repo: `ashes-2063-weapons/forge/` and `brutal-doom-3d-guns/forge/`.

## Not yet

- The game exporters (`gz_world.py`, the kit's `gz_export`) do not read forge models yet.
- Hands are not on the forge guns yet.
