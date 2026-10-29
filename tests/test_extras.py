"""Tests of the tool cursors, spider webs and the spider easter egg."""

import unittest

import qgis_stub
from qgis_stub import OUT, PLUGIN_METADATA, FakeIface, app
from qgis.PyQt.QtCore import QEvent, QSize, Qt
from qgis.PyQt.QtGui import (QAction, QColor, QIcon, QImage, QKeyEvent,
                             QPixmap)
from qgis.PyQt.QtWidgets import QToolBar, QToolButton

from halloween_skin import cursors, icons, spiders


class CursorsTest(unittest.TestCase):
    """Halloween cursors for the map tools."""

    def setUp(self):
        """Create a main window with map tool actions."""
        app()
        self.iface = FakeIface()

    def tearDown(self):
        """Close the main window."""
        self.iface.close()

    def test_tool_gets_cursor_and_gives_it_back(self):
        """Zoom In gets the pumpkin and QGIS's cursor back on removal."""
        watcher = cursors.ToolCursors(self.iface)
        tool = self.iface.tool("ZoomIn")
        self.iface.canvas.setMapTool(tool)
        self.assertEqual(tool.cursor.shape(), Qt.CursorShape.BitmapCursor)
        self.assertEqual(self.iface.canvas.cursor().shape(),
                         Qt.CursorShape.BitmapCursor)
        watcher.remove()
        self.assertEqual(tool.cursor.theme_name, "ZoomIn")

    def test_pan_returns_to_open_hand(self):
        """Pan has no QGIS theme cursor; it gets the open hand back."""
        watcher = cursors.ToolCursors(self.iface)
        tool = self.iface.tool("Pan")
        self.iface.canvas.setMapTool(tool)
        watcher.remove()
        self.assertEqual(tool.cursor.shape(), Qt.CursorShape.OpenHandCursor)

    def test_other_tools_are_left_alone(self):
        """A tool of another action keeps its cursor."""
        watcher = cursors.ToolCursors(self.iface)
        other = qgis_stub.MapTool(QAction("Measure", self.iface.window))
        self.iface.canvas.setMapTool(other)
        self.assertIsNone(other.cursor)
        watcher.remove()

    def test_current_tool_is_handled_at_once(self):
        """The tool already in use gets its cursor when the skin starts."""
        tool = self.iface.tool("Identify")
        self.iface.canvas.setMapTool(tool)
        watcher = cursors.ToolCursors(self.iface)
        self.assertIsNotNone(tool.cursor)
        watcher.remove()

    def test_cursor_pictures(self):
        """Each cursor picture exists and renders."""
        for _, _, name, hot, _ in cursors.TOOLS:
            cursor = cursors.halloween_cursor(name, hot)
            self.assertFalse(cursor.pixmap().isNull(), name)
            self.assertEqual((cursor.hotSpot().x(), cursor.hotSpot().y()),
                             hot)


class _Plugin:
    """A plugin object as built by Plugin Builder."""

    def __init__(self, window):
        """Create one action on a toolbar of ``window``."""
        self.toolbar = QToolBar("EnviroSolutions", window)
        window.addToolBar(self.toolbar)
        icon = QPixmap(24, 24)
        icon.fill(QColor("#3a7d44"))
        self.action = QAction(QIcon(icon), "Tool", window)
        self.toolbar.addAction(self.action)


