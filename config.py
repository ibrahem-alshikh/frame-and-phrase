import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_SETTINGS = {
    "box": {
        "x": 77,
        "y": 43,
        "width": 425,
        "height": 425,
        "border_width": 8,
        "border_color": "#8FA28A",
        "corner_radius": 32,
        "fit_mode": "cover",
        "background_color": "#FBE4A8",
    },
    "text": {
        "x": 505,
        "y": 32,
        "width": 490,
        "height": 446,
        "font": "calibrib.ttf",
        "font_size": 72,
        "color": "#17433F",
        "align": "center",
        "valign": "middle",
        "line_spacing": 1.25,
    },
}


def load_settings():
    if not os.path.exists(CONFIG_PATH):
        save_settings(DEFAULT_SETTINGS)
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # backfill any missing keys from defaults (e.g. after an upgrade)
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    for section in ("box", "text"):
        merged[section].update(data.get(section, {}))
    return merged


def save_settings(settings):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
