# Buttons and keys

Everything the CubeKit add-on (version 0.9.0) adds to Blender. The add-on puts a **CubeKit** tab in
the 3D view's side panel: with the mouse over the 3D view, press **N** if the panel is hidden, then
click **CubeKit** on the panel's right edge.

Every change can be undone with **Ctrl + Z**.

## The CubeKit tab, top to bottom

### Cube size, this file only

A row of buttons: the project's starting size, half, and quarter (**3.4 mm · 1.7 mm · 0.85 mm** for
the Ashes 2063 weapons). The lit button is this file's size.

- **A smaller size:** every cube becomes 8 cubes of half the size, in the same place and colours.
  Detail painted on split sides lands on the new smaller sides.
- **A bigger size:** every 8 small cubes become one again. A big cube comes back where at least half
  of its 8 small cubes are: a single dug-out small cube is filled in, a mostly dug-out block
  disappears. Fine colour detail is kept as far as the bigger sides can hold it.
- It asks before it acts, changes **only the open file**, and never goes bigger than the starting
  size. The starting size is in the project's `cube_project.py`.

### The three buttons

| Button | What it does |
| --- | --- |
| **Colours on** | Shows the model flat and unlit with its colours: exactly what the game shows. |
| **Every cube on its own** | Gets a model ready for cube editing: cuts merged strips back into single cubes and works out which cubes are solid inside, so cubes can be picked, added, removed and coloured. Works on the selected parts, or on everything when nothing is selected. |
| **Save pick copy** | Saves the scene as `<name>_pick.blend` beside the open file. The original is what the game export reads, so it is never overwritten with the editing version. |

### picking

| Button | What it does |
| --- | --- |
| **whole cubes (F) / sides only (F)** | What a pick grabs and what a colour paints. The **F** key switches it. |
| **brush size (Ctrl + wheel)** | How big the picking brush circle is, in pixels. |
| **Split finer (C)** | The **C** key: see the edit-mode keys below. |
| **Join (Shift C)** | The **Shift + C** key: see below. |

### colours

Laid out like Microsoft Paint's palette: two rows of Paint's colours, then your own underneath.

- **Click a colour square:** whatever is picked takes that colour at once (sides or whole cubes,
  as **F** is set). The colour also goes into the **big square** at the top: the colour in hand.
- **Big square:** click it to fine-tune the colour in hand.
- **Add to my colours:** puts the colour in hand into a new square at the end. The palette grows
  downwards, ten to a row.
- **Change this colour:** gives the last clicked square (orange outline) the colour in hand.
- **Remove this colour:** takes the last clicked square away. **Ctrl + click** a square does the same.
  Every square can be changed or removed, Paint's too.
- **Number keys 1 to 0** (the row above the letters, not the numpad):
  - **Click a colour square, then press a number** with the mouse still over the side panel: that
    number now means that colour, and is drawn in the square's corner. 1 to 0 start as Paint's top
    row.
  - **Hover a cube in edit mode and press a number:** paints the side under the mouse with that
    colour, or the whole cube when **F** is on whole cubes. Nothing needs picking first, and what is
    picked stays picked.

The palette and the number keys are saved with the file.

### The reminder lines

The bottom of the tab repeats the main keys, so they are always in view.

## Keys

### Object mode (before Tab)

| Key | What it does |
| --- | --- |
| **L** (mouse over a cube) | Picks exactly that cube: selects the part, goes into edit mode and picks the one cube under the mouse. |
| **Tab** | Into cube editing with **nothing picked**, so the cubes show and can be picked. **Tab** again comes out. |

### Edit mode (after Tab)

| Key | What it does |
| --- | --- |
| **Left mouse** | The picking brush. A click picks the cube (or side) under the mouse; hold and sweep to pick more. An orange circle follows the mouse and shows its size. |
| **Right mouse** held | The same brush, un-picking. A red circle shows it. |
| **Ctrl + wheel** | Brush circle bigger or smaller. (Turning the wheel while holding the left mouse does it too.) |
| **Alt + A** | Un-pick everything (Blender's own). |
| **F** | Sides only, or whole cubes. |
| **E** | Adds a cube outside every picked side, in that side's colour. The new cube's outer side becomes the picked one, so **E E E** builds a row of three. Needs sides picked, so it knows which way. |
| **Q** | Removes the cube behind every picked side; the next cube inward becomes picked, so **Q Q** digs two deep. With whole cubes picked, removes those cubes. |
| **C** | Split a side for fine detail: plain, then 4 squares, then 16, then back to 4, and so on. Each square is picked and painted on its own. Colours painted at 16 stay when you go back to 4: a quarter holding finer detail keeps showing it, and is picked and painted as one quarter. With whole cubes picked, every outside side of those cubes is split. The cube keeps its size. |
| **Shift + C** | Joins a split side back into one square, in its most common colour. |
| **1 to 0** (mouse over a cube) | Paints with that key's colour (see the colours section above). |
| **R** | The whole model in view, at a sensible distance. |
| **F5** | Blender's plain click-select (what the left mouse did before). |
| **F6** | The edit-mesh menu (what the right mouse did before). |
| **Space** | Blender's own: play and stop the animation. |

### Moving around: always on, every mode

No mode to switch on: the 3D view moves like a game.

| Key | What it does |
| --- | --- |
| **W A S D** | Move forward, left, back, right, the way you are facing. |
| **Z / X** | Lower / raise. |
| **Shift** | Faster, while held. |
| **Middle mouse** held | Turn your head: look around from where you stand. |
| **Wheel** | Zoom (Blender's own). |

### Where Blender's own keys went

Those movement keys did other jobs in Blender; the jobs are now here:

| Key | What it does now | What used to do it |
| --- | --- | --- |
| **F7** | Pick everything / nothing | A |
| **F8** | Scale | S |
| **F9** | The shading wheel | Z |
| **F10** | Blender's spin-the-model view (hold and move the mouse) | middle mouse |
| **Delete** | Delete | X |
| **F12** (inside Blender's walk mode) | Falling on / off | Tab |

Blender's own walk mode (Shift + the key left of 1) is not needed any more; it starts with falling
off.

## Blender's own keys still worth knowing

| Key | What it does |
| --- | --- |
| **N** | Show or hide the side panel with the CubeKit tab. |
| **Numpad 1 / 3 / 7** | Look from the front, the side, the top. **Ctrl** with any of them looks from the opposite side. |
| **Numpad .** | Zoom onto what is picked. |
| **Home** | Zoom out to show everything. |
| **Ctrl + Z** | Undo. **Ctrl + Shift + Z** redo. |
| **Shift + Left arrow** | Jump to the first frame of the animation. |

## Where edits go

Picking, painting, adding, removing and splitting change the **editing copy** (`<name>_pick.blend`)
directly, and are saved with it. Turning an edited copy back into the game's model is not built yet,
so edits do not reach the game for now. Models are first built by script from their settings and
shape files; see [TUTORIAL.md](TUTORIAL.md).
