#!/usr/bin/env python3
"""Generate Phinbox branding assets — app icon, tray icons, splash, DMG background.

Brand: #7EBAB5 teal, dark mode, no emoji.
Outputs: PNG files ready for macOS deployment.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

TEAL = (126, 186, 181)        # #7EBAB5
TEAL_DIM = (80, 130, 126)     # dimmer teal for shadows
BG_DARK = (19, 25, 37)        # #131925
BG_DARKER = (12, 16, 24)


def rounded_rect_mask(size, radius):
    """Create a rounded rectangle mask."""
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def draw_envelope(draw, cx, cy, w, h, color, flap_color, line_w=3):
    """Draw a clean envelope icon with body and V-flap."""
    left = cx - w / 2
    top = cy - h / 2
    right = cx + w / 2
    bottom = cy + h / 2
    r = w * 0.12  # corner radius

    # Body
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=r,
        fill=None,
        outline=color,
        width=line_w,
    )
    # V-flap
    flap_top = top
    flap_mid = top + h * 0.48
    draw.line(
        [(left, flap_top), (cx, flap_mid)],
        fill=flap_color,
        width=line_w,
    )
    draw.line(
        [(cx, flap_mid), (right, flap_top)],
        fill=flap_color,
        width=line_w,
    )


def gen_app_icon():
    """1024x1024 app icon with dark bg, teal envelope, subtle glow."""
    sz = 1024
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark rounded rect background
    r = int(sz * 0.22)  # macOS icon corner radius
    mask = rounded_rect_mask(sz, r)

    bg = Image.new("RGBA", (sz, sz), BG_DARK + (255,))
    bg.putalpha(mask)

    # Subtle teal glow behind envelope
    glow = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    glow_r = int(sz * 0.35)
    for i in range(glow_r, 0, -2):
        alpha = int(35 * (1 - i / glow_r))
        gd.ellipse(
            [sz // 2 - i, sz // 2 - i, sz // 2 + i, sz // 2 + i],
            fill=TEAL + (alpha,),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=20))

    img = Image.alpha_composite(img, bg)
    img = Image.alpha_composite(img, glow)

    # Draw envelope
    draw = ImageDraw.Draw(img)
    env_w = sz * 0.48
    env_h = sz * 0.35
    draw_envelope(
        draw,
        sz // 2,
        int(sz * 0.48),
        env_w,
        env_h,
        color=TEAL + (255,),
        flap_color=TEAL + (220,),
        line_w=8,
    )

    # "P" letter below envelope
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSRounded.ttf", 120)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "P", font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        (sz // 2 - tw // 2, int(sz * 0.68)),
        "P",
        fill=TEAL + (200,),
        font=font,
    )

    img.save(OUT / "app_icon_1024.png")
    print(f"[OK] app_icon_1024.png ({sz}x{sz})")


def gen_tray_icons():
    """22px and 44px tray icons — simple teal envelope outline."""
    for target_size in [22, 44]:
        # Draw at 4x then downscale for crispness
        draw_sz = target_size * 4
        img = Image.new("RGBA", (draw_sz, draw_sz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad = draw_sz * 0.12
        env_w = draw_sz - pad * 2
        env_h = env_w * 0.7
        cy = draw_sz * 0.44
        draw_envelope(
            draw,
            draw_sz // 2,
            int(cy),
            env_w,
            env_h,
            color=TEAL + (255,),
            flap_color=TEAL + (255,),
            line_w=max(2, int(draw_sz * 0.04)),
        )
        img = img.resize((target_size, target_size), Image.LANCZOS)
        img.save(OUT / f"tray_{target_size}.png")
        print(f"[OK] tray_{target_size}.png ({target_size}x{target_size})")


def gen_splash():
    """1024x768 splash — dark gradient with teal center glow and envelope."""
    w, h = 1024, 768
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))

    # Radial gradient background
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    max_r = int(math.sqrt(cx ** 2 + cy ** 2))
    for r in range(max_r, 0, -3):
        t = r / max_r
        # Dark center, slightly lighter edges
        rv = int(BG_DARK[0] + (BG_DARKER[0] - BG_DARK[0]) * t)
        gv = int(BG_DARK[1] + (BG_DARKER[1] - BG_DARK[1]) * t)
        bv = int(BG_DARK[2] + (BG_DARKER[2] - BG_DARK[2]) * t)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(rv, gv, bv, 255))

    # Teal glow
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    glow_r = 260
    for i in range(glow_r, 0, -2):
        alpha = int(50 * (1 - i / glow_r))
        gd.ellipse(
            [cx - i, cy - i, cx + i, cy + i],
            fill=TEAL + (alpha,),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=30))
    img = Image.alpha_composite(img, glow)

    # Envelope
    draw = ImageDraw.Draw(img)
    env_w = 240
    env_h = 170
    draw_envelope(
        draw,
        cx,
        cy - 40,
        env_w,
        env_h,
        color=TEAL + (255,),
        flap_color=TEAL + (200,),
        line_w=5,
    )

    # "Phinbox" text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSRounded.ttf", 56)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "Phinbox", font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        (cx - tw // 2, cy + 100),
        "Phinbox",
        fill=TEAL + (200,),
        font=font,
    )

    img.save(OUT / "splash_1024x768.png")
    print(f"[OK] splash_1024x768.png ({w}x{h})")


def gen_iconset():
    """Generate AppIcon.iconset for macOS using sips/iconutil."""
    iconset_dir = OUT / "AppIcon.iconset"
    iconset_dir.mkdir(exist_ok=True)

    src = OUT / "app_icon_1024.png"
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    import subprocess

    for sz, name in sizes:
        out_path = iconset_dir / name
        subprocess.run(
            ["sips", "-z", str(sz), str(sz), str(src), "--out", str(out_path)],
            capture_output=True,
        )
    subprocess.run(["iconutil", "-c", "icns", str(iconset_dir)], check=True)
    print(f"[OK] AppIcon.icns generated via iconutil")


if __name__ == "__main__":
    gen_app_icon()
    gen_tray_icons()
    gen_splash()
    gen_iconset()
    print("\nAll assets in:", OUT)
