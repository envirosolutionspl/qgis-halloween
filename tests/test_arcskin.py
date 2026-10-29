"""Tests of living next to ArcSkin, played by a stand-in for its widgets."""

import unittest

import qgis_stub
from qgis_stub import PLUGIN_METADATA, FakeIface, QgsSettings, app, flush
from qgis.PyQt.QtCore import QEvent, Qt
from qgis.PyQt.QtGui import QKeyEvent
from qgis.PyQt.QtWidgets import QLineEdit, QToolBar, QToolButton, QWidget

from halloween_skin import arcskin, classFactory, plugin
from test_extras import _Plugin

OTHER = "QWidget { color: #123456; }"  # ArcSkin's style sheet


class FakeArcSkin:
    """What ArcSkin does to the window when it is switched on.

    The style sheet is replaced, the menu bar hidden, a ribbon with a title
    row put on top and a coordinate box placed under the map. Switching
    off undoes it in reverse and restores the sheet it found, as ArcSkin's
    undo log does.
    """

    def __init__(self, iface):
        """Switch the stand-in on."""
        self.win = win = iface.mainWindow()
        self.found = app().styleSheet()
        app().setStyleSheet(OTHER)
        win.menuBar().hide()
        self.ribbon = QToolBar("ArcSkin", win, objectName="ArcSkinRibbonBar")
        self.title = QWidget(objectName=arcskin.TITLE_ROW)
        self.title.setFixedHeight(30)
        self.ribbon.addWidget(self.title)
        win.addToolBar(self.ribbon)
        self.coords = QLineEdit(win, objectName=arcskin.COORDINATES)
        self.coords.show()

    def add_in(self, action):
        """Put ``action`` on a new ribbon button, as the Add-ins tab does."""
        button = QToolButton(self.title)
        button.setDefaultAction(action)
        button.show()
        return button

    def off(self):
        """Switch the stand-in off."""
        self.coords.deleteLater()
        self.win.removeToolBar(self.ribbon)
        self.ribbon.deleteLater()
        self.win.menuBar().show()
        app().setStyleSheet(self.found)
        flush()


class ArcSkinTest(unittest.TestCase):
    """Both plugins on, in either order, and off again."""

    def setUp(self):
        """Start with a plain application and the skin on."""
        QgsSettings.store.clear()
        self.app = app()
        self.app.setStyleSheet("")
        self.iface = FakeIface()
        self.plugin = classFactory(self.iface)
        self.plugin.initGui()

    def tearDown(self):
        """Unload the plugin and restore the application."""
        try:
            self.plugin.unload()
        except (AttributeError, ValueError):  # never loaded, or unloaded
            pass
        self.app.setStyleSheet("")
        self.iface.close()
        flush()

    def settle(self):
        """Let the deferred resync run."""
        flush()
        flush()

    def test_sheet_of_another_plugin_is_kept(self):
        """With ArcSkin first, its sheet stays under the block and after."""
        self.plugin.action.setChecked(False)
        self.app.setStyleSheet(OTHER)
        self.plugin.action.setChecked(True)
        sheet = self.app.styleSheet()
        self.assertTrue(sheet.startswith(OTHER))
        self.assertIn("Nosifer", sheet)
        self.plugin.set_theme("Halloween Dark")
        sheet = self.app.styleSheet()
        self.assertTrue(sheet.startswith(OTHER))
        self.assertEqual(sheet.count(plugin.MARK_BEGIN), 1)
        self.assertIn("Halloween Dark", sheet)
        self.plugin.action.setChecked(False)
        self.assertEqual(self.app.styleSheet(), OTHER)

    def test_block_returns_after_the_sheet_is_replaced(self):
        """Halloween first: ArcSkin's sheet gets the block appended."""
        FakeArcSkin(self.iface)
        self.settle()
        sheet = self.app.styleSheet()
        self.assertTrue(sheet.startswith(OTHER))
        self.assertIn("Nosifer", sheet)
        self.assertEqual(sheet.count(plugin.MARK_BEGIN), 1)

    def test_stale_block_goes_while_off(self):
        """A block restored by ArcSkin's undo is removed while off."""
        other = FakeArcSkin(self.iface)  # the sheet it found has our block
        self.settle()
        self.plugin.action.setChecked(False)
        self.assertEqual(self.app.styleSheet(), OTHER)
        other.off()
        self.settle()
        self.assertEqual(self.app.styleSheet(), "")

    def test_decoration_moves_to_the_title_row_and_back(self):
        """The drawings sit on ArcSkin's title row while the bar is hidden."""
        deco = self.plugin.decoration
        other = FakeArcSkin(self.iface)
        self.settle()
        self.assertIs(deco.host, other.title)
        self.assertIs(deco.overlay.parent(), other.title)
        self.assertTrue(deco.timer.isActive())
        other.off()
        self.settle()
        self.assertIs(deco.host, self.iface.window.menuBar())
        self.assertIs(deco.overlay.parent(), self.iface.window.menuBar())
        self.assertTrue(deco.timer.isActive())

    def test_timer_rests_while_the_bar_is_hidden(self):
        """Without a stand-in, a hidden menu bar stops the frames."""
        deco = self.plugin.decoration
        self.iface.window.menuBar().hide()
        self.settle()
        self.assertFalse(deco.timer.isActive())
        self.iface.window.menuBar().show()
        self.assertTrue(deco.timer.isActive())

    def test_egg_answers_in_arcskin_box(self):
        """The word typed into ArcSkin's coordinate box drops the spiders."""
        other = FakeArcSkin(self.iface)
        self.settle()
        egg = self.plugin.egg
        self.assertIn(other.coords, egg.boxes)
        other.coords.setText("halloween")
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return,
                          Qt.KeyboardModifier.NoModifier)
        self.assertTrue(egg.eventFilter(other.coords, event))
        self.assertIsNotNone(egg.running)
        self.assertEqual(other.coords.text(), "")

    def test_webs_reach_ribbon_buttons(self):
        """Buttons ArcSkin builds for EnviroSolutions actions get the web."""
        ours = _Plugin(self.iface.window)
        qgis_stub.sys.modules["qgis.utils"].plugins["ours"] = ours
        PLUGIN_METADATA["ours"] = {"author": "EnviroSolutions Sp. z o.o."}
        try:
            other = FakeArcSkin(self.iface)
            button = other.add_in(ours.action)
            self.settle()
            self.assertIn(button, self.plugin.webs.buttons)
        finally:
            qgis_stub.sys.modules["qgis.utils"].plugins.clear()
            PLUGIN_METADATA.clear()


if __name__ == "__main__":
    qgis_stub.app()
    unittest.main()
