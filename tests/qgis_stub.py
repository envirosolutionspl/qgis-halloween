"""A stand-in ``qgis`` package for running the tests without QGIS.

Importing this module registers ``qgis``, ``qgis.core``, ``qgis.utils``
and ``qgis.PyQt.*`` in :data:`sys.modules`, built on PyQt5 or, when PyQt5
is not installed (QGIS 4), on PyQt6:

* ``qgis.PyQt.QtGui`` exports ``QAction`` and ``QActionGroup`` with both,
  as the real ``qgis.PyQt`` does;
* ``qgis.core`` has an in-memory :class:`QgsSettings`, a
  :class:`QgsApplication` with ``getThemeCursor`` and a minimal ``Qgis``;
* ``qgis.utils`` has an empty ``plugins`` dict and ``pluginMetadata``
  reading from :data:`PLUGIN_METADATA`.

It also creates the single offscreen :class:`QApplication` the tests use
(see :func:`app`) and provides :class:`FakeIface`, a main window with a
menu bar, status bar coordinate box and map canvas.
"""

import os
import sys
import types
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5 import QtCore, QtGui, QtWidgets, sip
    QT6 = False
except ImportError:
    from PyQt6 import QtCore, QtGui, QtWidgets, sip
    QT6 = True

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Metadata of fake plugins: {plugin name: {key: value}}.
PLUGIN_METADATA = {}


class QgsSettings:
    """In-memory replacement for ``QgsSettings`` shared by all instances."""

    store = {}

    def value(self, key, default=None, type=None):  # noqa: A002 (Qt API)
        """Return the stored value of ``key``, or ``default``."""
        value = self.store.get(key, default)
        if type is bool and isinstance(value, str):
            return value.lower() in ("true", "1")
        return type(value) if type is not None and value is not None \
            else value

    def setValue(self, key, value):  # noqa: N802 (QGIS API name)
        """Store ``value`` under ``key``."""
        self.store[key] = value


class QgsApplication:
    """The parts of ``QgsApplication`` the plugin uses."""

    class Cursor:
        """Names of QGIS's theme cursors."""

        ZoomIn = "ZoomIn"
        ZoomOut = "ZoomOut"
        Identify = "Identify"
        Select = "Select"

    @staticmethod
    def getThemeCursor(cursor):  # noqa: N802 (QGIS API name)
        """Return a cursor that records which theme cursor it stands for."""
        result = QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor)
        result.theme_name = cursor
        return result


def _plugin_metadata(name, key):
    """Return ``key`` from the fake metadata of plugin ``name``."""
    return PLUGIN_METADATA.get(name, {}).get(key)


def _module(name, **attributes):
    """Create a module, register it and return it."""
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module
    return module


def install():
    """Register the stand-in modules (idempotent)."""
    if "qgis" in sys.modules:
        return
    if not QT6:
        QtGui.QAction = QtWidgets.QAction
        QtGui.QActionGroup = QtWidgets.QActionGroup
    pyqt = _module("qgis.PyQt", QtCore=QtCore, QtGui=QtGui,
                   QtWidgets=QtWidgets, sip=sip)
    for name, module in (("QtCore", QtCore), ("QtGui", QtGui),
                         ("QtWidgets", QtWidgets), ("sip", sip)):
        sys.modules["qgis.PyQt." + name] = module
    core = _module("qgis.core", QgsSettings=QgsSettings,
                   QgsApplication=QgsApplication,
                   Qgis=types.SimpleNamespace(QGIS_VERSION="3.40.0"))
    utils = _module("qgis.utils", plugins={},
                    pluginMetadata=_plugin_metadata)
    _module("qgis", PyQt=pyqt, core=core, utils=utils)


_APP = None


def app():
    """Return the shared offscreen application."""
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _APP


def dispose(widget):
    """Delete ``widget`` now, with every object waiting for deletion.

    The tests run without an event loop, so ``deleteLater`` would otherwise
    leave half-removed widgets that a later style sheet change touches.
    """
    widget.close()
    widget.deleteLater()
    flush()


def flush():
    """Carry out pending deletions and events."""
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete)
    QtWidgets.QApplication.processEvents()


class MapTool(QtCore.QObject):
    """A map tool with an action and a cursor, as ``QgsMapTool``."""

    def __init__(self, action, parent=None):
        """Create a tool belonging to ``action``."""
        super().__init__(parent)
        self._action = action
        self.cursor = None

    def action(self):
        """Return the tool's action."""
        return self._action

    def setCursor(self, cursor):  # noqa: N802 (QGIS API name)
        """Remember the cursor set on the tool."""
        self.cursor = cursor


class MapCanvas(QtWidgets.QWidget):
    """A map canvas with a current tool and the ``mapToolSet`` signal."""

    mapToolSet = QtCore.pyqtSignal(object, object)  # noqa: N815 (QGIS)

    def __init__(self, parent=None):
        """Create a canvas without a tool."""
        super().__init__(parent)
        self._tool = None

    def mapTool(self):  # noqa: N802 (QGIS API name)
        """Return the current tool."""
        return self._tool

    def setMapTool(self, tool):  # noqa: N802 (QGIS API name)
        """Make ``tool`` current and emit ``mapToolSet``."""
        old, self._tool = self._tool, tool
        self.mapToolSet.emit(tool, old)


class QgsStatusBarCoordinatesWidget(QtWidgets.QWidget):
    """Holds the coordinate box; the class name is what the plugin seeks."""

    def __init__(self, parent=None):
        """Create the widget with a plain line edit inside."""
        super().__init__(parent)
        self.edit = QtWidgets.QLineEdit(self)


class FakeIface:
    """A ``QgisInterface`` with the parts the plugin uses."""

    TOOLS = ("Pan", "SelectRectangle", "ZoomIn", "ZoomOut", "Identify")

    def __init__(self):
        """Build the main window, menus, status bar, canvas and tools."""
        self.window = QtWidgets.QMainWindow()
        self.window.resize(900, 600)
        self.window.menuBar().addMenu("&Project")
        self.window.menuBar().addMenu("&Plugins")
        self.canvas = MapCanvas(self.window)
        self.window.setCentralWidget(self.canvas)
        self.coordinates = QgsStatusBarCoordinatesWidget()
        self.window.statusBar().addWidget(self.coordinates)
        self.plugin_menus = {}
        self.actions = {}
        for name in self.TOOLS:
            action = QtGui.QAction(name, self.window)
            self.actions[name] = action
            setattr(self, "action" + name,
                    lambda action=action: action)
        self.window.show()

    def mainWindow(self):  # noqa: N802 (QGIS API name)
        """Return the main window."""
        return self.window

    def mapCanvas(self):  # noqa: N802 (QGIS API name)
        """Return the map canvas."""
        return self.canvas

    def addPluginToMenu(self, menu, action):  # noqa: N802 (QGIS API name)
        """Record ``action`` under the plugin menu ``menu``."""
        self.plugin_menus.setdefault(menu, []).append(action)

    def removePluginMenu(self, menu, action):  # noqa: N802 (QGIS API)
        """Forget ``action`` from the plugin menu ``menu``."""
        self.plugin_menus.get(menu, []).remove(action)

    def tool(self, name):
        """Create a map tool for the action ``name``."""
        return MapTool(self.actions[name], self.window)

    def close(self):
        """Delete the main window and everything in it."""
        dispose(self.window)


install()
