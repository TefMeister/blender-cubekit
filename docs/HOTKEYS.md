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

## Painting cubes with the palette

The palette lives in the **CubeKit** tab, on the right side of the 3D view.

1. With the mouse over the 3D view, press **N** if the side panel is hidden.
2. Click the **CubeKit** tab on the panel's right edge.
3. Scroll down to the **colours** box.

To paint:

1. Press **Tab** and pick cubes with the left mouse (**F** chooses sides only or whole cubes).
2. Click the **brush button** next to a colour. The picked sides or cubes take that colour.

Click a colour swatch itself to change that colour. **+** at the top of the box adds a colour (it
copies the picked side's colour when something is picked); **x** removes one. The palette is saved
with the file. Ctrl+Z undoes a paint.

## Keys the add-on adds

Object mode (before Tab):

| Key | What it does |
| --- | --- |
| **L** (mouse over a cube) | Picks exactly that cube: selects the object, enters edit mode, selects the one cube under the mouse. |
| **Tab** | Into cube editing with **nothing picked**, so the cubes show and can be picked. Tab again comes out. |

## Moving around: always on, in every mode

No mode to switch on: the 3D view moves like a game (asked for on 2026-10-03).

| Key | What it does |
| --- | --- |
| **W A S D** | Move forward, left, back, right, the way you are facing. |
| **Z / X** | Lower / raise. |
| **Shift** | Faster, while held. |
| **Middle mouse** held | Turn your head: look around from where you stand. |
| **Wheel** | Blender's own zoom. |

Those keys did other jobs in Blender before; they are now here:

| Key | What it does now | What used to do it |
| --- | --- | --- |
| **F7** | Pick everything / nothing | A |
| **F8** | Scale | S |
| **F9** | The shading wheel | Z |
| **F10** | Blender's spin-the-model view (hold and move the mouse) | middle mouse |
| **Delete** | Delete | X (Delete already did it) |

Blender's own walk mode (Shift + the key left of 1) is not needed any more. Its Tab switch for
falling is moved to **F12**, and it starts with falling off.

Edit mode (after Tab), asked for on 2026-10-03:

| Key | What it does |
| --- | --- |
| **Left mouse** | The picking brush. A click picks the cube (or side) under the mouse; hold and sweep to pick more. Turn the **wheel** while holding to make the brush bigger or smaller. An orange circle shows it. |
| **Right mouse** | Held: the same brush, un-picking. A red circle shows it. |
| **F** | Sides only, or whole cubes. |
| **E** | Adds a cube outside every picked side, in that side's colour. The new cube's outer side becomes the picked one, so **E E E** builds a row of three. Needs sides picked, so it knows which way. |
| **Q** | Removes the cube behind every picked side; the next cube inward becomes picked, so **Q Q** digs two deep. With whole cubes picked, removes those cubes. |
| **R** | The whole model in view, at a sensible distance. |
| **Ctrl + wheel** | Brush circle bigger or smaller. The circle follows the mouse in edit mode, so its size is always visible. |
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
