"""Animated pumpkins, bats and ghosts on the menu bar.

MAIP animates its Halloween header with CSS inside the SVG: bats flap
(scaleY 1 -> .42), ghosts float (translateY -5 px, rotate +-2 deg), pumpkins
pulse (scale 1.045) and their faces flicker (opacity), each element with its
own period and phase. Qt renders no CSS animation, so the same drawings
(shapes and colours of MAIP's tools/seasonal_skins.py) are painted with
QPainter on a transparent overlay over the menu bar and refreshed by a
timer. Three modes:

* ``off``    - one still frame of the MAIP set at the right end;
* ``gentle`` - the MAIP set at the right end, animated in place;
* ``flight`` - the pumpkins stay at the right end while bats and ghosts fly
  across the whole menu bar, each on its own wavy course.
"""

import itertools
import math
import random
import re

from qgis.PyQt import sip
from qgis.PyQt.QtCore import (QElapsedTimer, QEvent, QObject, QPointF, Qt,
                              QTimer)
from qgis.PyQt.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform
from qgis.PyQt.QtWidgets import QWidget

BAND_WIDTH = 240     # right end of the menu bar the MAIP set occupies
FRAME_MS = 40        # 25 frames per second
MODES = ("off", "gentle", "flight")
MAX_BATS = 3         # in flight at once
MAX_GHOSTS = 1
FLICKER = [(0, 1), (.18, .78), (.32, .95), (.47, .7), (.63, 1), (.81, .85),
           (1, 1)]  # CSS keyframes of the face: (time fraction, opacity)
# Course of a flyer: ranges drawn at random for each flight, and how much
# it banks with its wave.
FLIGHT = {
    "bat": {"first_wait": (0.2, 3.0), "wait": (0.5, 4.0),
            "scale": (.36, .5), "speed": (70, 150), "amplitude": (3, 8),
            "period": (1.0, 2.4), "bank": .8},
    "ghost": {"first_wait": (2.0, 12.0), "wait": (6.0, 16.0),
              "scale": (.3, .4), "speed": (22, 40), "amplitude": (1, 3),
              "period": (3, 5), "bank": .3},
}
ARITY = {"M": 2, "L": 2, "C": 6, "S": 4, "Z": 0}  # numbers per SVG command


def path(d):
    """Build a QPainterPath from SVG path data.

    Only the absolute commands used by the drawings are understood:
    ``M``, ``L``, ``C``, ``S`` and ``Z``; numbers after a command's own
    repeat it (after ``M`` they are lines, as in SVG).

    :param d: SVG path data, e.g. ``"M0 0 L10 0 Z"``.
    :returns: the equivalent :class:`QPainterPath`.
    """
    out = QPainterPath()
    tokens = re.findall(r"[MLCSZ]|-?\d*\.?\d+", d)
    i = 0
    cmd = None
    last_ctrl = None  # second control point of the previous curve
    while i < len(tokens):
        if tokens[i] in ARITY:
            cmd = tokens[i]
            i += 1
        n = ARITY[cmd]
        args = [float(t) for t in tokens[i:i + n]]
        i += n
        if cmd == "Z":
            out.closeSubpath()
        elif cmd == "M":
            out.moveTo(*args)
            cmd = "L"
        elif cmd == "L":
            out.lineTo(*args)
        else:
            if cmd == "S":
                cur = out.currentPosition()
                first = ((2 * cur.x() - last_ctrl[0],
                          2 * cur.y() - last_ctrl[1])
                         if last_ctrl else (cur.x(), cur.y()))
                args = [*first, *args]
            out.cubicTo(*args)
            last_ctrl = (args[2], args[3])
            continue
        last_ctrl = None
    return out


BAT_BODY = path("M0 -4 C-6 -14 -18 -16 -30 -10 C-26 -8 -25 -4 -26 0 "
                "C-22 -2 -18 -1 -16 2 C-12 -1 -8 0 -6 4 C-4 2 -2 2 0 4 "
                "C2 2 4 2 6 4 C8 0 12 -1 16 2 C18 -1 22 -2 26 0 "
                "C25 -4 26 -8 30 -10 C18 -16 6 -14 0 -4 Z")
