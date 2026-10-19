# Puts a forge model's preview pictures onto one sheet (plain Python with Pillow, outside Blender):
#   python forge_sheet.py <render dir> <name> <out.png>
import os
import sys

from PIL import Image, ImageDraw

ORDER = ("left", "right", "player", "front34", "close", "top")


def main():
    folder, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
    ims = [(v, Image.open(os.path.join(folder, "%s_%s.png" % (name, v))).convert("RGB")) for v in ORDER
           if os.path.exists(os.path.join(folder, "%s_%s.png" % (name, v)))]
    w = 1400
    rows = []
    # sides on top of each other at full width, then the two perspective views side by side, then the top
    for v, im in ims:
        if v in ("left", "right", "top"):
            rows.append([im.resize((w, int(im.height * w / im.width)))])
    persp = [im for v, im in ims if v in ("player", "front34")]
    if persp:
        rows.insert(2, [im.resize((w // 2, int(im.height * (w // 2) / im.width))) for im in persp])
    close = [im for v, im in ims if v == "close"]
    if close:
        rows.insert(3, [close[0].resize((w, int(close[0].height * w / close[0].width)))])
    H = sum(max(i.height for i in r) for r in rows) + 30
    sheet = Image.new("RGB", (w, H), (20, 20, 26))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), name, fill=(255, 220, 90))
    y = 30
    for r in rows:
        x = 0
        for im in r:
            sheet.paste(im, (x, y))
            x += im.width
        y += max(i.height for i in r)
    sheet.save(out)
    print(out)


main()
