"""Turn a photo into braille-dot art for the banner.

Works with any image size: the crop and head mask are fractions of the image, not pixels.
Preview in the terminal while tuning:  python3 scripts/portrait.py path/to/photo.jpg
"""

import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

# braille cells pack a 2x4 dot grid, the same trick chafa/fastfetch use for images in a terminal
DOTS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]


def braille(
    path, cols=64, rows=32, focus=(0.5, 0.45), zoom=1.0, head=(0.86, 1.0), feather=0.045, contrast=1.6, edges=0.4, flatten=0.0
):
    """Return `rows` strings of `cols` braille characters; lit dots are the bright parts of the photo.

    focus   center of the crop, as fractions of the image width/height
    zoom    crop size as a fraction of the largest box with the art's aspect that fits
    head    width/height of the elliptical mask as fractions of the crop; it drops the background
    feather mask edge softness as a fraction of the crop width
    contrast gamma applied after equalizing; above 1 darkens midtones so features stand out
    edges   how strongly to trace outlines, so dark areas like hair still get a shape (0 turns it off)
    flatten 0..1 blend toward a high-pass copy, which evens out side lighting in dim photos (0 turns it off)
    """
    img = ImageOps.exif_transpose(Image.open(path)).convert("L")
    w, h = img.size
    aspect = (cols * 2) / (rows * 4)  # dots are square, so this is the crop's width / height
    cw = min(w, h * aspect) * zoom
    ch = cw / aspect
    cx = min(max(focus[0] * w, cw / 2), w - cw / 2)
    cy = min(max(focus[1] * h, ch / 2), h - ch / 2)
    img = img.crop((round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2), round(cy + ch / 2)))

    mw, mh = img.size
    if flatten:
        # detail relative to the local brightness, so a shadowed half of the face keeps its features
        detail = ImageChops.subtract(img, img.filter(ImageFilter.GaussianBlur(mw * 0.1)), scale=0.4, offset=128)
        img = Image.blend(img.point(lambda v: min(255, int(v * 1.8))), detail, flatten)
    mask = Image.new("L", img.size, 0)
    ex, ey = mw * head[0] / 2, mh * head[1] / 2
    ImageDraw.Draw(mask).ellipse((mw / 2 - ex, mh / 2 - ey, mw / 2 + ex, mh / 2 + ey), fill=255)
    # stretch tones using only the pixels inside the head, so a bright wall can't wash the face out
    img = ImageOps.equalize(img, mask=mask).point(lambda v: int(255 * (v / 255) ** contrast))
    if edges:
        small = img.resize((cols * 2, rows * 4), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
        outline = ImageOps.autocontrast(small.filter(ImageFilter.FIND_EDGES), cutoff=2).resize(img.size, Image.BILINEAR)
        img = ImageChops.lighter(img, outline.point(lambda v: int(v * edges)))
    img = ImageChops.multiply(img, mask.filter(ImageFilter.GaussianBlur(mw * feather)))

    img = img.resize((cols * 2, rows * 4), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1, 120, 1))
    px = img.convert("1").load()  # floyd-steinberg dither
    return [
        "".join(chr(0x2800 + sum(bit for dx, dy, bit in DOTS if px[c * 2 + dx, r * 4 + dy])) for c in range(cols))
        for r in range(rows)
    ]


if __name__ == "__main__":
    print("\n".join(braille(sys.argv[1])))
