#!/usr/bin/env python3
"""Make the 2Web pictures from the source art in 2web/art/.

    python3 2web/make_pictures.py

- cover.jpg  (1280x720): art/cover-source.jpg as it is (already has the title, centre is clear).
- thumb.webp (512x512):  art/tile-source.png as it is, re-encoded as WebP.
Needs Pillow and the Inter Display Black font (any heavy sans works; change FONT).
"""
import os, shutil
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, 'art')
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'


def bottom_band(img, top, alpha):
    w, h = img.size[0], img.size[1] - top
    g = Image.new('L', (1, h))
    for y in range(h):
        g.putpixel((0, y), int(alpha * y / h))
    img.paste(Image.new('RGB', (w, h), (8, 16, 28)), (0, top), g.resize((w, h)))


def title(img, text, size, cx, cy, stroke):
    f = ImageFont.truetype(FONT, size)
    shadow = Image.new('L', img.size, 0)
    ImageDraw.Draw(shadow).multiline_text((cx + size // 18, cy + size // 14), text, font=f, fill=200,
                                          anchor='mm', align='center', spacing=-size // 8)
    img.paste(Image.new('RGB', img.size, (10, 20, 30)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(size // 10)))
    ImageDraw.Draw(img).multiline_text((cx, cy), text, font=f, fill=(255, 214, 40), anchor='mm', align='center',
                                       stroke_width=stroke, stroke_fill=(40, 22, 8), spacing=-size // 8)


def main():
    cover = Image.open(os.path.join(ART, 'cover-source.jpg'))
    assert cover.size == (1280, 720), cover.size
    shutil.copy(os.path.join(ART, 'cover-source.jpg'), os.path.join(HERE, 'cover.jpg'))

    thumb = Image.open(os.path.join(ART, 'tile-source.png')).convert('RGB')
    assert thumb.size == (512, 512), thumb.size
    thumb.save(os.path.join(HERE, 'thumb.webp'), quality=82, method=6)

    for f, limit in (('cover.jpg', 300_000), ('thumb.webp', 150_000)):
        size = os.path.getsize(os.path.join(HERE, f))
        print(f'{f}: {size / 1000:.0f} KB')
        assert size < limit, f'{f} is over {limit // 1000} KB'


if __name__ == '__main__':
    main()
