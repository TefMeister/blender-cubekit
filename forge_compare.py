# Several forge models' pictures of one view stacked on one sheet, for a quick look:
#   python forge_compare.py <render dir> <view> <out.png> <model> [<model> ...]
import os
import sys

from PIL import Image, ImageDraw

folder, view, out, names = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
w = 1100
ims = []
for n in names:
    im = Image.open(os.path.join(folder, "%s_%s.png" % (n, view))).convert("RGB")
    ims.append((n, im.resize((w, int(im.height * w / im.width)))))
sheet = Image.new("RGB", (w, sum(i.height + 18 for _, i in ims)), (20, 20, 26))
d = ImageDraw.Draw(sheet)
y = 0
for n, im in ims:
    d.text((6, y + 3), n, fill=(255, 220, 90))
    sheet.paste(im, (0, y + 18))
    y += im.height + 18
sheet.save(out)
