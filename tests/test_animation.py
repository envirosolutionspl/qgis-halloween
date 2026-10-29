"""Tests of the menu-bar decoration; previews go to ``tests/out``."""

import unittest

import qgis_stub
from qgis_stub import OUT, app
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QImage, QPainter
from qgis.PyQt.QtWidgets import QMenuBar

from halloween_skin import animation, plugin


def render(widget, seconds, path=None):
    """Render ``widget`` with the decoration at ``seconds``."""
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("#160c22"))
    widget.render(image)
    if path is not None:
        OUT.mkdir(exist_ok=True)
        image.save(str(path))
    return image


class PathTest(unittest.TestCase):
    """The SVG path reader."""

    def test_lines(self):
        """A closed triangle has the expected bounds."""
        rect = animation.path("M0 0 L10 0 L10 5 Z").boundingRect()
        self.assertEqual((rect.width(), rect.height()), (10, 5))

    def test_smooth_curve(self):
        """``S`` mirrors the previous control point."""
        out = animation.path("M0 0 C0 10 10 10 10 0 S20 -10 20 0")
        self.assertAlmostEqual(out.currentPosition().x(), 20)
        self.assertLess(out.boundingRect().top(), -5)

    def test_drawings_are_not_empty(self):
        """Every drawing of the set parses into a shape."""
        for shape in (animation.BAT_BODY, animation.GHOST_BODY,
                      animation.PUMPKIN_MOUTH, animation.PUMPKIN_EYES):
            self.assertFalse(shape.isEmpty())


class CycleTest(unittest.TestCase):
    """Timing helpers copied from the CSS animations."""

    def test_eased_range(self):
        """The eased value stays within 0..1 and reaches both ends."""
        cycle = animation.Cycle((1.0, 1.0))
        values = [cycle.eased(i / 100) for i in range(200)]
        self.assertGreaterEqual(min(values), 0)
        self.assertLessEqual(max(values), 1)
        self.assertGreater(max(values), .99)
        self.assertLess(min(values), .01)

    def test_same_layout_same_timing(self):
        """The set is laid out the same way each time."""
        first = [getattr(d, "pulse", getattr(d, "flap", None))
                 for d in animation.decorations(240)]
        second = [getattr(d, "pulse", getattr(d, "flap", None))
                  for d in animation.decorations(240)]
        self.assertEqual([c.duration for c in first if c],
                         [c.duration for c in second if c])

    def test_flicker_keyframes(self):
        """The face is fully lit at the ends of its cycle."""
        self.assertEqual(animation.flicker(0), 1)
        self.assertEqual(animation.flicker(1), 1)
        self.assertAlmostEqual(animation.flicker(.47), .7)


class FlyerTest(unittest.TestCase):
    """Bats and ghosts crossing the bar."""

    def test_crosses_and_returns(self):
        """A bat flies across, disappears and comes back."""
        import random
        flyer = animation.Flyer("bat", random.Random(5), 800, 36)
        seen_alive = seen_gone = False
        for _ in range(2000):
            flyer.advance(.04)
            if flyer.alive:
                seen_alive = True
                self.assertTrue(-60 < flyer.x < 860)
            elif seen_alive:
                seen_gone = True
        self.assertTrue(seen_alive and seen_gone)


class DecorationTest(unittest.TestCase):
    """The overlay on a styled menu bar."""

    def setUp(self):
        """Create a menu bar styled like the Light theme."""
        self.app = app()
        self.bar = QMenuBar()
        self.bar.setStyleSheet(plugin.load_style("Halloween Light"))
        for name in ("Project", "Edit", "View", "Layer", "Plugins"):
            self.bar.addMenu(name)
        self.bar.resize(900, 38)
        self.bar.show()

    def tearDown(self):
        """Close the menu bar."""
        qgis_stub.dispose(self.bar)

    def test_modes(self):
        """Each mode sizes the overlay and runs the timer as expected."""
        deco = animation.MenuBarDecoration(self.bar, "gentle")
        self.assertEqual(deco.overlay.width(), animation.BAND_WIDTH)
        self.assertTrue(deco.timer.isActive())
        deco.set_mode("flight")
        self.assertEqual(deco.overlay.width(), self.bar.width())
        self.assertEqual(len(deco.flyers),
                         animation.MAX_BATS + animation.MAX_GHOSTS)
        deco.set_mode("off")
        self.assertFalse(deco.timer.isActive())
        deco.remove()

    def test_overlay_lets_the_mouse_through(self):
        """Clicks reach the menu bar under the overlay."""
        deco = animation.MenuBarDecoration(self.bar, "flight")
        self.assertTrue(deco.overlay.testAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        deco.remove()

    def test_resize_follows_the_bar(self):
        """The overlay follows the menu bar's width."""
        deco = animation.MenuBarDecoration(self.bar, "flight")
        self.bar.resize(600, 38)
        self.app.processEvents()
        self.assertEqual(deco.overlay.width(), 600)
        deco.remove()

    def test_previews(self):
        """Paint the modes into PNG files and check something is drawn."""
        for mode in animation.MODES:
            deco = animation.MenuBarDecoration(self.bar, mode)
            for flyer in deco.flyers:
                flyer.wait = 0
                flyer.advance(0)
                flyer.x = flyer.width / 2
                flyer.advance(.01)
            image = render(self.bar, 0, OUT / "menubar_{}.png".format(mode))
            orange = sum(
                1 for x in range(image.width() - 240, image.width())
                for y in range(image.height())
                if QColor(image.pixel(x, y)).red() > 200
                and QColor(image.pixel(x, y)).blue() < 80)
            self.assertGreater(orange, 50, mode)
            deco.remove()

    def test_frames(self):
        """Paint a few frames of the decoration on its own."""
        items = animation.decorations(animation.BAND_WIDTH)
        image = QImage(animation.BAND_WIDTH, 36,
                       QImage.Format.Format_ARGB32)
        for i, seconds in enumerate((0, .3, .6)):
            image.fill(QColor("#2d1246"))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for item in items:
                item.paint(painter, seconds, True)
            painter.end()
            OUT.mkdir(exist_ok=True)
            image.save(str(OUT / "frame_{}.png".format(i)))


if __name__ == "__main__":
    qgis_stub.app()
    unittest.main()
