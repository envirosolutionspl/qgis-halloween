"""Easter egg: four black spiders come down from the top of the map view.

Typing one of the KEYWORDS into the status bar's coordinate box (or into
ArcSkin's coordinate box under the map) and pressing Enter starts it. A
transparent overlay over the map canvas paints the spiders with QPainter:
each descends on its thread at its own speed, hangs for a while swaying and
moving its legs, then climbs back up and the overlay disappears. The map
keeps working underneath (the overlay lets the mouse through).
"""

import math
import random

from qgis.PyQt.QtCore import (QElapsedTimer, QEvent, QObject, QPointF, Qt,
                              QTimer)
from qgis.PyQt.QtGui import QColor, QPainter, QPen
from qgis.PyQt.QtWidgets import QLineEdit, QWidget

from . import arcskin

KEYWORDS = ("halloween",)
COORDS_WIDGET = "QgsStatusBarCoordinatesWidget"
FRAME_MS = 40
SPIDERS = 4


class Spider:
    """One spider on its thread: where it hangs and its timeline.

    The timeline is a start delay, then descend, hang and climb phases.
    """

    def __init__(self, rnd, width, height, index):
        """Draw the spider's size, position and timings.

        :param rnd: :class:`random.Random` to draw from.
        :param width: width of the map view in pixels.
        :param height: height of the map view in pixels.
        :param index: slot of the spider (0 .. :data:`SPIDERS` - 1); the
            view is split into equal slots, one spider in each.
        """
        slot = width / SPIDERS
        self.x = slot * index + rnd.uniform(.25, .75) * slot
        self.size = rnd.uniform(17, 26)           # body length
        self.target = rnd.uniform(.3, .7) * height
        self.start = rnd.uniform(0, 1.5)           # seconds before it appears
        self.descend = rnd.uniform(3.0, 5.0)
        self.hang = rnd.uniform(4.0, 6.0)
        self.climb = rnd.uniform(2.5, 4.0)
        self.sway_period = rnd.uniform(2.0, 3.5)
        self.sway = rnd.uniform(6, 14)             # px at the spider
        self.leg_speed = rnd.uniform(5, 8)         # leg cycles per second
        self.phase = rnd.uniform(0, 6.28)

    @property
    def end(self):
        """Time in seconds when the spider has climbed out of view."""
        return self.start + self.descend + self.hang + self.climb

    def pose(self, t):
        """Return where the spider is at time ``t``.

        :param t: seconds since the show started.
        :returns: ``(y, leg activity 0..1)``, or ``None`` when the spider
            is not shown.
        """
        t -= self.start
        if t < 0 or t > self.descend + self.hang + self.climb:
            return None
        if t < self.descend:
            p = t / self.descend
            y = self.target * (1 - (1 - p) ** 2)   # slows down near the end
            return y, 1.0
        t -= self.descend
        if t < self.hang:
            return self.target, 0.35
        t -= self.hang
        p = t / self.climb
        return self.target * (1 - p * p), 1.0

    def paint(self, painter, t):
        """Paint the thread and the spider swaying on it at time ``t``."""
        pose = self.pose(t)
        if pose is None:
            return
        y, activity = pose
        sway = self.sway * math.sin(2 * math.pi * t / self.sway_period
                                    + self.phase) * min(1, y / 80)
        x = self.x + sway
        s = self.size
        painter.setPen(QPen(QColor(70, 70, 70, 160), 1))
        painter.drawLine(QPointF(self.x, 0), QPointF(x, y))
        painter.save()
        painter.translate(x, y)
        painter.rotate(math.degrees(math.atan2(sway, max(y, 1))) * .5)
        body = QColor("#0b0b0b")
        painter.setPen(QPen(body, s * .11, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        wiggle = math.sin(2 * math.pi * self.leg_speed * t + self.phase)
        for side in (-1, 1):
            for i, base in enumerate((-62, -28, 18, 55)):
                # neighbouring legs move in opposite phase, as a spider walks
                swing = wiggle * (1 if i % 2 == 0 else -1) * 9 * activity
                a = math.radians(base + swing)
                knee = QPointF(side * math.cos(a) * s * .75,
                               math.sin(a) * s * .75 - s * .35)
                foot = QPointF(side * math.cos(a) * s * 1.35,
                               math.sin(a) * s * 1.35 + s * .25
                               + abs(wiggle) * 2 * activity)
                painter.drawLine(QPointF(0, 0), knee)
                painter.drawLine(knee, foot)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(body)
        painter.drawEllipse(QPointF(0, s * .3), s * .42, s * .55)   # abdomen
        painter.drawEllipse(QPointF(0, -s * .3), s * .3, s * .3)    # head
        painter.setBrush(QColor("#ffd23f"))
        painter.drawEllipse(QPointF(-s * .1, -s * .38), s * .06, s * .06)
        painter.drawEllipse(QPointF(s * .1, -s * .38), s * .06, s * .06)
        painter.restore()


class SpiderDrop(QWidget):
    """Overlay over the map canvas running one show.

    The overlay lets the mouse through and deletes itself when the last
    spider has gone.
    """

    def __init__(self, canvas):
        """Create the spiders and start the show at once.

        :param canvas: the :class:`QgsMapCanvas`.
        """
        super().__init__(canvas)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.canvas = canvas
        self.setGeometry(canvas.rect())
        rnd = random.Random()
        self.spiders = [Spider(rnd, self.width(), self.height(), i)
                        for i in range(SPIDERS)]
        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.setInterval(FRAME_MS)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        canvas.installEventFilter(self)
        self.raise_()
        self.show()

    def seconds(self):
        """Return the time since the show started, in seconds."""
        return self.clock.elapsed() / 1000.0

    def tick(self):
        """Repaint, or finish once every spider is gone."""
        if self.seconds() > max(s.end for s in self.spiders) + .2:
            self.finish()
            return
        self.update()

    def finish(self):
        """Stop the show and delete the overlay."""
        self.timer.stop()
        self.canvas.removeEventFilter(self)
        self.hide()
        self.deleteLater()

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API name)
        """Follow the size of the map canvas."""
        if obj is self.canvas and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.canvas.rect())
        return False

    def paintEvent(self, event):  # noqa: N802 (Qt API name)
        """Paint every spider at the current time."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.seconds()
        for spider in self.spiders:
            spider.paint(painter, t)
        painter.end()


def coordinate_box(win):
    """Find the coordinate box on the status bar.

    The box has no object name; it is the plain :class:`QLineEdit` inside
    ``QgsStatusBarCoordinatesWidget``. If that widget is not found, the
    first plain line edit on the status bar is taken (the locator uses a
    subclass, so it is skipped).

    :param win: the QGIS main window.
    :returns: the :class:`QLineEdit`, or ``None``.
    """
    for edit in win.statusBar().findChildren(QLineEdit):
        parent = edit.parent()
        if parent is not None and (
                parent.metaObject().className() == COORDS_WIDGET):
            return edit
    for edit in win.statusBar().findChildren(QLineEdit):
        if edit.metaObject().className() == "QLineEdit":
            return edit  # not the locator's QgsFilterLineEdit
    return None


class EasterEgg(QObject):
    """Watch the coordinate boxes; a keyword and Enter drop the spiders."""

    def __init__(self, iface):
        """Find the coordinate boxes and install the event filter on them.

        :param iface: the QGIS interface.
        """
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.box = coordinate_box(iface.mainWindow())  # QGIS's own box
        self.boxes = []  # every box watched: QGIS's and ArcSkin's
        self.show = None
        self.attach()

    def attach(self):
        """Watch the coordinate boxes present now; may be called again.

        ArcSkin hides the status bar and types coordinates into a box of
        its own under the map, built after it is switched on.
        """
        win = self.iface.mainWindow()
        for box in (self.box, arcskin.coordinate_box(win)):
            if box is not None and box not in self.boxes:
                box.installEventFilter(self)
                self.boxes.append(box)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API name)
        """Start the show on Enter if the box holds one of :data:`KEYWORDS`.

        That key press is consumed; everything else reaches QGIS.
        """
        if (obj in self.boxes and event.type() == QEvent.Type.KeyPress
                and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and obj.text().strip().lower() in KEYWORDS):
            obj.clear()
            self.drop()
            return True  # QGIS must not try to read it as coordinates
        return False

    def drop(self):
        """Start a new show, ending one still running."""
        canvas = self.iface.mapCanvas()
        if self.show is not None:
            try:
                self.show.finish()
            except RuntimeError:
                pass
        self.show = SpiderDrop(canvas)

    def remove(self):
        """Stop watching the boxes and end a running show."""
        for box in self.boxes:
            try:
                box.removeEventFilter(self)
            except RuntimeError:  # gone with ArcSkin's footer
                pass
        self.boxes = []
        if self.show is not None:
            try:
                self.show.finish()
            except RuntimeError:
                pass
            self.show = None
        self.deleteLater()
