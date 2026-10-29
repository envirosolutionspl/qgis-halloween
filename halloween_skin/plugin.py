"""Halloween look for the standard QGIS interface (QGIS 3.40 - 4.x).

A theme is a folder under ``themes/<name>/`` in the same format as a QGIS
UI theme: ``style.qss`` (``@theme_path`` stands for the folder), optional
``palette.txt`` (lines ``<QPalette::ColorRole number>:<colour>``) and the
files they refer to. The plugin applies the chosen theme to the running
application and takes it off again when it is switched off, so nothing is
written into the QGIS profile.

The style sheet is not put in place of the application's but appended to
it as a block between :data:`MARK_BEGIN` and :data:`MARK_END`, and only
that block is removed on switching off: another plugin that styles QGIS
(ArcSkin) keeps its rules whatever the order the two are switched. Should
such a plugin replace the whole sheet, Qt's ``StyleChange`` event on the
main window brings the block back - or removes a stale copy of it that the
other plugin restored while the skin is off.
"""

import re
from pathlib import Path

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import (QCoreApplication, QEvent, QLocale, QObject,
                              QTimer)
from qgis.PyQt.QtGui import (QAction, QActionGroup, QColor, QFontDatabase,
                             QIcon, QPalette)
from qgis.PyQt.QtWidgets import QApplication, QMenu

from . import arcskin
from .animation import MODES, MenuBarDecoration
from .cursors import ToolCursors
from .icons import SpiderWebs
from .spiders import EasterEgg

PLUGIN_DIR = Path(__file__).resolve().parent
THEMES_DIR = PLUGIN_DIR / "themes"
THEMES = ("Halloween Light", "Halloween Dark")
MENU_NAME = "&Halloween Skin"
ENABLED_KEY = "halloween_skin/enabled"
THEME_KEY = "halloween_skin/theme"
ANIMATION_KEY = "halloween_skin/animation"
FONT_FILE = PLUGIN_DIR / "fonts" / "Nosifer-Regular.ttf"
# The plugin's part of the application style sheet lies between these.
MARK_BEGIN = "/* halloween_skin: begin */"
MARK_END = "/* halloween_skin: end */"
BLOCK_RE = re.compile(r"\n?" + re.escape(MARK_BEGIN) + ".*?"
                      + re.escape(MARK_END), re.DOTALL)
# Appended to every theme: the Halloween face on the menu bar, pane titles
# and the welcome page's headings.
EXTRA_QSS = """
QMenuBar { font-family: "Nosifer"; font-size: 7pt; }
QMenuBar::item { padding: 12px 9px 7px 9px; }
QDockWidget { font-family: "Nosifer"; font-size: 7pt; }
QgsWelcomePage > QLabel { font-family: "Nosifer"; }
"""
# QPalette::ColorRole numbers used in palette.txt (Qt 5 and Qt 6 agree).
ROLES = {
    0: "WindowText", 1: "Button", 2: "Light", 3: "Midlight", 4: "Dark",
    5: "Mid", 6: "Text", 7: "BrightText", 8: "ButtonText", 9: "Base",
    10: "Window", 11: "Shadow", 12: "Highlight", 13: "HighlightedText",
    14: "Link", 15: "LinkVisited", 16: "AlternateBase", 18: "ToolTipBase",
    19: "ToolTipText", 20: "PlaceholderText",
}
POLISH = {
    "Halloween look": "Wygląd Halloween",
    "Theme": "Motyw",
    "Animation": "Animacja",
    "Off": "Wyłączona",
    "In place, as in MAIP": "W miejscu, jak w MAIP",
    "Flying across the menu bar": "Przelot przez pasek menu",
    "Halloween Light": "Halloween – jasny",
    "Halloween Dark": "Halloween – ciemny",
}


def tr(text):
    """Translate a menu caption.

    QGIS set to Polish gets the entry from :data:`POLISH`; any other
    language goes through Qt's translator (English by default).

    :param text: the English caption.
    :returns: the caption in the user's language.
    """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())
    if str(locale).startswith("pl"):
        return POLISH.get(text, text)
    return QCoreApplication.translate("HalloweenSkin", text)


def load_style(theme):
    """Read a theme's style sheet.

    :param theme: theme name, one of :data:`THEMES`.
    :returns: the contents of ``style.qss`` with ``@theme_path`` replaced
        by the theme folder and :data:`EXTRA_QSS` appended.
    """
    folder = THEMES_DIR / theme
    qss = (folder / "style.qss").read_text(encoding="utf-8")
    return qss.replace("@theme_path", folder.as_posix()) + EXTRA_QSS


def has_skin(sheet):
    """Tell whether ``sheet`` holds the plugin's block.

    :param sheet: an application style sheet.
    """
    return MARK_BEGIN in sheet


def without_skin(sheet):
    """Return ``sheet`` with the plugin's block taken out.

    :param sheet: an application style sheet.
    :returns: the sheet as it was before the block was appended.
    """
    return BLOCK_RE.sub("", sheet)


