"""Core image-generation logic: places a user photo inside the template's
left-hand box and draws the user's words on the right-hand side, while
keeping the decorative frame untouched.
"""
import os
import arabic_reshaper
from bidi.algorithm import get_display
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# قالب 2.png is the same design as قالب.png but without the "Words/كلمات"
# placeholder text baked in, so the words area never needs to be wiped —
# that erase step used to risk clipping the frame artwork near the text zone.
TEMPLATE_PATH = os.path.join(BASE_DIR, "static", "template", "قالب 2.png")
FONTS_DIR = os.path.join(BASE_DIR, "static", "fonts")

CANVAS_SIZE = (1024, 512)

# Region measured directly from the template. Used to wipe the original
# placeholder photo box before drawing the user's own photo, without
# touching the golden frame.
DEFAULT_BOX_RECT = (77, 43, 502, 468)          # outer rect incl. border
BOX_ERASE_RECT = (74, 40, 505, 471)            # a hair wider, for anti-aliasing

FONT_CHOICES = [
    ("calibrib.ttf", "Calibri Bold (افتراضي)"),
    ("calibri.ttf", "Calibri"),
    ("tahomabd.ttf", "Tahoma Bold"),
    ("tahoma.ttf", "Tahoma"),
    ("Cairo-Bold.ttf", "Cairo Bold"),
    ("Cairo-Regular.ttf", "Cairo"),
    ("Almarai-Bold.ttf", "Almarai Bold"),
    ("Almarai-Regular.ttf", "Almarai"),
    ("arialbd.ttf", "Arial Bold"),
    ("arial.ttf", "Arial"),
    ("Amiri-Bold.ttf", "Amiri Bold (خط عربي كلاسيكي)"),
    ("Amiri-Regular.ttf", "Amiri Regular"),
    ("DUBAI-BOLD.TTF", "Dubai Bold (للنصوص الإنجليزية فقط)"),
    ("DUBAI-MEDIUM.TTF", "Dubai Medium (للنصوص الإنجليزية فقط)"),
    ("DUBAI-REGULAR.TTF", "Dubai Regular (للنصوص الإنجليزية فقط)"),
    ("BalooBhaijaan2-Bold.ttf", "Baloo Bhaijaan 2 Bold (للنصوص الإنجليزية فقط)"),
    ("BalooBhaijaan2-Regular.ttf", "Baloo Bhaijaan 2 (للنصوص الإنجليزية فقط)"),
]


def hex_to_rgba(hex_color, alpha=255):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def shape_line(line):
    """Reshape + reorder a line of (possibly Arabic) text for correct rendering."""
    if not line:
        return ""
    reshaped = arabic_reshaper.reshape(line)
    return get_display(reshaped)


# Some modern Arabic webfonts (built for proper OpenType shaping) ship an
# incomplete Arabic Presentation-Forms set, e.g. a missing "isolated" glyph
# for one particular letter. Since this project reshapes text in Python
# (no libraqm in this Pillow build) and draws pre-shaped codepoints directly,
# a gap like that would otherwise show as a blank tofu box. Tahoma Bold has
# full coverage of that block, so it is used to silently patch any single
# missing glyph from whichever font the user picked.
FALLBACK_FONT_FILE = "tahomabd.ttf"

_cmap_cache = {}


def _font_cmap(font_path):
    if font_path not in _cmap_cache:
        try:
            cmap = set(TTFont(font_path, lazy=True, fontNumber=0).getBestCmap().keys())
        except Exception:
            cmap = None  # unreadable: assume full coverage rather than block all text
        _cmap_cache[font_path] = cmap
    return _cmap_cache[font_path]


def _font_has_char(font_path, ch):
    cmap = _font_cmap(font_path)
    return cmap is None or ord(ch) in cmap


def resolve_line_fonts(shaped_line, font, font_path, fallback_font, fallback_path):
    """Return a list of (char, PIL font) pairs for a shaped line, substituting
    the fallback font for any individual character missing from the main font."""
    pairs = []
    for ch in shaped_line:
        if ch.isspace() or _font_has_char(font_path, ch):
            pairs.append((ch, font))
        elif fallback_font is not None and _font_has_char(fallback_path, ch):
            pairs.append((ch, fallback_font))
        else:
            pairs.append((ch, font))
    return pairs


def rounded_mask(size, radius):
    w, h = size
    radius = max(0, min(radius, w // 2, h // 2))
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return mask


def fit_photo(user_img, box_w, box_h, fit_mode, background_rgba):
    user_img = user_img.convert("RGBA")
    box_w, box_h = max(1, box_w), max(1, box_h)

    if fit_mode == "cover":
        # flatten any transparency onto white first: the final paste uses only
        # the box's rounded-corner mask, so a transparent pixel here would
        # otherwise leak the PNG's raw (often black) RGB data through.
        flat = Image.new("RGBA", user_img.size, (255, 255, 255, 255))
        flat.alpha_composite(user_img)
        user_img = flat
        scale = max(box_w / user_img.width, box_h / user_img.height)
        new_w, new_h = max(1, round(user_img.width * scale)), max(1, round(user_img.height * scale))
        resized = user_img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - box_w) // 2
        top = (new_h - box_h) // 2
        return resized.crop((left, top, left + box_w, top + box_h))

    # contain: fit the whole photo inside the box, padding with background color
    scale = min(box_w / user_img.width, box_h / user_img.height)
    new_w, new_h = max(1, round(user_img.width * scale)), max(1, round(user_img.height * scale))
    resized = user_img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (box_w, box_h), background_rgba)
    left = (box_w - new_w) // 2
    top = (box_h - new_h) // 2
    canvas.paste(resized, (left, top), resized)
    return canvas


