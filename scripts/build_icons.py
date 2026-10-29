"""Generate the cursor pictures and the spider web of Halloween Skin.

Writes into ``halloween_skin/icons/``:

* ``tool_pan.svg`` (ghost), ``tool_select.svg`` (witch's broom),
  ``tool_zoom_in.svg`` / ``tool_zoom_out.svg`` (large and small pumpkin)
  and ``tool_identify.svg`` (bat) - the map tool cursors;
* ``web.svg`` - the spider web painted over EnviroSolutions plugin icons.

The ghost, pumpkin and bat are the menu-bar drawings of
``halloween_skin/animation.py``. Only the subset of SVG Tiny that Qt
renders is used (no masks, filters, CSS or animation).

Usage::

    python scripts/build_icons.py
"""

import math
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parent.parent / "halloween_skin" / "icons"
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
       'viewBox="0 0 24 24">{}</svg>')

GHOST = ('<path d="M-18 24 L-18 -4 C-18 -18 -9 -26 0 -26 C9 -26 18 -18 18 -4 '
         'L18 24 L12 18 L6 24 L0 18 L-6 24 L-12 18 Z" fill="#ffffff" '
         'stroke="#8b5cc4" stroke-width="1.5"/>'
         '<ellipse cx="-6" cy="-6" rx="3" ry="4.5" fill="#1a0f1f"/>'
         '<ellipse cx="6" cy="-6" rx="3" ry="4.5" fill="#1a0f1f"/>'
         '<ellipse cx="0" cy="5" rx="3.5" ry="4" fill="#1a0f1f"/>')
PUMPKIN = ('<path d="M-2 -26 C-2 -34 4 -38 8 -40" stroke="#3d5a1e" '
           'stroke-width="5" fill="none" stroke-linecap="round"/>'
           '<ellipse cx="-16" cy="0" rx="18" ry="24" fill="#e2600c"/>'
           '<ellipse cx="16" cy="0" rx="18" ry="24" fill="#e2600c"/>'
           '<ellipse cx="0" cy="0" rx="20" ry="26" fill="#ff7a1a"/>'
           '<path d="M-6 -24 C-10 -8 -10 8 -6 24 M6 -24 C10 -8 10 8 6 24" '
           'stroke="#e2600c" stroke-width="2" fill="none"/>'
           '<path d="M-15 -7 L-8 -15 L-3 -6 Z M15 -7 L8 -15 L3 -6 Z" '
           'fill="#ffd23f"/>'
           '<path d="M-16 6 L-11 12 L-6 7 L0 13 L6 7 L11 12 L16 6 L13 15 '
           'C6 20 -6 20 -13 15 Z" fill="#ffd23f"/>')
BAT = ('<path d="M0 -4 C-6 -14 -18 -16 -30 -10 C-26 -8 -25 -4 -26 0 '
       'C-22 -2 -18 -1 -16 2 C-12 -1 -8 0 -6 4 C-4 2 -2 2 0 4 C2 2 4 2 6 4 '
       'C8 0 12 -1 16 2 C18 -1 22 -2 26 0 C25 -4 26 -8 30 -10 '
       'C18 -16 6 -14 0 -4 Z" fill="#2a1540" stroke="#8b5cc4" '
       'stroke-width="2"/>'
       '<path d="M-3 -6 L-2 -10 L0 -7 L2 -10 L3 -6 Z" fill="#2a1540"/>'
       '<circle cx="-1.3" cy="-4" r="1.2" fill="#ffd23f"/>'
       '<circle cx="1.3" cy="-4" r="1.2" fill="#ffd23f"/>')
