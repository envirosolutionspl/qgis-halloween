"""Generate the starry sky behind the Halloween menu bar.

Writes ``stars.svg`` into every theme folder under
``halloween_skin/themes/``. The style sheets place it at the top right of
the menu bar (``background-image: url(@theme_path/stars.svg)``), over the
violet gradient. The stars are random but always the same, because the
generator is seeded.

Usage::

    python scripts/build_stars.py
"""

import random
from pathlib import Path

THEMES_DIR = (Path(__file__).resolve().parent.parent / "halloween_skin"
              / "themes")
WIDTH, HEIGHT = 1600, 36   # wider than any menu bar; as tall as the bar
COUNT = 170
SEED = 31
STAR = ('<circle cx="{x}" cy="{y:.1f}" r="{r:.1f}" fill="#ffffff" '
        'opacity="{opacity:.2f}"/>')


def stars(seed=SEED, count=COUNT):
    """Build the star picture.

    :param seed: seed of the random generator.
    :param count: number of stars.
    :returns: the SVG document as a string.
    """
    rnd = random.Random(seed)
    circles = []
    for _ in range(count):
        circles.append(STAR.format(
            x=round(rnd.uniform(0, WIDTH)),
            y=rnd.uniform(1, HEIGHT - 1),
            r=rnd.uniform(.5, 1.3),
            opacity=rnd.uniform(.35, .9)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
            'height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'
            .format(w=WIDTH, h=HEIGHT, body="".join(circles)))


def main():
    """Write ``stars.svg`` into each theme folder."""
    text = stars()
    for folder in sorted(p for p in THEMES_DIR.iterdir() if p.is_dir()):
        target = folder / "stars.svg"
        target.write_text(text, encoding="utf-8", newline="\n")
        print("wrote", target)


if __name__ == "__main__":
    main()
