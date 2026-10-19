# Builds forge designs end to end with no Blender window: the .blend, its preview pictures and one sheet each.
#   python forge_make.py <blend folder> <render folder> <design.py> [<design.py> ...]
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def make(design, blend_dir, render_dir):
    name = os.path.splitext(os.path.basename(design))[0]
    blend = os.path.join(blend_dir, name + ".blend")
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", os.path.join(HERE, "forge_run.py"), "--",
                        os.path.abspath(design), blend, os.path.abspath(render_dir)],
                       capture_output=True, text=True, errors="replace")
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("FORGE ")]
    if r.returncode or not lines:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("blender failed on " + design)
    print(lines[-1])
    model = lines[-1].split()[1].rstrip(":")
    subprocess.run([sys.executable, os.path.join(HERE, "forge_sheet.py"), render_dir, model,
                    os.path.join(render_dir, "sheet_" + model + ".png")], check=True, capture_output=True)


if __name__ == "__main__":
    blend_dir, render_dir = sys.argv[1], sys.argv[2]
    os.makedirs(blend_dir, exist_ok=True)
    os.makedirs(render_dir, exist_ok=True)
    for d in sys.argv[3:]:
        make(d, blend_dir, render_dir)
