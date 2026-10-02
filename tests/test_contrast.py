"""WCAG contrast-ratio checks for every text/bg token pair and chart series on white.

Run:  python -m pytest tests/test_contrast.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from utils.theme import T

def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _relative_luminance(r, g, b):
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def contrast_ratio(fg: str, bg: str) -> float:
    l1 = _relative_luminance(*_hex_to_rgb(fg))
    l2 = _relative_luminance(*_hex_to_rgb(bg))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

# ---------- text on background pairs (>= 4.5:1) ----------

TEXT_PAIRS = [
    ("text on bg",           T["text"],       T["bg"]),
    ("text on surface",      T["text"],       T["surface"]),
    ("text_muted on bg",     T["text_muted"], T["bg"]),
    ("text_muted on surface",T["text_muted"], T["surface"]),
    ("primary on surface",   T["primary"],    T["surface"]),
    ("danger on surface",    T["danger"],     T["surface"]),
    ("warning on surface",   T["warning"],    T["surface"]),
    ("success on surface",   T["success"],    T["surface"]),
    ("danger on danger_tint",T["danger"],     T["danger_tint"]),
    ("warning on warning_tint",T["warning"],  T["warning_tint"]),
    ("success on success_tint",T["success"],  T["success_tint"]),
    ("sidebar_text on sidebar_bg", T["sidebar_text"], T["sidebar_bg"]),
    ("sidebar_muted on sidebar_bg", T["sidebar_muted"], T["sidebar_bg"]),
]

def test_text_contrast():
    failures = []
    for label, fg, bg in TEXT_PAIRS:
        ratio = contrast_ratio(fg, bg)
        if ratio < 4.5:
            failures.append(f"  FAIL {label}: {fg}/{bg} = {ratio:.2f} (need >= 4.5)")
    assert not failures, "Text contrast failures:\n" + "\n".join(failures)

# ---------- graphics / UI on white (>= 3:1) ----------

GRAPHIC_PAIRS = [
    ("primary on surface",  T["primary"],  T["surface"]),
    ("danger on surface",   T["danger"],   T["surface"]),
    ("warning on surface",  T["warning"],  T["surface"]),
    ("success on surface",  T["success"],  T["surface"]),
    # border is decorative, not tested for 3:1
]

# chart series on white
for i, c in enumerate(T["series"]):
    GRAPHIC_PAIRS.append((f"series[{i}] on white", c, "#FFFFFF"))

def test_graphic_contrast():
    failures = []
    for label, fg, bg in GRAPHIC_PAIRS:
        ratio = contrast_ratio(fg, bg)
        if ratio < 3.0:
            failures.append(f"  FAIL {label}: {fg}/{bg} = {ratio:.2f} (need >= 3.0)")
    assert not failures, "Graphic contrast failures:\n" + "\n".join(failures)

if __name__ == "__main__":
    print("Text pairs:")
    for label, fg, bg in TEXT_PAIRS:
        r = contrast_ratio(fg, bg)
        status = "PASS" if r >= 4.5 else "FAIL"
        print(f"  {status} {r:5.2f}:1  {label} ({fg} on {bg})")
    print("\nGraphic pairs:")
    for label, fg, bg in GRAPHIC_PAIRS:
        r = contrast_ratio(fg, bg)
        status = "PASS" if r >= 3.0 else "FAIL"
        print(f"  {status} {r:5.2f}:1  {label} ({fg} on {bg})")