class SpiderWebsTest(unittest.TestCase):
    """The web over EnviroSolutions plugin icons."""

    def setUp(self):
        """Register one EnviroSolutions plugin and one by someone else."""
        app()
        self.iface = FakeIface()
        self.ours = _Plugin(self.iface.window)
        self.theirs = _Plugin(self.iface.window)
        qgis_stub.sys.modules["qgis.utils"].plugins.update(
            ours=self.ours, theirs=self.theirs)
        PLUGIN_METADATA.update(ours={"author": "EnviroSolutions Sp. z o.o."},
                               theirs={"author": "Someone Else"})

    def tearDown(self):
        """Forget the fake plugins."""
        qgis_stub.sys.modules["qgis.utils"].plugins.clear()
        PLUGIN_METADATA.clear()
        self.iface.close()

    def button(self, plugin):
        """Return the tool button showing ``plugin``'s action."""
        return plugin.toolbar.widgetForAction(plugin.action)

    def test_only_envirosolutions_buttons(self):
        """The filter goes on EnviroSolutions buttons only."""
        webs = icons.SpiderWebs(self.iface)
        self.assertIn(self.button(self.ours), webs.buttons)
        self.assertNotIn(self.button(self.theirs), webs.buttons)
        webs.remove()

    def test_hover_shows_and_hides_the_web(self):
        """Enter shows the web, Leave puts the plain icon back."""
        webs = icons.SpiderWebs(self.iface)
        button = self.button(self.ours)
        plain = button.icon().cacheKey()
        webs.eventFilter(button, QEvent(QEvent.Type.Enter))
        self.assertNotEqual(button.icon().cacheKey(), plain)
        webs.eventFilter(button, QEvent(QEvent.Type.Leave))
        self.assertEqual(button.icon().cacheKey(), plain)
        webs.remove()

    def test_webbed_preview(self):
        """Paint the webbed icon into a PNG file."""
        icon = self.button(self.ours).icon()
        pixmap = icons.webbed(icon, QSize(48, 48)).pixmap(48, 48)
        OUT.mkdir(exist_ok=True)
        pixmap.save(str(OUT / "web_icon.png"))
        self.assertFalse(pixmap.isNull())
        self.assertIsInstance(self.button(self.ours), QToolButton)


class EasterEggTest(unittest.TestCase):
    """The spiders behind the word *halloween*."""

    def setUp(self):
        """Create a main window with a coordinate box."""
        self.app = app()
        self.iface = FakeIface()

    def tearDown(self):
        """Close the main window."""
        self.iface.close()

    def press_enter(self, egg, text):
        """Type ``text`` into the box and press Enter through the filter."""
        egg.box.setText(text)
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return,
                          Qt.KeyboardModifier.NoModifier)
        return egg.eventFilter(egg.box, event)

    def test_finds_the_coordinate_box(self):
        """The box inside QgsStatusBarCoordinatesWidget is found."""
        box = spiders.coordinate_box(self.iface.window)
        self.assertIs(box, self.iface.coordinates.edit)

    def test_keyword_starts_the_show(self):
        """*halloween* and Enter drop the spiders and clear the box."""
        egg = spiders.EasterEgg(self.iface)
        self.assertTrue(self.press_enter(egg, " Halloween "))
        self.assertIsNotNone(egg.show)
        self.assertEqual(egg.box.text(), "")
        egg.remove()

    def test_coordinates_pass_through(self):
        """Anything else reaches QGIS untouched."""
        egg = spiders.EasterEgg(self.iface)
        self.assertFalse(self.press_enter(egg, "21.0,52.2"))
        self.assertIsNone(egg.show)
        self.assertEqual(egg.box.text(), "21.0,52.2")
        egg.remove()

    def test_spider_timeline(self):
        """A spider comes down, hangs and climbs out of view."""
        import random
        spider = spiders.Spider(random.Random(3), 800, 600, 0)
        self.assertIsNone(spider.pose(spider.start - .1))
        hang = spider.start + spider.descend + spider.hang / 2
        self.assertAlmostEqual(spider.pose(hang)[0], spider.target)
        self.assertIsNone(spider.pose(spider.end + .1))

    def test_preview(self):
        """Paint the spiders while they hang into a PNG file."""
        import random
        canvas = self.iface.canvas
        drop = spiders.SpiderDrop(canvas)
        drop.timer.stop()
        drop.spiders = [spiders.Spider(random.Random(i), canvas.width(),
                                       canvas.height(), i)
                        for i in range(spiders.SPIDERS)]
        t = max(s.start + s.descend + s.hang / 2 for s in drop.spiders)
        drop.seconds = lambda: t
        image = QImage(drop.size(), QImage.Format.Format_ARGB32)
        image.fill(QColor("#e8eef2"))
        drop.render(image)
        OUT.mkdir(exist_ok=True)
        image.save(str(OUT / "spiders.png"))
        dark = sum(1 for x in range(0, image.width(), 2)
                   for y in range(0, image.height(), 2)
                   if QColor(image.pixel(x, y)).lightness() < 40)
        self.assertGreater(dark, 50)
        drop.finish()


if __name__ == "__main__":
    qgis_stub.app()
    unittest.main()
