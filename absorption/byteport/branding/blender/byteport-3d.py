# BytePort 3D Logo Generator (Pillow-based, no Blender required)
# Run: python3 byteport-3d.py
# Output: byteport-3d.png (512x512)

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZE = 512
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "byteport-3d.png")

# Brand colors
BG_TOP = (15, 15, 35)
BG_BOTTOM = (26, 10, 46)
ORANGE = (255, 107, 53)
GOLD = (247, 201, 72)
DARK_TEXT = (107, 114, 128)


def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB colors."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_gradient_bg(draw, size):
    """Draw a diagonal gradient background with rounded corners."""
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            color = lerp_color(BG_TOP, BG_BOTTOM, t)
            draw.point((x, y), fill=color)


def draw_rounded_rect(draw, bbox, radius, fill):
    """Draw a filled rounded rectangle."""
    x0, y0, x1, y1 = bbox
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)


def draw_arrow(draw, tip_x, tip_y, base_w, base_h, direction, color, shadow_offset=0):
    """Draw an arrow (triangle + stem) with optional shadow.

    direction: 'up' or 'down'
    """
    stem_w = base_w * 0.25
    head_h = base_h * 0.45
    stem_h = base_h * 0.55

    if direction == "up":
        # Triangle pointing up
        tri = [
            (tip_x, tip_y - shadow_offset),
            (tip_x - base_w / 2, tip_y + head_h - shadow_offset),
            (tip_x + base_w / 2, tip_y + head_h - shadow_offset),
        ]
        # Stem below triangle
        stem = [
            (tip_x - stem_w / 2, tip_y + head_h - shadow_offset),
            (tip_x + stem_w / 2, tip_y + head_h - shadow_offset),
            (tip_x + stem_w / 2, tip_y + head_h + stem_h - shadow_offset),
            (tip_x - stem_w / 2, tip_y + head_h + stem_h - shadow_offset),
        ]
    else:
        # Triangle pointing down
        tri = [
            (tip_x, tip_y + shadow_offset),
            (tip_x - base_w / 2, tip_y - head_h + shadow_offset),
            (tip_x + base_w / 2, tip_y - head_h + shadow_offset),
        ]
        # Stem above triangle
        stem = [
            (tip_x - stem_w / 2, tip_y - head_h + shadow_offset),
            (tip_x + stem_w / 2, tip_y - head_h + shadow_offset),
            (tip_x + stem_w / 2, tip_y - head_h - stem_h + shadow_offset),
            (tip_x - stem_w / 2, tip_y - head_h - stem_h + shadow_offset),
        ]

    draw.polygon(tri, fill=color)
    draw.polygon(stem, fill=color)


def draw_isometric_depth(base_img, cx, cy, depth=4, color_shift=(20, 20, 30)):
    """Apply an isometric depth effect by adding offset copies of elements."""
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Draw subtle depth layers
    for i in range(depth, 0, -1):
        alpha = int(40 * (1 - i / depth))
        shifted_color = (
            max(0, ORANGE[0] - color_shift[0] * i),
            max(0, ORANGE[1] - color_shift[1] * i),
            max(0, ORANGE[2] - color_shift[2] * i),
            alpha,
        )
        # Small shifted rectangle to simulate depth
        offset = i * 2
        draw.rounded_rectangle(
            [cx - 80 + offset, cy - 100 + offset, cx + 80 + offset, cy + 100 + offset],
            radius=8,
            fill=shifted_color,
        )
    return Image.alpha_composite(base_img, overlay)