BROOM = ('<g transform="rotate(45 12 12)">'
         '<rect x="11" y="1" width="2.4" height="13" rx="1" fill="#8a5a2b" '
         'stroke="#5b3a18" stroke-width=".6"/>'
         '<rect x="9.4" y="13" width="5.6" height="2.2" rx=".6" '
         'fill="#d9a441" stroke="#8a6a1f" stroke-width=".5"/>'
         '<path d="M9.6 15.2 L7.2 23 L9.4 22.6 L10.6 23.2 L12.2 22.4 '
         'L13.8 23.2 L15 22.6 L17.2 23 L14.8 15.2 Z" fill="#e8b94f" '
         'stroke="#8a6a1f" stroke-width=".6" stroke-linejoin="round"/>'
         '<path d="M10.6 16 L9.6 22 M12.2 16 L12.2 22 M13.8 16 L14.8 22" '
         'stroke="#b58a2a" stroke-width=".6" fill="none"/></g>')

# Spider web in the top-left corner: spokes every WEB_STEP degrees and
# rings whose threads sag towards the corner.
WEB_SPOKES = 6
WEB_STEP = 18            # degrees between spokes (0 .. 90)
WEB_SPOKE_LENGTH = 25.2
WEB_RINGS = (5.0, 9.5, 14.0, 18.5, 23.0)
WEB_SAG = 0.909          # control point radius relative to the ring
WEB_SPIDER = ('<g fill="#1a0f1f"><circle cx="15.5" cy="13.5" r="1.7"/>'
              '<circle cx="15.5" cy="11.6" r="1"/>'
              '<path d="M13.9 13 L11.8 11.4 M13.9 13.8 L11.6 14.2 '
              'M14.2 14.7 L12.4 16.6 M17.1 13 L19.2 11.4 M17.1 13.8 '
              'L19.4 14.2 M16.8 14.7 L18.6 16.6" stroke="#1a0f1f" '
              'stroke-width=".7" fill="none"/></g>')


def polar(radius, degrees):
    """Return the point at ``radius`` and ``degrees`` as ``"x y"``.

    :param radius: distance from the corner.
    :param degrees: angle from the top edge towards the left edge.
    :returns: coordinates rounded to one decimal place.
    """
    a = math.radians(degrees)
    return "%.1f %.1f" % (radius * math.cos(a), radius * math.sin(a))


def web():
    """Build the spider web picture.

    :returns: the SVG document as a string.
    """
    spokes = "".join(
        '<path d="M0 0 L%s"/>' % polar(WEB_SPOKE_LENGTH, i * WEB_STEP)
        for i in range(WEB_SPOKES))
    rings = []
    for radius in WEB_RINGS:
        segments = []
        for i in range(WEB_SPOKES - 1):
            start, end = i * WEB_STEP, (i + 1) * WEB_STEP
            segments.append("M%s Q%s %s" % (
                polar(radius, start),
                polar(radius * WEB_SAG, (start + end) / 2),
                polar(radius, end)))
        rings.append('<path d="%s"/>' % " ".join(segments))
    threads = ('<g stroke="#f4ecff" stroke-opacity=".9" stroke-width=".8" '
               'fill="none" stroke-linecap="round">%s%s</g>'
               % (spokes, "".join(rings)))
    return SVG.format(threads + WEB_SPIDER)


def pictures():
    """Return every generated picture.

    :returns: a dict mapping file names to SVG documents.
    """
    return {
        "tool_pan.svg": SVG.format(
            '<g transform="translate(12 12) scale(.42)">%s</g>' % GHOST),
        "tool_select.svg": SVG.format(BROOM),
        "tool_zoom_in.svg": SVG.format(
            '<g transform="translate(12 14) scale(0.42)">%s</g>' % PUMPKIN),
        "tool_zoom_out.svg": SVG.format(
            '<g transform="translate(12 14) scale(0.27)">%s</g>' % PUMPKIN),
        "tool_identify.svg": SVG.format(
            '<g transform="translate(12 13) scale(.36)">%s</g>' % BAT),
        "web.svg": web(),
    }


def main():
    """Write the pictures into the plugin's ``icons`` folder."""
    for name, text in pictures().items():
        (ICON_DIR / name).write_text(text, encoding="utf-8", newline="\n")
        print("wrote", ICON_DIR / name)


if __name__ == "__main__":
    main()
