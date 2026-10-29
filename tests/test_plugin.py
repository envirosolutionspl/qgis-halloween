"""Tests of the plugin: themes, switching on and off, settings."""

import re
import unittest

import qgis_stub
from qgis_stub import FakeIface, QgsSettings, app
from PyQt5.QtGui import QFontDatabase, QPalette
from PyQt5.QtWidgets import QWidget

from halloween_skin import classFactory, plugin


class ThemeFilesTest(unittest.TestCase):
    """The theme folders are complete and well formed."""

    def test_every_theme_has_its_files(self):
        """Each theme has a style sheet, a palette and the stars."""
        for theme in plugin.THEMES:
            folder = plugin.THEMES_DIR / theme
            for name in ("style.qss", "palette.txt", "stars.svg"):
                self.assertTrue((folder / name).is_file(), (theme, name))

    def test_style_sheet_refers_to_existing_files(self):
        """Every ``url()`` in a style sheet points to an existing file."""
        for theme in plugin.THEMES:
            qss = plugin.load_style(theme)
            self.assertNotIn("@theme_path", qss)
            for url in re.findall(r"url\(([^)]+)\)", qss):
                self.assertTrue(plugin.Path(url).is_file(), (theme, url))

    def test_style_sheet_braces_balance(self):
        """Blocks of the style sheets are closed."""
        for theme in plugin.THEMES:
            qss = plugin.load_style(theme)
            self.assertEqual(qss.count("{"), qss.count("}"), theme)

    def test_palette_sets_known_roles(self):
        """``palette.txt`` lines name known roles and valid colours."""
        app()
        base = QPalette()
        for theme in plugin.THEMES:
            path = plugin.THEMES_DIR / theme / "palette.txt"
            for line in path.read_text(encoding="utf-8").splitlines():
                number, colour = line.split(":", 1)
                self.assertIn(int(number), plugin.ROLES, (theme, line))
            palette = plugin.load_palette(theme, base)
            self.assertNotEqual(
                palette.color(QPalette.ColorRole.Window).name(),
                base.color(QPalette.ColorRole.Window).name(), theme)

    def test_dark_theme_has_light_text_on_dark_window(self):
        """The dark palette keeps text readable."""
        palette = plugin.load_palette("Halloween Dark", QPalette())
        window = palette.color(QPalette.ColorRole.Window).lightness()
        text = palette.color(QPalette.ColorRole.WindowText).lightness()
        self.assertGreater(text, window + 100)


class TranslationTest(unittest.TestCase):
    """Menu captions follow the QGIS language."""

    def tearDown(self):
        """Forget the locale set by the test."""
        QgsSettings.store.pop("locale/userLocale", None)

    def test_polish(self):
        """Polish QGIS gets Polish captions."""
        QgsSettings().setValue("locale/userLocale", "pl_PL")
        self.assertEqual(plugin.tr("Theme"), "Motyw")

    def test_english(self):
        """Any other language gets English captions."""
        QgsSettings().setValue("locale/userLocale", "en_GB")
        self.assertEqual(plugin.tr("Theme"), "Theme")

    def test_every_caption_is_translated(self):
        """Captions used in the menu all have a Polish entry."""
        for caption in ("Halloween look", "Theme", "Animation", "Off",
                        "In place, as in MAIP", "Flying across the menu bar",
                        *plugin.THEMES):
            self.assertIn(caption, plugin.POLISH)