def with_skin(sheet, theme):
    """Return ``sheet`` with the block of ``theme`` appended.

    A block already there is replaced, so changing themes never stacks
    one theme on another.

    :param sheet: an application style sheet.
    :param theme: theme name, one of :data:`THEMES`.
    """
    base = without_skin(sheet)
    block = "\n".join((MARK_BEGIN, load_style(theme), MARK_END))
    return base + "\n" + block if base else block


def load_palette(theme, base):
    """Build the palette of a theme.

    :param theme: theme name, one of :data:`THEMES`.
    :param base: palette to start from (the application's own).
    :returns: a copy of ``base`` with the colours of the theme's
        ``palette.txt`` applied; ``base`` unchanged if there is no file.
    """
    palette = QPalette(base)
    path = THEMES_DIR / theme / "palette.txt"
    if not path.exists():
        return palette
    role = QPalette.ColorRole
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        number, colour = line.split(":", 1)
        name = ROLES.get(int(number.strip()))
        if name and hasattr(role, name):
            palette.setColor(getattr(role, name), QColor(colour.strip()))
    return palette


class StyleSync(QObject):
    """Call back once the application style sheet has been changed.

    Qt sends every widget a ``StyleChange`` event when the application's
    style sheet is set; watching the main window for it tells when another
    plugin (ArcSkin) has replaced the sheet. The call is deferred to the
    next turn of the event loop, so the other plugin has finished building
    its widgets by then, and several changes in a row give one call.
    """

    def __init__(self, win, callback):
        """Watch ``win`` and call ``callback`` after a style change.

        :param win: the QGIS main window.
        :param callback: called with no arguments.
        """
        super().__init__(win)
        self.callback = callback
        self.pending = False
        win.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API name)
        """Schedule the callback on ``StyleChange``; nothing is consumed."""
        if event.type() == QEvent.Type.StyleChange and not self.pending:
            self.pending = True
            QTimer.singleShot(0, self._fire)
        return False

    def _fire(self):
        """Run the callback (on the event loop's next turn)."""
        self.pending = False
        self.callback()

    def remove(self):
        """Stop watching and delete this object."""
        win = self.parent()
        if win is not None:
            win.removeEventFilter(self)
        self.deleteLater()


