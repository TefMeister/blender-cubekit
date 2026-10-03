# THE one cube size for every cube model in a project - gun, hands, casings, shells, flash,
# lantern, bare hand, pickups, all of it. Every model's *_settings.py imports VOXEL_M from here
# and nothing else may set it. Change it here and ONLY here, then rebuild every model.
#
# Why one number: a hand built from bigger cubes than the gun it holds looks like it came from a
# different game. One size, set in one place, is the only way that cannot drift.
#
# 3.4 mm is the size the first project settled on: a pistol about 21 cm long comes out at ~60 cubes,
# fine enough for a trigger and coarse enough to read as pixels from arm's length in a headset.
CUBE_MM = 3.4
VOXEL_M = CUBE_MM / 1000.0       # one cube, in metres (Blender units)