BAT_EARS = path("M-3 -6 L-2 -10 L0 -7 L2 -10 L3 -6 Z")
GHOST_BODY = path("M-18 24 L-18 -4 C-18 -18 -9 -26 0 -26 C9 -26 18 -18 18 -4 "
                  "L18 24 L12 18 L6 24 L0 18 L-6 24 L-12 18 Z")
PUMPKIN_STEM = path("M-2 -26 C-2 -34 4 -38 8 -40")
PUMPKIN_RIBS = path("M-6 -24 C-10 -8 -10 8 -6 24 M6 -24 C10 -8 10 8 6 24")
PUMPKIN_EYES = path("M-15 -7 L-8 -15 L-3 -6 Z M15 -7 L8 -15 L3 -6 Z")
PUMPKIN_MOUTH = path("M-16 6 L-11 12 L-6 7 L0 13 L6 7 L11 12 L16 6 L13 15 "
                     "C6 20 -6 20 -13 15 Z")

# Centres the animations transform about (CSS transform-origin: center).
BAT_CENTRE = BAT_BODY.boundingRect().center()
GHOST_CENTRE = GHOST_BODY.boundingRect().center()
PUMPKIN_CENTRE = PUMPKIN_STEM.boundingRect().united(
    PUMPKIN_RIBS.boundingRect()).adjusted(-18, 0, 18, 0).center()

# Colours, pens and brushes of the drawings (MAIP's palette).
BAT_FILL = QColor("#140a1c")
BAT_PEN = QPen(QColor(139, 92, 196, 191), 1.4)
GHOST_FILL = QColor(255, 255, 255, 242)
FACE_DARK = QColor("#1a0f1f")
EYES = QColor("#ffd23f")
PUMPKIN_SIDE = QColor("#e2600c")
PUMPKIN_FRONT = QColor("#ff7a1a")
STEM_PEN = QPen(QColor("#3d5a1e"), 5, Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap)
RIBS_PEN = QPen(PUMPKIN_SIDE, 2)


class Cycle:
    """One repeating animation with its own period and phase.

    Mirrors a CSS animation in MAIP: the duration is drawn from a range and
    a negative delay starts the cycle part-way through. A cycle given a
    ``seed`` always moves the same way (see :func:`decorations`).
    """

    def __init__(self, dur_range, seed=None):
        """Draw the duration and the starting delay.

        :param dur_range: ``(shortest, longest)`` duration in seconds.
        :param seed: number of the cycle in its set, as MAIP numbers them;
            ``None`` draws freely.
        """
        rnd = random.Random(None if seed is None else 1000 + seed)
        self.duration = rnd.uniform(*dur_range)
        self.delay = -rnd.uniform(0, self.duration)

    def phase(self, seconds):
        """Return the fraction of the cycle elapsed at ``seconds`` (0..1)."""
        return ((seconds - self.delay) / self.duration) % 1.0

    def eased(self, seconds):
        """Return the animation's progress at ``seconds``.

        The value goes 0 -> 1 -> 0 over one cycle, eased in and out like
        CSS ``ease-in-out`` between the 0%, 50% and 100% keyframes.
        """
        tri = 1 - abs(2 * self.phase(seconds) - 1)
        return tri * tri * (3 - 2 * tri)


def flicker(fraction):
    """Return the opacity of a pumpkin face.

    :param fraction: point of the (linear) flicker cycle, 0..1.
    :returns: opacity interpolated between the :data:`FLICKER` keyframes.
    """
    for (t0, v0), (t1, v1) in zip(FLICKER, FLICKER[1:]):
        if fraction <= t1:
            return v0 + (v1 - v0) * (fraction - t0) / (t1 - t0)
    return 1.0


