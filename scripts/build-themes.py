#!/usr/bin/env python3
"""Regenerate the Macquarium theme files from one palette.

Outputs:
  themes/Macquarium.terminal    (macOS Terminal.app profile)
  themes/Macquarium.itermcolors (iTerm2 color preset)

Run from the repo root:  python3 scripts/build-themes.py
Only needed if you change the palette below.
"""
import plistlib
from pathlib import Path

# ---- The deep-sea palette ---------------------------------------------------
PALETTE = {
    "background": "#041C2C",   # deep water
    "foreground": "#BFEFFF",   # light through the surface
    "bold":       "#E6FBFF",
    "cursor":     "#FF9F43",   # clownfish orange
    "selection":  "#0E4D6B",
    "ansi": [
        "#02111B",  # black   - the abyss
        "#FF6B6B",  # red     - coral
        "#3DDC97",  # green   - seaweed
        "#FFD166",  # yellow  - sand / yellow tang
        "#1E90FF",  # blue    - open water
        "#C77DFF",  # magenta - jellyfish
        "#2EE6D6",  # cyan    - lagoon
        "#A9D6E5",  # white   - foam
        "#2B4B5E",  # bright black
        "#FF8E8E",  # bright red
        "#7CF5BE",  # bright green
        "#FFE29A",  # bright yellow
        "#5EB8FF",  # bright blue
        "#DDB3FF",  # bright magenta
        "#7FFFF4",  # bright cyan
        "#E6FBFF",  # bright white
    ],
}
BACKGROUND_ALPHA = 0.12  # see-through so the live tank shows behind the text
BACKGROUND_BLUR = 0.0

ANSI_KEYS = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def archived_color(hex_color, alpha=1.0):
    """NSKeyedArchiver blob for an NSColor, the format Terminal.app stores."""
    r, g, b = rgb(hex_color)
    comps = f"{r:.6f} {g:.6f} {b:.6f}"
    if alpha < 1.0:
        comps += f" {alpha:.6f}"
    archive = {
        "$archiver": "NSKeyedArchiver",
        "$version": 100000,
        "$top": {"root": plistlib.UID(1)},
        "$objects": [
            "$null",
            {
                "NSColorSpace": 1,
                "NSRGB": comps.encode("ascii") + b"\x00",
                "$class": plistlib.UID(2),
            },
            {"$classname": "NSColor", "$classes": ["NSColor", "NSObject"]},
        ],
    }
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY)


def build_terminal(path):
    p = PALETTE
    profile = {
        "name": "Macquarium-Reef",
        "type": "Window Settings",
        "ProfileCurrentVersion": 2.07,
        "BackgroundColor": archived_color(p["background"], BACKGROUND_ALPHA),
        "BackgroundBlur": BACKGROUND_BLUR,
        "TextColor": archived_color(p["foreground"]),
        "TextBoldColor": archived_color(p["bold"]),
        "CursorColor": archived_color(p["cursor"]),
        "SelectionColor": archived_color(p["selection"]),
        "CursorType": 0,
        "CursorBlink": True,
        "UseBrightBold": True,
        "columnCount": 110,
        "rowCount": 32,
        "ShowActiveProcessInTitle": True,
    }
    for i, name in enumerate(ANSI_KEYS):
        profile[f"ANSI{name}Color"] = archived_color(p["ansi"][i])
        profile[f"ANSIBright{name}Color"] = archived_color(p["ansi"][i + 8])
    path.write_bytes(plistlib.dumps(profile, fmt=plistlib.FMT_XML))


def iterm_color(hex_color, alpha=1.0):
    r, g, b = rgb(hex_color)
    return {"Color Space": "sRGB", "Red Component": r, "Green Component": g,
            "Blue Component": b, "Alpha Component": alpha}


def build_iterm(path):
    p = PALETTE
    preset = {f"Ansi {i} Color": iterm_color(c) for i, c in enumerate(p["ansi"])}
    preset.update({
        "Background Color": iterm_color(p["background"]),
        "Foreground Color": iterm_color(p["foreground"]),
        "Bold Color": iterm_color(p["bold"]),
        "Cursor Color": iterm_color(p["cursor"]),
        "Cursor Text Color": iterm_color(p["background"]),
        "Selection Color": iterm_color(p["selection"]),
        "Selected Text Color": iterm_color(p["bold"]),
    })
    path.write_bytes(plistlib.dumps(preset, fmt=plistlib.FMT_XML))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "themes"
    out.mkdir(exist_ok=True)
    build_terminal(out / "Macquarium-Reef.terminal")
    build_iterm(out / "Macquarium.itermcolors")
    print("Built themes in", out)
