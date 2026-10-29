"""Halloween cursors for the map tools (their icons stay as they are).

Pan = white ghost, Select Features = witch's broom, Zoom In = large pumpkin,
Zoom Out = small pumpkin, Identify = bat. QGIS creates the tools inside the
application, so they are reached when they become the canvas's current tool
(``mapToolSet``): the tool is recognised by its action, gets the cursor and
keeps it. Switching the skin off gives every touched tool QGIS's own cursor
back.
"""

from pathlib import Path

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QObject, Qt
from qgis.PyQt.QtGui import QAction, QCursor, QIcon

from .qtutil import address, same

ICON_DIR = Path(__file__).resolve().parent / "icons"
SIZE = 32
# iface accessor, QGIS action object name, cursor picture, hot spot,
# QGIS's own cursor (QgsApplication.Cursor name, or a Qt cursor shape)
TOOLS = (
    ("actionPan", "mActionPan", "tool_pan.svg", (16, 16),
     Qt.CursorShape.OpenHandCursor),
    ("actionSelectRectangle", "mActionSelectFeatures", "tool_select.svg",
     (22, 24), "Select"),
    ("actionZoomIn", "mActionZoomIn", "tool_zoom_in.svg", (16, 18),
     "ZoomIn"),
    ("actionZoomOut", "mActionZoomOut", "tool_zoom_out.svg", (16, 17),
     "ZoomOut"),
    ("actionIdentify", "mActionIdentify", "tool_identify.svg", (16, 17),
     "Identify"),
)


def _action(iface, accessor, object_name):
    """Find a QGIS action.

    :param iface: the QGIS interface.
    :param accessor: name of the ``iface`` method returning the action.
    :param object_name: object name of the action in the main window,
        used when ``iface`` has no such method.
    :returns: the :class:`QAction`, or ``None`` if it is not found.
    """
    getter = getattr(iface, accessor, None)
    action = getter() if getter else None
    if action is None:
        action = iface.mainWindow().findChild(QAction, object_name)
    return action


def halloween_cursor(file, hot):
    """Make a cursor from one of the plugin's SVG pictures.

    :param file: file name in the ``icons`` folder.
    :param hot: ``(x, y)`` of the hot spot in a :data:`SIZE` square.
    :returns: a :class:`QCursor`.
    """
    pixmap = QIcon(str(ICON_DIR / file)).pixmap(SIZE, SIZE)
    return QCursor(pixmap, *hot)


def qgis_cursor(default):
    """Return the cursor QGIS itself gives a tool.

    :param default: a ``QgsApplication.Cursor`` name (``"ZoomIn"``) or a
        :class:`Qt.CursorShape`.
    :returns: a :class:`QCursor`.
    """
    if isinstance(default, str):
        return QgsApplication.getThemeCursor(
            getattr(QgsApplication.Cursor, default))
    return QCursor(default)


class ToolCursors(QObject):
    """Give the map tools their cursors as they come into use.

    Every tool that got a Halloween cursor is remembered, so that
    :meth:`remove` can give it QGIS's cursor back.
    """

    def __init__(self, iface):
        """Find the tools' actions and start watching the map canvas.

        The canvas's current tool gets its cursor at once.

        :param iface: the QGIS interface.
        """
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        # (action, Halloween cursor, QGIS's cursor); the pictures are
        # rendered once here, not on every change of tool.
        self.by_action = []
        for accessor, name, file, hot, default in TOOLS:
            action = _action(iface, accessor, name)
            if action is not None:
                self.by_action.append(
                    (action, halloween_cursor(file, hot), default))
        self.touched = {}  # C++ address of the tool -> (tool, QGIS cursor)
        self.canvas.mapToolSet.connect(self.on_tool)
        self.on_tool(self.canvas.mapTool(), None)

    def on_tool(self, tool, _old=None):
        """Give ``tool`` its Halloween cursor if it is one of :data:`TOOLS`.

        Connected to ``QgsMapCanvas.mapToolSet``.

        :param tool: the new map tool (may be ``None``).
        :param _old: the previous map tool (not used).
        """
        if tool is None:
            return
        try:
            action = tool.action()
        except (AttributeError, RuntimeError):
            return
        entry = next((e for e in self.by_action if same(e[0], action)),
                     None)
        if entry is None:
            return
        _, cursor, default = entry
        tool.setCursor(cursor)
        if same(self.canvas.mapTool(), tool):
            self.canvas.setCursor(cursor)
        self.touched[address(tool)] = (tool, default)

    def remove(self):
        """Stop watching the canvas and restore QGIS's cursors."""
        try:
            self.canvas.mapToolSet.disconnect(self.on_tool)
        except (TypeError, RuntimeError):
            pass
        for tool, default in self.touched.values():
            try:
                cursor = qgis_cursor(default)
                tool.setCursor(cursor)
                if same(self.canvas.mapTool(), tool):
                    self.canvas.setCursor(cursor)
            except RuntimeError:  # tool gone with QGIS
                pass
        self.touched = {}
        self.deleteLater()
