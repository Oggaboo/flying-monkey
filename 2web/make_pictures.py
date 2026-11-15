#!/usr/bin/env python3
"""Make 2web/cover.jpg (1280x720) and 2web/thumb.webp (512x512) from a 2560x1440 gameplay
screenshot (the gorilla flying, no obstacle on screen).

    python3 2web/make_pictures.py <screenshot.png> 2web
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')  # 2560x1440 gameplay frame
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'

def title(img, text, size, cx, cy, stroke):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size)
    # soft shadow
    sh = Image.new('L', img.size, 0); ImageDraw.Draw(sh).text((cx + size // 18, cy + size // 14), text, font=f, fill=200, anchor='mm', align='center', spacing=0)
    sh = sh.filter(ImageFilter.GaussianBlur(size // 10))
    img.paste(Image.new('RGB', img.size, (10, 20, 30)), (0, 0), sh)
    d.multiline_text((cx, cy), text, font=f, fill=(255, 214, 40), anchor='mm', align='center',
                     stroke_width=stroke, stroke_fill=(40, 22, 8), spacing=-size // 8)

def band(img, top, h, alpha, from_top=True):
    w = img.size[0]
    g = Image.new('L', (1, h))
    for y in range(h):
        a = int(alpha * (1 - y / h)) if from_top else int(alpha * y / h)
        g.putpixel((0, y), a)
    g = g.resize((w, h))
    img.paste(Image.new('RGB', (w, h), (8, 16, 28)), (0, top), g)

# cover: 1280x720, drop the HUD row, title in the top band, centre left clear
cover = im.crop((142, 160, 2418, 1440)).resize((1280, 720), Image.LANCZOS)
band(cover, 0, 230, 170)
title(cover, 'FLYING GORILLA', 104, 640, 112, 6)
cover.save(f'{out}/cover.jpg', quality=84, optimize=True, progressive=True)

# thumb: 512x512 around the gorilla, title at the bottom
thumb = im.crop((800, 380, 1760, 1340)).resize((512, 512), Image.LANCZOS)
band(thumb, 300, 212, 210, from_top=False)
title(thumb, 'FLYING\nGORILLA', 92, 256, 420, 5)
thumb.save(f'{out}/thumb.webp', quality=82, method=6)
