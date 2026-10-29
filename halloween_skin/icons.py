"""A spider web over EnviroSolutions plugin icons on hover.

The tool buttons of plugins whose metadata names EnviroSolutions as the
author show a spider web over their icon while the mouse is on them.
"""

from pathlib import Path

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QEvent, QObject, QSize, Qt
from qgis.PyQt.QtGui import QAction, QIcon, QPainter, QPixmap
from qgis.PyQt.QtWidgets import QToolBar, QToolButton

ICON_DIR = Path(__file__).resolve().parent / "icons"
AUTHOR = "envirosolutions"


def envirosolutions_actions():
    """Collect the actions of loaded plugins written by EnviroSolutions.

    The actions are looked up in the plugin attributes Plugin Builder uses:
    ``actions`` (a list), ``action`` and ``toolbar``.

    :returns: a list of :class:`QAction`; empty outside QGIS.
    """
    try:
        from qgis import utils
    except ImportError:  # outside QGIS
        return []
    actions = []
    for name, plugin in list(getattr(utils, "plugins", {}).items()):
        try:
            author = utils.pluginMetadata(name, "author") or ""
        except Exception:  # noqa: BLE001 (any metadata trouble)
            author = ""
        if AUTHOR not in author.lower():
            continue
        found = list(getattr(plugin, "actions", None) or [])
        single = getattr(plugin, "action", None)
        if isinstance(single, QAction):
            found.append(single)
        toolbar = getattr(plugin, "toolbar", None)
        if isinstance(toolbar, QToolBar):
            found.extend(toolbar.actions())
        actions.extend(a for a in found if isinstance(a, QAction))
    return actions


def _address(obj):
    """Return the Qt object's address (stable, unlike the wrapper's id)."""
    try:
        return sip.unwrapinstance(obj)
    except (TypeError, RuntimeError):
        return id(obj)


def webbed(icon, size):
    """Paint the spider web over an icon.

    :param icon: the button's :class:`QIcon`.
    :param size: :class:`QSize` of the picture to paint.
    :returns: a new :class:`QIcon` with the web on top.
    """
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    icon.paint(painter, pixmap.rect())
    QIcon(str(ICON_DIR / "web.svg")).paint(painter, pixmap.rect())
    painter.end()
    return QIcon(pixmap)


class SpiderWebs(QObject):
    """Spider webs on the tool buttons of EnviroSolutions plugins.

    An event filter on each button shows the web when the mouse enters and
    puts the plain icon back when it leaves.
    """

    def __init__(self, iface):
        """Find the buttons and install the event filter on them.

        :param iface: the QGIS interface.
        """
        super().__init__(iface.mainWindow())
        self.buttons = {}  # button -> its plain icon
        win = iface.mainWindow()
        actions = {_address(a) for a in envirosolutions_actions()}
        if not actions:
            return
        for button in win.findChildren(QToolButton):
            action = button.defaultAction()
            if action is not None and _address(action) in actions:
                self.buttons[button] = None
                button.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API name)
        """Swap the icon on Enter and Leave; events are never consumed."""
        if obj in self.buttons:
            if event.type() == QEvent.Type.Enter:
                self.buttons[obj] = obj.icon()
                size = obj.iconSize()
                if size.isEmpty():
                    size = QSize(24, 24)
                obj.setIcon(webbed(obj.icon(), size * 2))
            elif event.type() == QEvent.Type.Leave:
                plain = self.buttons.get(obj)
                if plain is not None:
                    obj.setIcon(plain)
                    self.buttons[obj] = None
        return False

    def remove(self):
        """Remove the event filters and put the plain icons back."""
        for button, plain in list(self.buttons.items()):
            try:
                button.removeEventFilter(self)
                if plain is not None:
                    button.setIcon(plain)
            except RuntimeError:
                pass
        self.buttons = {}
        self.deleteLater()