class Decoration:
    """A drawing with its position, rotation, scale and animation cycles."""

    def __init__(self, kind, x, y, scale, rot=0, seeds=None):
        """Place the drawing and give it its animation cycles.

        :param kind: ``"pumpkin"``, ``"bat"`` or ``"ghost"``.
        :param x: horizontal position of the centre, in pixels.
        :param y: vertical position of the centre, in pixels.
        :param scale: size relative to the original drawing.
        :param rot: rotation in degrees.
        :param seeds: iterator giving each cycle its seed, or ``None`` for
            free cycles.
        """
        self.kind, self.x, self.y = kind, x, y
        self.scale, self.rot = scale, rot

        def cycle(dur_range):
            return Cycle(dur_range, None if seeds is None else next(seeds))

        if kind == "pumpkin":
            self.pulse = cycle((2.2, 3.0))
            self.flicker = cycle((1.4, 2.2))
        elif kind == "bat":
            self.flap = cycle((0.5, 0.8))
        else:
            self.float = cycle((3.0, 4.5))

    def paint(self, painter, seconds, animate):
        """Paint the drawing.

        :param painter: an active :class:`QPainter`.
        :param seconds: animation clock in seconds.
        :param animate: ``False`` paints the still drawing.
        """
        painter.save()
        painter.translate(self.x, self.y)
        painter.rotate(self.rot)
        painter.scale(self.scale, self.scale)
        getattr(self, "_" + self.kind)(painter, seconds if animate else None)
        painter.restore()

    @staticmethod
    def _about_centre(painter, centre, transform):
        """Apply ``transform`` about ``centre``.

        This is CSS ``transform-box: fill-box; transform-origin: center``.
        """
        painter.translate(centre)
        painter.setTransform(transform, True)
        painter.translate(-centre)

    def _bat(self, painter, seconds):
        """Paint a bat; its wings flap unless ``seconds`` is ``None``."""
        if seconds is not None:
            sy = 1 - 0.58 * self.flap.eased(seconds)
            self._about_centre(painter, BAT_CENTRE,
                               QTransform().scale(1, sy))
        painter.setPen(BAT_PEN)
        painter.setBrush(BAT_FILL)
        painter.drawPath(BAT_BODY)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(BAT_EARS)
        painter.setBrush(EYES)
        painter.drawEllipse(QPointF(-1.3, -4), .9, .9)
        painter.drawEllipse(QPointF(1.3, -4), .9, .9)

    def _ghost(self, painter, seconds):
        """Paint a ghost; it floats unless ``seconds`` is ``None``."""
        if seconds is not None:
            e = self.float.eased(seconds)
            self._about_centre(
                painter, GHOST_CENTRE,
                QTransform().translate(0, -5 * e).rotate(-2 + 4 * e))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(GHOST_FILL)
        painter.drawPath(GHOST_BODY)
        painter.setBrush(FACE_DARK)
        painter.drawEllipse(QPointF(-6, -6), 3, 4.5)
        painter.drawEllipse(QPointF(6, -6), 3, 4.5)
        painter.drawEllipse(QPointF(0, 5), 3.5, 4)

    def _pumpkin(self, painter, seconds):
        """Paint a pumpkin; it pulses and flickers if ``seconds`` is set."""
        if seconds is not None:
            s = 1 + 0.045 * self.pulse.eased(seconds)
            self._about_centre(painter, PUMPKIN_CENTRE,
                               QTransform().scale(s, s))
        painter.setPen(STEM_PEN)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(PUMPKIN_STEM)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(PUMPKIN_SIDE)
        painter.drawEllipse(QPointF(-16, 0), 18, 24)
        painter.drawEllipse(QPointF(16, 0), 18, 24)
        painter.setBrush(PUMPKIN_FRONT)
        painter.drawEllipse(QPointF(0, 0), 20, 26)
        painter.setPen(RIBS_PEN)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(PUMPKIN_RIBS)
        if seconds is not None:
            painter.setOpacity(flicker(self.flicker.phase(seconds)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(EYES)
        painter.drawPath(PUMPKIN_EYES)
        painter.drawPath(PUMPKIN_MOUTH)


def decorations(width, pumpkins_only=False):
    """Lay out MAIP's menu-bar set of drawings.

    The animation cycles are numbered 1, 2, ... in the order of the set,
    as in MAIP, so the set always moves the same way.

    :param width: width of the band the set is right-aligned in.
    :param pumpkins_only: keep only the pumpkins (the ``flight`` mode,
        where bats and ghosts fly separately).
    :returns: a list of :class:`Decoration`.
    """
    seeds = itertools.count(1)
    right = width - 16
    items = [Decoration("pumpkin", right - 212, 21, .34, 0, seeds),
             Decoration("bat", right - 166, 15, .46, -10, seeds),
             Decoration("ghost", right - 118, 18, .4, 8, seeds),
             Decoration("bat", right - 76, 20, .38, 12, seeds),
             Decoration("pumpkin", right - 30, 21, .34, 0, seeds)]
    if pumpkins_only:
        items = [i for i in items if i.kind == "pumpkin"]
    return items


class Flyer:
    """A bat or ghost crossing the menu bar on a wavy course.

    Bats are fast and flap; ghosts drift slowly and bob. A flyer enters at
    one edge, leaves past the other and comes back after a pause.
    """

    def __init__(self, kind, rnd, width, height):
        """Create a flyer that waits before its first flight.

        :param kind: ``"bat"`` or ``"ghost"``.
        :param rnd: :class:`random.Random` used for every course.
        :param width: width of the menu bar in pixels.
        :param height: height of the menu bar in pixels.
        """
        self.kind, self.rnd = kind, rnd
        self.spec = FLIGHT[kind]
        self.width, self.height = width, height
        self.item = Decoration(kind, 0, 0, 1)
        self.wait = rnd.uniform(*self.spec["first_wait"])
        self.alive = False

    def launch(self):
        """Start a new flight: random size, side, speed, height and wave."""
        rnd, spec = self.rnd, self.spec
        self.item.scale = rnd.uniform(*spec["scale"])
        self.margin = 40 * self.item.scale + 10
        self.direction = rnd.choice((-1, 1))
        self.x = -self.margin if self.direction > 0 \
            else self.width + self.margin
        self.speed = rnd.uniform(*spec["speed"])
        self.base_y = rnd.uniform(12, self.height - 10)
        self.amplitude = rnd.uniform(*spec["amplitude"])
        self.period = rnd.uniform(*spec["period"])
        self.phase = rnd.uniform(0, 6.283)
        self.time = 0.0
        self.alive = True

    def advance(self, dt):
        """Move the flyer on by ``dt`` seconds (or count down its pause)."""
        if not self.alive:
            self.wait -= dt
            if self.wait <= 0:
                self.launch()
            return
        self.time += dt
        self.x += self.direction * self.speed * dt
        w = 2 * math.pi / self.period
        wave = self.amplitude * math.sin(w * self.time + self.phase)
        slope = self.amplitude * w * math.cos(w * self.time + self.phase)
        self.item.x = self.x
        self.item.y = self.base_y + wave
        # Tilt with the course (bats bank, ghosts barely).
        tilt = math.degrees(math.atan2(slope, self.speed))
        self.item.rot = self.direction * tilt * self.spec["bank"]
        if (self.direction > 0 and self.x > self.width + self.margin) or (
                self.direction < 0 and self.x < -self.margin):
            self.alive = False
            self.wait = self.rnd.uniform(*self.spec["wait"])

    def paint(self, painter, seconds):
        """Paint the flyer if it is in flight."""
        if self.alive:
            self.item.paint(painter, seconds, True)


class MenuBarDecoration(QObject):
    """Animated drawings over the menu bar in one of the :data:`MODES`.

    Owns a transparent overlay widget and the frame timer, and follows the
    menu bar's size through an event filter. While the menu bar is hidden
    (ArcSkin puts a ribbon in its place) the overlay moves to a stand-in
    widget if one is given, and the timer rests otherwise.
    """

    def __init__(self, menubar, mode="flight", stand_in=None):
        """Create and show the overlay.

        :param menubar: the main window's :class:`QMenuBar`.
        :param mode: one of :data:`MODES`.
        :param stand_in: callable returning the widget to draw on while
            the menu bar is hidden (ArcSkin's title row), or ``None``.
        """
        super().__init__(menubar)
        self.menubar = menubar
        self.stand_in = stand_in
        self.host = menubar  # the widget the overlay sits on
        self.overlay = _Overlay(menubar, self)
        self.clock = QElapsedTimer()
        self.clock.start()
        self.last = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(FRAME_MS)
        self.timer.timeout.connect(self.tick)
        menubar.installEventFilter(self)
        self.set_mode(mode)
        self.overlay.show()
        self.rehost()

    def set_mode(self, mode):
        """Switch to another animation mode (unknown modes mean ``flight``).

        :param mode: one of :data:`MODES`.
        """
        self.mode = mode if mode in MODES else "flight"
        self.animate = self.mode != "off"
        rect = self.host.rect()
        rnd = random.Random()
        self.flyers = []
        if self.mode == "flight":
            self.flyers = [Flyer("bat", rnd, rect.width(), rect.height())
                           for _ in range(MAX_BATS)]
            self.flyers += [Flyer("ghost", rnd, rect.width(), rect.height())
                            for _ in range(MAX_GHOSTS)]
        self.overlay.items = self._set_items()
        self.place()
        self.last = self.seconds()
        self.run_timer()
        self.overlay.update()

    def _set_items(self):
        """Return the drawings at the right end for the current mode."""
        return decorations(BAND_WIDTH, pumpkins_only=self.mode == "flight")

    def seconds(self):
        """Return the time since the decoration was created, in seconds."""
        return self.clock.elapsed() / 1000.0

    def tick(self):
        """Advance the flyers and repaint; called by the frame timer."""
        now = self.seconds()
        dt = min(now - self.last, 0.2)  # after a pause, no giant leap
        self.last = now
        for flyer in self.flyers:
            flyer.advance(dt)
        self.overlay.update()

    def place(self):
        """Fit the overlay to the whole host or to its right end."""
        rect = self.host.rect()
        if self.mode == "flight":
            width = rect.width()
            for flyer in self.flyers:
                flyer.width, flyer.height = rect.width(), rect.height()
        else:
            width = min(BAND_WIDTH, rect.width())
        self.overlay.setGeometry(rect.right() - width + 1, rect.top(),
                                 width, rect.height())
        self.overlay.raise_()

    def run_timer(self):
        """Run the frame timer only while there is something to show."""
        if self.animate and not self.host.isHidden():
            self.timer.start()
        else:
            self.timer.stop()

    def rehost(self):
        """Sit on the menu bar, or on the stand-in while the bar is hidden.

        ArcSkin hides the menu bar before it builds its title row, so a
        hidden bar is followed up on the event loop's next turn; the way
        back is taken at once, before ArcSkin's widgets are deleted.
        """
        if sip.isdeleted(self):
            return  # removed while the deferred call was waiting
        host = self.menubar
        if self.menubar.isHidden() and self.stand_in is not None:
            host = self.stand_in() or self.menubar
        if sip.isdeleted(self.overlay):  # went down with its host
            self.overlay = _Overlay(host, self)
            self.overlay.items = self._set_items()
        if host is not self.host:
            if (self.host is not self.menubar
                    and not sip.isdeleted(self.host)):
                self.host.removeEventFilter(self)
            if host is not self.menubar:
                host.installEventFilter(self)
            self.host = host
            self.overlay.setParent(host)
        self.overlay.show()
        self.place()
        self.run_timer()

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API name)
        """Follow the host's size and the menu bar being hidden or shown."""
        kind = event.type()
        if obj is self.menubar and kind == QEvent.Type.Hide:
            QTimer.singleShot(0, self.rehost)
        elif obj is self.menubar and kind == QEvent.Type.Show:
            self.rehost()
        elif obj is self.host and kind in (QEvent.Type.Resize,
                                           QEvent.Type.Show):
            self.place()
        return False

    def remove(self):
        """Stop the animation and delete the overlay and this object."""
        self.timer.stop()
        self.menubar.removeEventFilter(self)
        if self.host is not self.menubar and not sip.isdeleted(self.host):
            self.host.removeEventFilter(self)
        if not sip.isdeleted(self.overlay):
            self.overlay.hide()
            self.overlay.deleteLater()
        self.deleteLater()


class _Overlay(QWidget):
    """Transparent child of the menu bar that paints the decoration.

    Mouse events pass through to the menu bar underneath.
    """

    def __init__(self, menubar, owner):
        """Create the overlay owned by a :class:`MenuBarDecoration`."""
        super().__init__(menubar)
        self.owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.items = []

    def paintEvent(self, event):  # noqa: N802 (Qt API name)
        """Paint the flyers, then the set at the right end."""
        owner = self.owner
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        seconds = owner.seconds()
        for flyer in owner.flyers:
            flyer.paint(painter, seconds)
        # The MAIP set is laid out for BAND_WIDTH; keep its right edge aligned.
        painter.translate(self.width() - BAND_WIDTH, 0)
        for item in self.items:
            item.paint(painter, seconds, owner.animate)
        painter.end()