class PluginTest(unittest.TestCase):
    """Switching the skin on and off."""

    def setUp(self):
        """Start with empty settings and a fresh main window."""
        QgsSettings.store.clear()
        self.app = app()
        self.app.setStyleSheet("QWidget { color: #123456; }")
        self.palette = QPalette(self.app.palette())
        self.iface = FakeIface()
        self.plugin = classFactory(self.iface)

    def tearDown(self):
        """Unload the plugin and restore the application."""
        try:
            self.plugin.unload()
        except (AttributeError, ValueError):  # never loaded, or unloaded
            pass
        self.app.setStyleSheet("")
        self.iface.close()

    def test_on_by_default(self):
        """A fresh install shows the skin and builds the menu."""
        self.plugin.initGui()
        self.assertTrue(self.plugin.action.isChecked())
        self.assertIn("Nosifer", self.app.styleSheet())
        self.assertIsNotNone(self.plugin.decoration)
        self.assertEqual(len(self.iface.plugin_menus[plugin.MENU_NAME]), 3)
        self.assertIn("Nosifer", QFontDatabase().families())

    def test_off_restores_style_and_palette(self):
        """Switching off puts back what the application had."""
        self.plugin.initGui()
        self.plugin.action.setChecked(False)
        self.assertEqual(self.app.styleSheet(),
                         "QWidget { color: #123456; }")
        self.assertEqual(self.app.palette().color(QPalette.ColorRole.Window),
                         self.palette.color(QPalette.ColorRole.Window))
        self.assertIsNone(self.plugin.decoration)
        self.assertIsNone(self.plugin.cursors)
        self.assertIsNone(self.plugin.webs)
        self.assertIsNone(self.plugin.egg)
        self.assertFalse(QgsSettings().value(plugin.ENABLED_KEY))

    def test_off_is_remembered(self):
        """The skin stays off after a restart if it was switched off."""
        QgsSettings().setValue(plugin.ENABLED_KEY, False)
        self.plugin.initGui()
        self.assertFalse(self.plugin.action.isChecked())
        self.assertEqual(self.app.styleSheet(),
                         "QWidget { color: #123456; }")

    def test_unload_keeps_the_setting(self):
        """Unloading takes the skin off without storing *off*."""
        self.plugin.initGui()
        self.plugin.unload()
        self.assertTrue(QgsSettings().value(plugin.ENABLED_KEY))
        self.assertNotIn("Nosifer", self.app.styleSheet())
        self.assertEqual(self.iface.plugin_menus[plugin.MENU_NAME], [])

    def test_theme_change(self):
        """Choosing a theme applies and remembers it."""
        self.plugin.initGui()
        self.plugin.set_theme("Halloween Dark")
        self.assertEqual(QgsSettings().value(plugin.THEME_KEY),
                         "Halloween Dark")
        self.assertIn("Halloween Dark", self.app.styleSheet())
        dark = [a for a in self.plugin.theme_menu.actions()
                if a.isChecked()]
        self.assertEqual([a.data() for a in dark], ["Halloween Dark"])

    def test_unknown_theme_and_mode_are_ignored(self):
        """Stored nonsense falls back to the defaults."""
        QgsSettings().setValue(plugin.THEME_KEY, "Christmas")
        QgsSettings().setValue(plugin.ANIMATION_KEY, "spin")
        self.assertEqual(self.plugin.theme(), plugin.THEMES[0])
        self.assertEqual(self.plugin.animation_mode(), "flight")
        self.plugin.initGui()
        self.plugin.set_theme("Christmas")
        self.plugin.set_animated("spin")
        self.assertEqual(QgsSettings().value(plugin.THEME_KEY), "Christmas")

    def test_animation_change(self):
        """Choosing an animation mode switches the decoration."""
        self.plugin.initGui()
        self.plugin.set_animated("off")
        self.assertEqual(self.plugin.decoration.mode, "off")
        self.assertFalse(self.plugin.decoration.timer.isActive())
        self.assertEqual(QgsSettings().value(plugin.ANIMATION_KEY), "off")

    def test_repeated_switching(self):
        """On, off, on, off leaves the application as it was."""
        self.plugin.initGui()
        for state in (False, True, False, True, False):
            self.plugin.action.setChecked(state)
        self.assertEqual(self.app.styleSheet(),
                         "QWidget { color: #123456; }")
        overlays = [w for w in self.iface.window.menuBar().findChildren(
            QWidget) if type(w).__name__ == "_Overlay" and w.isVisible()]
        self.assertEqual(overlays, [])


if __name__ == "__main__":
    qgis_stub.app()
    unittest.main()
