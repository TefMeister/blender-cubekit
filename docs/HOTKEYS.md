# Buttons and keys

Everything the CubeKit add-on adds to Blender, and the handful of Blender's own keys this way of
working leans on. The add-on puts a **CubeKit** tab in the 3D view's sidebar (press **N** to show
the sidebar if it is hidden).

## The CubeKit tab

| Button | What it does |
| --- | --- |
| **Colours on** | Shows the model flat and unlit with its colours, which is exactly what the game shows. |
| **Every cube on its own** | Gets a model ready for cube editing: cuts merged strips back into single cubes and works out which cubes are solid inside, so cubes can be picked, added, removed and coloured. Works on the selected objects, or on everything when nothing is selected. |
| **Save pick copy** | Saves the scene as `<name>_pick.blend` beside the open file. The original file is what the game export reads, so it is never overwritten with the editing version. |
| **sides only / whole cubes** | What a pick grabs and what a colour paints. **F** switches it. |
| **brush size** | How big the picking brush is. The mouse wheel changes it while picking. |
| **colours** | The palette. Click a swatch to change it, the brush button beside it paints the picked sides (or whole cubes) with it, **+** adds a colour (the picked side's colour, if something is picked), **x** removes one. The palette is saved with the file. |

The tab also shows the project's cube size, read from `cube_size.py`.

## Keys the add-on adds

Object mode (before Tab):

| Key | What it does |
| --- | --- |
| **L** (mouse over a cube) | Picks exactly that cube: selects the object, enters edit mode, selects the one cube under the mouse. |

Edit mode (after Tab), asked for on 2026-10-03:

| Key | What it does |
| --- | --- |
| **Left mouse** | The picking brush. A click picks the cube (or side) under the mouse; hold and sweep to pick more. Turn the **wheel** while holding to make the brush bigger or smaller. An orange circle shows it. |
| **Right mouse** | Held: the same brush, un-picking. A red circle shows it. |
| **F** | Sides only, or whole cubes. |
| **E** | Adds a cube outside every picked side, in that side's colour. The new cube's outer side becomes the picked one, so **E E E** builds a row of three. Needs sides picked, so it knows which way. |
| **Q** | Removes the cube behind every picked side; the next cube inward becomes picked, so **Q Q** digs two deep. With whole cubes picked, removes those cubes. |
| **R** | The whole model in view, at a sensible distance. |
| **F5** | What the left mouse did before: Blender's plain click-select. |
| **F6** | What the right mouse did before: the edit-mesh menu. |
| **Space** | Blender's own: play and stop the animation. |

Every edit can be undone with **Ctrl+Z**.

## Blender keys worth knowing

| Key | What it does |
| --- | --- |
| **Tab** | In and out of edit mode. |
| **N** | Show or hide the sidebar with the CubeKit tab. |
| **Z** | The shading wheel (Colours on does the same thing with one click). |
| **Numpad 1 / 3 / 7** | Look from the front, the side, the top. **Ctrl** with any of them looks from the opposite side. |
| **Numpad .** | Zoom onto what is selected. |
| **Home** | Zoom out to show everything. |
| **Middle mouse drag** | Turn the view. **Shift** + drag slides it, the wheel zooms. |
| **X** | Delete what is selected (in edit mode: the picked cube's faces). |
| **Ctrl+Z** | Undo. |
| **Space** | Play and stop the animation. **Shift+Left** jumps to the first frame. |

## What a picked cube is for

Picking tells you *which* cube you are looking at. The model itself is built by a script from its
settings and shape files, so a change is made there and the model rebuilt; the pick is how a cube is
pointed at ("this one, two to the left of it, one up"). Deleting or moving cubes by hand in Blender is
fine for trying something out, but it is lost at the next build. See
[TUTORIAL.md](TUTORIAL.md) for the loop.
