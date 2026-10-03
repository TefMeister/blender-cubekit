# Roadmap

What is asked for and not built yet, in the asker's words, with the open questions written down so
the next session starts ready.

## Mixed cube sizes inside one model (asked 2026-10-03, waiting for a design session)

**The ask, Tefa's words:** *"what i would like to have is just selected cubes, and it would have to
work if only a side is highlighted or the whole cube it doesn't matter, the whole cube still get's
split. so this selection would only work on highlighted boxes."* The cube size buttons act on the
picked cubes only, not the whole file. Picking one side of a cube counts as picking that cube.

**Going back to bigger, also theirs:** *"One or a few small cubes removed: the big cube comes back
whole, and the hole gets filled. More than half of the 8 removed: the whole big cube goes, so that
spot becomes empty. this would apply too."* (Today's rule, `edit.MERGE_KEEP = 4`.)

**The size row:** *"there would not be a button to change the scale of the whole project at all, but
the cube size must also have bigger sizes 6.8mm and 13.6mm, but these sizes in the Blender Cubekit
tab, please make them go larger from left to right."* So: 0.85 · 1.7 · 3.4 · 6.8 · 13.6 mm, smallest
on the left. The whole-file size buttons of 0.9.0 go away.

**Why it waits:** today every model has one grid of one size, and every tool (picking, painting,
E, Q, the 4 / 16 split, the game export) assumes it. Mixed sizes means a new way of storing cubes that
all of those rest on: a design decision, so it was held for a Fable session (Tefa's model rule).

**A likely shape, not decided:** store each model at its finest size, and keep a "block" mark for
cubes shown as one bigger cube (the way a 4-way split side keeps 16 colours but shows 4). A block
picks, paints and digs as one cube; pressing a smaller size on it removes the mark (its 8 parts
become separate); a bigger size adds marks. Blocks stay on their own size's grid, so a 6.8 mm block
always covers the same eight 3.4 mm cubes.

**Questions to settle first:**
1. **Bigger sizes on a selection** - ✅ Tefa chose (2026-10-03): **join every block the selection
   touches**, filling the block's empty spots by the more-than-half rule.
   **Still open: where the bigger cube lands.** Tefa asked whether the picked 3.4 mm cube always stays
   in the upper-left corner, with the 6.8 mm cube growing right, down and inward from it. Two ways:
   - *Anchored on the pick* (Tefa's picture): predictable from the click, but neighbouring big cubes
     need not line up, so steps of half a big cube appear, and going back down or up again can land
     somewhere different.
   - *Fixed grid* (the 3.4 mm cubes are already on one): every 6.8 mm cube covers the same eight
     3.4 mm cubes every time, so big cubes always line up and up / down always round-trips; the
     picked cube can end up in any of the 8 corners. Recommended, with a **preview outline** under
     the mouse showing exactly where the bigger cube will land before anything changes.
   Tefa to decide on Wednesday, ideally after seeing the preview idea.
2. **Neighbours of different sizes** - a 3.4 mm side next to a 1.7 mm cube shows part of its face.
   That is fine for the look; the game export has to handle it too.
3. **The game export** - edits in editing copies do not reach the game yet at all (a separate
   missing step); mixed sizes should be built so that step can come next.