def draw_photo_box(base, user_img, box_settings):
    x, y = box_settings["x"], box_settings["y"]
    w, h = box_settings["width"], box_settings["height"]
    border_w = box_settings["border_width"]
    radius = box_settings["corner_radius"]
    border_rgba = hex_to_rgba(box_settings["border_color"])
    bg_rgba = hex_to_rgba(box_settings.get("background_color", "#FBE4A8"))
    fit_mode = box_settings.get("fit_mode", "cover")

    # 1) filled border-colored rounded rect for the full outer box
    if border_w > 0:
        border_layer = Image.new("RGBA", (w, h), border_rgba)
        mask = rounded_mask((w, h), radius)
        base.paste(border_layer, (x, y), mask)

    # 2) the photo itself, inset by the border, with a slightly smaller radius
    inner_x, inner_y = x + border_w, y + border_w
    inner_w, inner_h = max(1, w - 2 * border_w), max(1, h - 2 * border_w)
    inner_radius = max(0, radius - border_w)

    photo = fit_photo(user_img, inner_w, inner_h, fit_mode, bg_rgba)
    inner_mask = rounded_mask((inner_w, inner_h), inner_radius)
    base.paste(photo, (inner_x, inner_y), inner_mask)


def _line_width(logical_line, font, font_path, fallback_font, fallback_path):
    shaped = shape_line(logical_line)
    run = resolve_line_fonts(shaped, font, font_path, fallback_font, fallback_path)
    return sum(f.getlength(ch) for ch, f in run)


def _wrap_paragraph(paragraph, font, font_path, fallback_font, fallback_path, max_width):
    """Greedy word-wrap a single paragraph (already split on \\n) into lines
    that each fit within max_width at the given font size."""
    words = paragraph.split()
    if not words:
        return [""]

    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        width = _line_width(candidate, font, font_path, fallback_font, fallback_path)
        if width <= max_width or not current:
            # keep the word on this line even if it alone overflows —
            # there is nowhere else to put it at this font size
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def fit_text_to_box(text, font_path, fallback_path, start_size, min_size, line_spacing, area_w, area_h):
    """Word-wrap `text` to fit area_w, shrinking the font size (down to
    min_size) until the wrapped block also fits within area_h.

    Returns (font_size, wrapped_lines, font, fallback_font, line_height, gap).
    """
    size = start_size
    while True:
        font = ImageFont.truetype(font_path, size)
        fallback_font = ImageFont.truetype(fallback_path, size) if fallback_path else None

        all_lines = []
        for paragraph in (text.splitlines() or [""]):
            all_lines.extend(_wrap_paragraph(paragraph, font, font_path, fallback_font, fallback_path, area_w))
        if not all_lines:
            all_lines = [""]

        ascent, descent = font.getmetrics()
        line_height = ascent + descent
        gap = size * (line_spacing - 1)
        total_height = line_height * len(all_lines) + gap * (len(all_lines) - 1)

        if total_height <= area_h or size <= min_size:
            return size, all_lines, font, fallback_font, line_height, gap

        size = max(min_size, size - max(1, round(size * 0.06)))


def draw_words(base, text, text_settings):
    font_path = os.path.join(FONTS_DIR, text_settings["font"])
    fallback_path = os.path.join(FONTS_DIR, FALLBACK_FONT_FILE)
    if os.path.normcase(fallback_path) == os.path.normcase(font_path):
        fallback_path = None

    color = hex_to_rgba(text_settings["color"])
    align = text_settings.get("align", "center")
    valign = text_settings.get("valign", "middle")
    line_spacing = text_settings.get("line_spacing", 1.25)

    area_x, area_y = text_settings["x"], text_settings["y"]
    area_w, area_h = text_settings["width"], text_settings["height"]

    start_size = text_settings["font_size"]
    min_size = max(12, round(start_size * 0.35))

    size, all_lines, font, fallback_font, line_height, gap = fit_text_to_box(
        text, font_path, fallback_path, start_size, min_size, line_spacing, area_w, area_h
    )

    draw = ImageDraw.Draw(base)
    line_runs = [
        resolve_line_fonts(shape_line(ln), font, font_path, fallback_font, fallback_path)
        for ln in all_lines
    ]
    line_widths = [sum(f.getlength(ch) for ch, f in run) for run in line_runs]

    total_height = line_height * len(all_lines) + gap * (len(all_lines) - 1)
    if valign == "top":
        cursor_y = area_y
    elif valign == "bottom":
        cursor_y = area_y + area_h - total_height
    else:
        cursor_y = area_y + (area_h - total_height) / 2

    for run, line_w in zip(line_runs, line_widths):
        if align == "left":
            cursor_x = area_x
        elif align == "right":
            cursor_x = area_x + area_w - line_w
        else:
            cursor_x = area_x + (area_w - line_w) / 2

        for ch, ch_font in run:
            draw.text((cursor_x, cursor_y), ch, font=ch_font, fill=color)
            cursor_x += ch_font.getlength(ch)

        cursor_y += line_height + gap


def generate_image(user_image_file, text, settings):
    """Return a finished PIL.Image (RGBA) built from the template.

    The canvas starts fully transparent (like the source template) so the
    exported PNG keeps a transparent background outside the decorative frame.
    """
    base = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    base.alpha_composite(template)

    draw = ImageDraw.Draw(base)
    draw.rectangle(BOX_ERASE_RECT, fill=(0, 0, 0, 0))

    user_img = Image.open(user_image_file)
    draw_photo_box(base, user_img, settings["box"])
    draw_words(base, text, settings["text"])

    return base
