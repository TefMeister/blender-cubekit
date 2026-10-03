# Tutorial: your first cube model

This builds the mug in `examples/mug/` and then changes it, which is the whole loop: settings,
shape, build, look, pick, change, build again. Nothing here needs Blender knowledge beyond the keys
in [HOTKEYS.md](HOTKEYS.md).

## What you need

- **Blender 4.2 or newer.** The `blender` command below is Blender's own program file. On Windows it
  is usually `C:\Program Files\Blender Foundation\Blender <version>\blender.exe`; put that full path
  in quotes where the steps say `blender`.
- **This repo**, downloaded or cloned anywhere.
- **The add-on** installed: see the README's install steps.

## Step 1: build the mug

Open a terminal in the repo folder and run:

```
blender -b --factory-startup --python examples/mug/mug_build.py
```

`-b` means no window, `--factory-startup` means ignore your Blender settings so the result is the
same on every PC. It prints the cube counts and writes:

- `examples/mug/renders/three_quarter.png`: a picture of the mug.
- `examples/mug/mug.blend`: the model, ready to open.
- `examples/mug/mug_atlas.png`: the texture, every cube's colour in one picture.

Look at the picture first. That is the model as the game would show it: flat colours, no lighting.

## Step 2: open it and look around

Open `mug.blend` in Blender. If the mug looks grey, press **N** for the side panel, open the
**CubeKit** tab and click **Colours on**. Move around like in a game: **W A S D** to move, **Z** down,
**X** up, hold the **middle mouse** to look around, the **wheel** to zoom, **R** (in edit mode) to see
the whole model.

## Step 3: pick a cube

Click **Every cube on its own**, press **Tab**, and click any cube with the **left mouse**. It turns
orange: that is the picked cube. The **left mouse** picks more (hold and sweep), the
**right mouse** held un-picks, **Ctrl + wheel** sizes the brush, **Alt + A** un-picks everything and
**F** switches between whole cubes and single sides. **Tab** leaves edit mode. Click **Save pick copy** if you want to keep
this cut-up version to come back to; it is saved as `mug_pick.blend`, the original stays as built.

## Step 3b: paint a cube

Still in edit mode, open the **CubeKit** tab and scroll down to the **colours** box. Pick a cube or
two with the left mouse and click a colour square: the picked cubes take it. Or hover a cube and press
**1** to paint it with key 1's colour (black, to start with). **F** switches between painting one side
and the whole cube.

For finer detail, pick a side and press **C**: it splits into 4 squares, **C** again makes 16, each
painted on its own. **E** adds a cube on a picked side, **Q** digs one out. Everything is in
[HOTKEYS.md](HOTKEYS.md).

## Step 4: change something

Open `examples/mug/mug_settings.py` in any text editor. Every number has a name and a comment.
Try:

- `HEIGHT = 26` to `34`: a taller mug.
- `BAND = (17, 20)` to `(5, 8)`: the red band lower down.
- `"band": (190, 50, 45)` to `(45, 90, 190)`: a blue band.

Save, run the build command from Step 1 again, open the new `mug.blend` (or in Blender: **File >
Revert**). That loop, change a named number and rebuild, is how every model is made. The scripts are
the model; the `.blend` is just the latest output.

## Step 5: change the shape

Open `examples/mug/mug_build.py` and find `shape()`. It places cubes with a few tools from
`parts.py`:

- `g.put(part, x, y, z, colour)`: one cube.
- `g.fill(part, x0, x1, y0, y1, z0, z1, colour)`: a box.
- `g.tube(part, x0, x1, zc, r, colour)`: a round bar along x.
- `g.cut(x0, x1, y0, y1, z0, z1)`: remove a box of cubes from every part.

Add a second handle on the other side by copying the handle loop with `HANDLE_CENTRE_X` negated,
or cut a notch in the rim with `g.cut(...)`. Rebuild and look.

## Step 6: start your own model

1. Copy `examples/mug/` to a folder of your own (outside this repo if it is a game model).
2. Rename the three files to `<name>_settings.py`, `<name>_build.py` and, if the shape grows, split
   the shape into `<name>_shape.py`.
3. In the settings file, keep the `from cube_size import VOXEL_M` line as it is. **Never type a
   cube size of your own**: every model in a project shares the one in `cube_size.py`.
4. Write the sizes in cubes with names, draw the shape with the `Parts` tools, build, look, change.
5. Keep a `NOTES.md` beside it saying what was done and what is not, and drop a dated picture into
   `progress/` after every big change.

## Working from reference pictures

The models in the projects this kit came from were built from screenshots of the real thing and
from the game's own sprites. The method: measure proportions off the pictures (the glass is 480
pixels wide and 660 tall, so the glass is 1.4 times taller than wide), turn each into cubes from one
known size, and sample the colours from the game's own pictures so the model matches what the game
already shows. Reference pictures of paid models are reference only and never go into a repo.

## Animation

Once the model is right, moving parts are keyed in a separate `<name>_anim.py` with
`bl.key(object, frame, loc=..., rot_deg=...)` and `bl.all_constant()` at the end for the stop-motion
look. Copy the timings from the game's own animation definitions frame for frame. The shotgun this
kit was built on has a shot, a pump stroke and a reload keyed this way, 294 frames at 35 a second.