def draw_gradient_overlay(img, bbox):
    """Draw a diagonal gradient overlay for 3D lighting effect."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = bbox
    for y in range(y0, y1):
        for x in range(x0, x1):
            # Diagonal gradient from top-left (bright) to bottom-right (dark)
            t = ((x - x0) + (y - y0)) / max(1, (x1 - x0) + (y1 - y0))
            brightness = 1.0 - t * 0.6  # Range: 0.4 to 1.0
            r = int(ORANGE[0] * brightness * 0.15)
            g = int(ORANGE[1] * brightness * 0.15)
            b = int(ORANGE[2] * brightness * 0.15)
            draw.point((x, y), fill=(r, g, b, 30))
    return Image.alpha_composite(img, overlay)


def draw_shadow(base_img, bbox, offset=(6, 6), blur_radius=10):
    """Draw a soft drop shadow behind a rectangular region."""
    shadow_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    x0, y0, x1, y1 = bbox
    # Draw shadow rectangle
    shadow_draw.rounded_rectangle(
        [x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]],
        radius=20,
        fill=(0, 0, 0, 60),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
    return Image.alpha_composite(shadow_layer, base_img)


def _corner_clips_out(x, y, size, r) -> bool:
    """True when (x, y) falls outside the rounded-corner clip region."""
    if x < r and y < r:
        return (x - r) ** 2 + (y - r) ** 2 > r * r
    if x > size - r and y < r:
        return (x - (size - r)) ** 2 + (y - r) ** 2 > r * r
    if x < r and y > size - r:
        return (x - r) ** 2 + (y - (size - r)) ** 2 > r * r
    if x > size - r and y > size - r:
        return (x - (size - r)) ** 2 + (y - (size - r)) ** 2 > r * r
    return False


def _paint_gradient(size, bg_top, bg_bottom, corner_r):
    """Vertical gradient clipped to the rounded-corner background."""
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(size):
        for x in range(size):
            if _corner_clips_out(x, y, size, corner_r):
                continue
            t = (x + y) / (2 * size)
            color = lerp_color(bg_top, bg_bottom, t)
            draw.point((x, y), fill=color + (255,))
    return overlay


def _load_font(px):
    """First available system font, falling back to the built-in default."""
    for path in (
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Monospaced.ttf",
    ):
        try:
            return ImageFont.truetype(path, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_dotted_line():
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(14):
        if i % 2 == 0:
            x = 208 + i * 8
            draw.ellipse([x - 1, 309, x + 1, 311], fill=ORANGE + (128,))
    return layer


def main():
    # Create base image with alpha channel
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- Background (rounded rect) ---
    margin = 0
    corner_r = 96
    draw_rounded_rect(
        draw, (margin, margin, SIZE - margin, SIZE - margin), corner_r, BG_TOP + (255,)
    )

    # Apply gradient on background
    bg_overlay = _paint_gradient(SIZE, BG_TOP, BG_BOTTOM, corner_r)
    img = Image.alpha_composite(img, bg_overlay)

    # --- Glow effect ---
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([126, 90, 386, 350], fill=ORANGE + (40,))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img, glow)

    # --- Isometric depth effect ---
    img = draw_isometric_depth(img, SIZE // 2, 200, depth=5)

    # --- Arrow shadow ---
    arrow_shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    as_draw = ImageDraw.Draw(arrow_shadow)
    # Left arrow shadow
    draw_arrow(as_draw, 160, 140, 120, 200, "up", (0, 0, 0, 30), shadow_offset=6)
    # Right arrow shadow
    draw_arrow(as_draw, 352, 220, 120, 200, "down", (0, 0, 0, 30), shadow_offset=6)
    arrow_shadow = arrow_shadow.filter(ImageFilter.GaussianBlur(8))
    img = Image.alpha_composite(img, arrow_shadow)

    # --- Draw arrows ---
    arrow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ar_draw = ImageDraw.Draw(arrow_layer)

    # Left arrow (upload) - orange
    draw_arrow(ar_draw, 160, 140, 120, 200, "up", ORANGE + (255,))

    # Right arrow (download) - gold, slightly transparent
    gold_transparent = GOLD + (180,)
    draw_arrow(ar_draw, 352, 220, 120, 200, "down", gold_transparent)

    img = Image.alpha_composite(img, arrow_layer)

    # --- Connection dots ---
    dot_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dot_draw = ImageDraw.Draw(dot_layer)
    dot_draw.ellipse([194, 304, 206, 316], fill=ORANGE + (204,))
    dot_draw.ellipse([306, 304, 318, 316], fill=GOLD + (204,))
    img = Image.alpha_composite(img, dot_layer)

    # --- Dotted connection line ---
    line_layer = _draw_dotted_line()
    img = Image.alpha_composite(img, line_layer)

    # --- Gradient lighting overlay ---
    img = draw_gradient_overlay(img, (100, 80, 412, 380))

    # --- Text: BYTEPORT ---
    text_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    font_large = _load_font(48)

    text = "BYTEPORT"
    bbox_text = text_draw.textbbox((0, 0), text, font=font_large)
    tw = bbox_text[2] - bbox_text[0]
    tx = (SIZE - tw) // 2
    text_draw.text((tx, 400), text, fill=ORANGE + (255,), font=font_large)
    img = Image.alpha_composite(img, text_layer)

    # --- Tagline ---
    tag_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tag_draw = ImageDraw.Draw(tag_layer)
    font_small = _load_font(14)

    tagline = "SECURE DATA TRANSPORT"
    tag_bbox = tag_draw.textbbox((0, 0), tagline, font=font_small)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_x = (SIZE - tag_w) // 2
    tag_draw.text((tag_x, 458), tagline, fill=DARK_TEXT + (255,), font=font_small)
    img = Image.alpha_composite(img, tag_layer)

    # --- Final composite: flatten to RGB ---
    final = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    final.paste(img, mask=img.split()[3])

    final.save(OUTPUT, "PNG")
    print(f"Rendered: {OUTPUT}")
    print(f"Size: {final.size}")


if __name__ == "__main__":
    main()