class HalloweenSkinPlugin:
    """The plugin: the *Halloween Skin* menu and the skin itself.

    The menu holds the on/off switch, the theme and the animation mode;
    all three are kept in :class:`QgsSettings`. While the skin is on, the
    plugin owns the menu-bar decoration, the tool cursors, the spider webs
    and the easter egg, and removes them when it is switched off.
    """

    def __init__(self, iface):
        """Keep ``iface``; nothing is shown before :meth:`initGui`.

        :param iface: the QGIS interface (``QgisInterface``).
        """
        self.iface = iface
        self.active = False  # the skin is on
        self.palette_before = None  # the application's palette before it
        self.sync = None  # StyleSync while the plugin is loaded
        self.decoration = None  # overlay on the menu bar while the skin is on
        self.cursors = None
        self.webs = None
        self.egg = None
        self.font_id = -1

    def initGui(self):  # noqa: N802 (QGIS API name)
        """Build the menu and switch the skin on if it was left on."""
        win = self.iface.mainWindow()
        self.action = QAction(QIcon(str(PLUGIN_DIR / "icons" / "icon.svg")),
                              tr("Halloween look"), win, checkable=True)
        self.action.toggled.connect(self.set_enabled)
        self.iface.addPluginToMenu(MENU_NAME, self.action)
        self.theme_menu = QMenu(tr("Theme"), win)
        group = QActionGroup(self.theme_menu)
        group.setExclusive(True)
        chosen = self.theme()
        for name in THEMES:
            action = QAction(tr(name), self.theme_menu, checkable=True)
            action.setData(name)
            action.setChecked(name == chosen)
            group.addAction(action)
            self.theme_menu.addAction(action)
        group.triggered.connect(lambda action: self.set_theme(action.data()))
        self.iface.addPluginToMenu(MENU_NAME, self.theme_menu.menuAction())
        settings = QgsSettings()
        self.animation_menu = QMenu(tr("Animation"), win)
        modes = QActionGroup(self.animation_menu)
        modes.setExclusive(True)
        for mode, caption in (("off", "Off"),
                              ("gentle", "In place, as in MAIP"),
                              ("flight", "Flying across the menu bar")):
            action = QAction(tr(caption), self.animation_menu,
                             checkable=True)
            action.setData(mode)
            action.setChecked(mode == self.animation_mode())
            modes.addAction(action)
            self.animation_menu.addAction(action)
        modes.triggered.connect(lambda action: self.set_animated(
            action.data()))
        self.iface.addPluginToMenu(MENU_NAME,
                                   self.animation_menu.menuAction())
        self.sync = StyleSync(win, self.resync)
        if settings.value(ENABLED_KEY, True, type=bool):
            self.action.setChecked(True)

    def unload(self):
        """Take the skin off and remove the menu; called by QGIS.

        The on/off setting is left as it was, so the skin comes back the
        next time the plugin is loaded.
        """
        try:
            self.set_enabled(False, remember=False)
        finally:
            if self.sync is not None:
                self.sync.remove()
                self.sync = None
            self.iface.removePluginMenu(MENU_NAME, self.action)
            self.iface.removePluginMenu(MENU_NAME,
                                        self.theme_menu.menuAction())
            self.iface.removePluginMenu(MENU_NAME,
                                        self.animation_menu.menuAction())

    def theme(self):
        """Return the theme chosen in the settings.

        :returns: a name from :data:`THEMES`; the first one if the stored
            value is missing or unknown.
        """
        theme = QgsSettings().value(THEME_KEY, THEMES[0])
        return theme if theme in THEMES else THEMES[0]

    def set_theme(self, theme):
        """Remember ``theme`` and apply it at once if the skin is on.

        :param theme: theme name; anything not in :data:`THEMES` is
            ignored.
        """
        if theme not in THEMES:
            return
        QgsSettings().setValue(THEME_KEY, theme)
        for action in self.theme_menu.actions():
            action.setChecked(action.data() == theme)
        if self.active:
            self._apply(theme)

    def animation_mode(self):
        """Return the animation mode chosen in the settings.

        :returns: one of :data:`~.animation.MODES` (``off``, ``gentle``
            or ``flight``); ``flight`` if the stored value is unknown.
        """
        mode = QgsSettings().value(ANIMATION_KEY, "flight")
        return mode if mode in MODES else "flight"

    def set_animated(self, mode):
        """Remember the animation ``mode`` and switch the decoration to it.

        :param mode: one of :data:`~.animation.MODES`; anything else is
            ignored.
        """
        if mode not in MODES:
            return
        QgsSettings().setValue(ANIMATION_KEY, mode)
        for action in self.animation_menu.actions():
            action.setChecked(action.data() == mode)
        if self.decoration is not None:
            self.decoration.set_mode(mode)

    def set_enabled(self, enabled, remember=True):
        """Switch the skin on or off.

        Switching on saves the application's palette, loads the Nosifer
        font, applies the theme and creates the decoration, cursors, webs
        and easter egg. Switching off removes them, takes the plugin's
        block out of the style sheet and puts the palette back. Repeated
        calls with the same state do nothing.

        :param enabled: ``True`` to apply the skin, ``False`` to remove it.
        :param remember: whether to store ``enabled`` in the settings
            (``False`` when QGIS unloads the plugin).
        """
        app = QApplication.instance()
        win = self.iface.mainWindow()
        if enabled and not self.active:
            self.active = True
            if self.font_id < 0:
                self.font_id = QFontDatabase.addApplicationFont(
                    str(FONT_FILE))
            self.palette_before = QPalette(app.palette())
            self._apply(self.theme())
            self.decoration = MenuBarDecoration(
                win.menuBar(), self.animation_mode(),
                stand_in=lambda: arcskin.title_row(win))
            self.cursors = ToolCursors(self.iface)
            self.webs = SpiderWebs(self.iface)
            self.egg = EasterEgg(self.iface)
        elif not enabled and self.active:
            self.active = False
            self.decoration.remove()
            self.decoration = None
            self.webs.remove()
            self.webs = None
            self.egg.remove()
            self.egg = None
            self.cursors.remove()
            self.cursors = None
            app.setPalette(self.palette_before)
            self.palette_before = None
            app.setStyleSheet(without_skin(app.styleSheet()))
            if self.font_id >= 0:
                QFontDatabase.removeApplicationFont(self.font_id)
                self.font_id = -1
        if remember:
            QgsSettings().setValue(ENABLED_KEY, bool(enabled))

    def resync(self):
        """Bring the skin in step with the switch after a style change.

        Called by :class:`StyleSync`. With the skin on, the plugin's block
        is appended again if another plugin's sheet has replaced it, and
        the decoration, webs and easter egg take in the widgets that
        plugin built (ArcSkin's title row, ribbon buttons and coordinate
        box). With the skin off, a block that came back with another
        plugin's saved copy of the sheet is removed.
        """
        if self.sync is None:
            return  # unloaded while the call was waiting
        app = QApplication.instance()
        sheet = app.styleSheet()
        if self.active:
            if not has_skin(sheet):
                app.setStyleSheet(with_skin(sheet, self.theme()))
            self.decoration.rehost()
            self.webs.rescan()
            self.egg.attach()
        elif has_skin(sheet):
            app.setStyleSheet(without_skin(sheet))

    def _apply(self, theme):
        """Set the palette and style sheet of ``theme`` on the application.

        The palette is built on the one saved when the skin was switched
        on and the style sheet block replaces the previous one, so changing
        themes never stacks one theme on another.
        """
        app = QApplication.instance()
        app.setPalette(load_palette(theme, self.palette_before))
        app.setStyleSheet(with_skin(app.styleSheet(), theme))
