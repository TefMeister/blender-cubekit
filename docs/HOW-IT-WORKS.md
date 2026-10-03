# How it works

The whole framework in one page: what a cube model is, where the numbers live, how a model gets
built, how it is animated, and how it reaches a game.

## 1. A model is a grid of cubes

Every model is a set of little cubes on a grid, like pixels with depth. There are no slopes and no
curves, only cube faces. Close up, every edge is a step; from arm's length it reads as pixel art,
which is the point.

- **Cube axes.** `x`, `y`, `z` are whole numbers. Which way they point is written at the top of each
  project's settings file (for a gun: `x` rear to muzzle, `y` across with `+` the gun's left, `z` up).
- **One cube size per project.** `cube_size.py` holds it, every settings file imports it, and nothing
  else may set it. A hand with bigger cubes than the gun it holds looks like it came from another
  game. Changing the number means rebuilding every model, so it is a decision, never a side effect.
- **Cubes have one colour each**, an sRGB triple, and belong to exactly one **part** (body, pump,
  trigger, hand). Each part becomes one Blender object, so the parts can move on their own.

## 2. Where the numbers live

Every project has one `*_settings.py` and that file holds **every** number and colour: sizes in
cubes, where the pivot is, the colours, the shading, the animation timings. A shape file reads
those names; a build script never holds a bare number. The reason is simple: a number with a name
can be found and changed; a `17` buried in a loop cannot.

A project's folder looks like this (the mug in `examples/` is a working one):

```
<project>/blender/
    xx_settings.py     every number and colour, imports VOXEL_M from cube_size.py
    xx_shape.py        the cubes, built with Parts (fill, tube, cut) from the settings
    xx_build.py        shape -> colours -> objects -> pictures -> .blend
    xx_anim.py         the animation keys, if the model moves
    renders/           pictures the build makes
    progress/          one dated picture per big change, so the history can be seen
    NOTES.md           what was done, what is not, and why
```

## 3. From cubes to a Blender object

1. **Shape.** `Parts` places cubes: `fill` a box, `tube` a round bar, `cut` a hole, `put` one cube.
   A cube belongs to one part only, so placing it moves it out of any other.
2. **Paint.** A function turns `{cube: colour name}` into `{cube: sRGB}`, adding bands, rust, wear,
   whatever the model needs, by rules, so it can be re-run.
3. **Shade.** Each face direction gets a brightness factor (`SHADE`): top lightest, underneath
   darkest, sides in between. Plus a small per-cube wobble (`NOISE`). This is what makes an unlit
   model read as solid. There are no lights in the scene, ever: what Blender shows is the texture
   the game gets.
4. **Merge.** Neighbouring faces of one colour are merged into bigger rectangles (greedy meshing,
   `atlas.py`), and every face's colour is written into one texture picture, the **atlas**. Tens of
   thousands of cubes become a few thousand faces, which is what a game can draw every frame.
5. **Objects.** `bl.make_objects` makes one mesh per part, textured from the atlas, parented to a
   root empty at the pivot. Materials are pure emission: unlit.

## 4. Picking one cube

Merging is right for the game and wrong for editing: a click lands on a strip that covers many
cubes. `bl.split_to_cubes` cuts every merged rectangle back into 1x1 cube faces and gives each cube
its own corners, so Blender's "select linked" grabs exactly one cube. The texture is cut with the
faces, so the look does not change. This is what the add-on's **Every cube on its own** button and
the **L** key use.

Pick-mode meshes are saved as `<name>_pick.blend`, never over the original: the game export reads
the mesh as it is in the file, and a pick-mode file would be thirty times heavier in the game.

## 5. Animation: stop-motion, tic for tic

Models that move are keyed in Blender with **constant** interpolation (`bl.all_constant`): no
blending between keys, every frame a held pose, like stop-motion. Timings are copied from the game's
own animation files frame for frame, so what is seen in Blender is what the game plays. Moving parts
are separate objects (the pump, the slide, a hand, a shell) and are moved whole cubes at a time where
possible, so they stay on the grid.

## 6. Into the game

The exporters read the `.blend` and write the game's model format with the atlas as the skin. There
is no unwrapping or baking: the atlas made at build time *is* the texture.

- `gz_world.py`: GZDoom. Writes several cube models into one `.pk3`, where a "frame" is simply
  which objects are showing. Takes a small profile file per project saying which objects and poses.
- Other engines get their own exporter in the same shape when a project needs one.

## 7. The rules this all rests on

- **One cube size per project**, in `cube_size.py`, nowhere else.
- **Every number has a name**, in the settings file.
- **No lights, ever.** The preview shows what the game shows.
- **The scripts are the model.** A `.blend` is an output; hand edits are for trying things, and the
  change is then made in the scripts and rebuilt.
- **Pick copies are never exported.**
- **Game models stay in their own project folders**, not in this repo. This repo is the framework.
