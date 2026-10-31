"""Turn the DerMedics logo into app assets.

Source: branding/dermedics_logo_v2_checker.jpg — the logo on a "transparency" checkerboard that is baked into
the JPG pixels (grey ~209 and white squares). The checkerboard is removed; the logo's own white (the face) is kept.

Outputs:
  branding/dermedics_logo.png               transparent logo, full resolution
  mobile/assets/images/logo.png             transparent logo, square, 512px (used in the app)
  mobile/android/app/src/main/res/mipmap-*/ic_launcher.png            transparent legacy icon
  mobile/android/app/src/main/res/drawable-*/ic_launcher_foreground.png  adaptive icon (Android 8+) on soft lavender
  mobile/web/favicon.png, mobile/web/icons/*.png                      transparent (maskable ones on lavender)
  mobile/ios/Runner/Assets.xcassets/AppIcon.appiconset/*.png          on lavender: Apple requires opaque icons

Run with the backend venv: backend/.venv/Scripts/python branding/make_assets.py
"""

from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "branding" / "dermedics_logo_v2_checker.jpg"
MOBILE = ROOT / "mobile"
CELL = 21  # checkerboard square size in pixels


def remove_checkerboard(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    r, g, b = img.split()
    hi = ImageChops.lighter(ImageChops.lighter(r, g), b)
    lo = ImageChops.darker(ImageChops.darker(r, g), b)
    spread = ImageChops.subtract(hi, lo)  # colourfulness

    neutral = spread.point(lambda v: 255 if v <= 10 else 0)
    light = lo.point(lambda v: 255 if v >= 192 else 0)
    grey_tone = hi.point(lambda v: 255 if 195 <= v <= 225 else 0)
    grey = ImageChops.multiply(neutral, grey_tone)
    # A checker pixel is light, neutral and close to a grey square; the face is pure white with no grey around it.
    near_grey = grey.filter(ImageFilter.MaxFilter(2 * CELL + 3))
    candidate = ImageChops.multiply(ImageChops.multiply(neutral, light), near_grey).load()

    bg = bytearray(w * h)
    q = deque([(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)])
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i] or not candidate[x, y]:
            continue
        bg[i] = 1
        if x > 0:
            q.append((x - 1, y))
        if x < w - 1:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y < h - 1:
            q.append((x, y + 1))

    mask = Image.frombytes("L", (w, h), bytes(255 if v else 0 for v in bg))
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), mask).load()
    m = mask.load()
    px = img.load()
    sp = spread.load()
    out = Image.new("RGBA", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            rr, gg, bb = px[x, y]
            if m[x, y]:
                op[x, y] = (rr, gg, bb, 0)
            elif edge[x, y]:
                # Anti-aliased rim: neutral-ish pixels are mostly checkerboard, colourful ones mostly logo.
                op[x, y] = (rr, gg, bb, max(0, min(255, sp[x, y] * 255 // 70)))
            else:
                op[x, y] = (rr, gg, bb, 255)
    out = clean_edges(out)
    bbox = out.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
    return out.crop(bbox)


def clean_edges(img: Image.Image) -> Image.Image:
    """Remove the light checkerboard fringe: pull the edge in 1px, feather it, and recolour edge pixels
    from nearby solid logo pixels so no grey/white bleeds through on dark backgrounds."""
    import numpy as np

    rgba = np.asarray(img, dtype=np.float32)
    solid = Image.fromarray(((rgba[..., 3] > 128) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
    soft = np.asarray(solid.filter(ImageFilter.GaussianBlur(0.9)), dtype=np.float32) / 255.0
    core = np.asarray(solid, dtype=np.float32) / 255.0

    def blur(a: np.ndarray, r: float) -> np.ndarray:
        # 8-bit blur (Pillow can't Gaussian-blur float images); inputs here are already in 0..255.
        img8 = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L")
        return np.asarray(img8.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32)

    weight = blur(core * 255, 3)
    fill = np.stack([blur(rgba[..., i] * core, 3) for i in range(3)], axis=-1) * 255 / np.maximum(weight, 1)[..., None]
    rgb = np.where((core < 1)[..., None], fill, rgba[..., :3])
    out = np.dstack([np.clip(rgb, 0, 255), soft * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def squared(logo: Image.Image, pad: float = 0.04) -> Image.Image:
    side = int(max(logo.size) * (1 + 2 * pad))
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(logo, ((side - logo.width) // 2, (side - logo.height) // 2), logo)
    return square


ADAPTIVE_ICON_XML = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
"""

BACKGROUND_COLOR_XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <!-- Launchers always draw a backdrop (transparent turns black on many); soft lavender matches the app theme. -->
    <color name="ic_launcher_background">#F3EEFF</color>
</resources>
"""

LAVENDER = (243, 238, 255, 255)  # app's soft lavender, for places that require an opaque background
CLEAR = (0, 0, 0, 0)


def on_tile(logo: Image.Image, size: int, pad: float = 0.12, bg=CLEAR) -> Image.Image:
    """Logo centred on a square canvas (transparent by default)."""
    tile = Image.new("RGBA", (size, size), bg)
    inner = int(size * (1 - 2 * pad))
    lg = logo.resize((inner, inner), Image.LANCZOS)
    tile.paste(lg, ((size - inner) // 2, (size - inner) // 2), lg)
    return tile


def main():
    logo = squared(remove_checkerboard(Image.open(SRC)))
    logo.save(ROOT / "branding" / "dermedics_logo.png", optimize=True)
    assets = MOBILE / "assets" / "images"
    assets.mkdir(parents=True, exist_ok=True)
    logo.resize((512, 512), Image.LANCZOS).save(assets / "logo.png", optimize=True)
    print("logo.png", logo.size)

    android = MOBILE / "android" / "app" / "src" / "main" / "res"
    densities = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
    for folder, scale in densities.items():
        # Legacy icon (Android 7 and older launchers): transparent, logo nearly fills it.
        d = android / f"mipmap-{folder}"
        d.mkdir(parents=True, exist_ok=True)
        on_tile(logo, round(48 * scale), 0.04).save(d / "ic_launcher.png")
        # Adaptive icon foreground: 108dp canvas, logo kept inside the 72dp safe zone.
        fg = android / f"drawable-{folder}"
        fg.mkdir(parents=True, exist_ok=True)
        on_tile(logo, round(108 * scale), 0.18).save(fg / "ic_launcher_foreground.png")
    anydpi = android / "mipmap-anydpi-v26"
    anydpi.mkdir(exist_ok=True)
    (anydpi / "ic_launcher.xml").write_text(ADAPTIVE_ICON_XML)
    values = android / "values"
    values.mkdir(exist_ok=True)
    (values / "ic_launcher_background.xml").write_text(BACKGROUND_COLOR_XML)
    print("android icons done")

    web = MOBILE / "web"
    if web.exists():
        logo.resize((64, 64), Image.LANCZOS).save(web / "favicon.png")
        for name, size in {"Icon-192.png": 192, "Icon-512.png": 512}.items():
            on_tile(logo, size).save(web / "icons" / name)
        for name, size in {"Icon-maskable-192.png": 192, "Icon-maskable-512.png": 512}.items():
            on_tile(logo, size, 0.2, LAVENDER).save(web / "icons" / name)  # maskable icons must be opaque
        print("web icons done")

    ios = MOBILE / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"
    if ios.exists():
        for f in ios.glob("*.png"):
            with Image.open(f) as existing:
                size = existing.size[0]
            on_tile(logo, size, 0.12, LAVENDER).convert("RGB").save(f)
        print("ios icons done")


if __name__ == "__main__":
    main()
