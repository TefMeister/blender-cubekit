# Buttons and keys

Everything the CubeKit add-on adds to Blender, and the handful of Blender's own keys this way of
working leans on. The add-on puts a **CubeKit** tab in the 3D view's sidebar (press **N** to show
the sidebar if it is hidden).

## The CubeKit tab

| Button | What it does |
| --- | --- |
| **Colours on** | Shows the model flat and unlit with its colours, which is exactly what the game shows. Use it when the model looks grey or shaded. |
| **Every cube on its own** | Cuts the merged strips back into single cubes so that one cube can be picked. Works on the selected objects, or on everything when nothing is selected. Already-cut objects are left alone. |
| **Save pick copy** | Saves the scene as `<name>_pick.blend` beside the open file. The original file is what the game export reads, so it is never overwritten with cut-up cubes. |

The tab also shows the project's cube size, read from `cube_size.py`.

## Keys the add-on adds

Object mode (before Tab):

| Key | What it does |
| --- | --- |
| **L** (mouse over a cube) | Picks exactly that cube: selects the object, enters edit mode, selects the one cube under the mouse. |

Edit mode (after Tab), set up the way a game is played (asked for 2026-10-03):

| Key | What it does |
| --- | --- |
| **Left mouse** | Picks the cube under the mouse. One click = that cube only; **Shift** + click adds a cube. |
| **Right mouse** | Paint-select on or off. With it on, hold the left mouse and sweep over cubes to add them all. The CubeKit tab shows which is on. |
| **Space** | Walk around the model: **W A S D** move, the mouse looks, **Q** lowers you, **E** raises you, **Shift** goes faster. **Space** again (or Esc) stops. |
| **F5** | What the left mouse did before: Blender's plain click-select of a face, edge or vertex. |
| **F6** | What the right mouse did before: the edit-mesh menu. |

In edit mode **L** still works too: it is Blender's own "select linked under the mouse", which on a
cut-up model is exactly one cube.

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
