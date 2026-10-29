"""Living next to ArcSkin (EnviroSolutions' ArcGIS Pro look for QGIS).

ArcSkin rebuilds the QGIS window: it hides the menu bar and the status bar
and puts a ribbon with a title row in their place, with its own coordinate
box in a footer under the map. When both plugins are on, the Halloween
drawings move to that title row and the easter egg also listens to that
coordinate box. Only object names are used, so nothing here imports
ArcSkin; without it every function returns ``None``.
"""

from qgis.PyQt.QtWidgets import QLineEdit, QWidget

TITLE_ROW = "ArcSkinTitleRow"       # row above the ribbon tabs
COORDINATES = "ArcSkinCoordinates"  # typed coordinates in the map footer


def title_row(win):
    """Return ArcSkin's title row, or ``None`` when ArcSkin is off.

    :param win: the QGIS main window.
    """
    return win.findChild(QWidget, TITLE_ROW)


def coordinate_box(win):
    """Return ArcSkin's coordinate box, or ``None`` when ArcSkin is off.

    :param win: the QGIS main window.
    """
    return win.findChild(QLineEdit, COORDINATES)
