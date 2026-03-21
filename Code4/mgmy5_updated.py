try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets

import threading
import sys, os, time, math, random, subprocess


# ══════════════════════════════════════════════════════
#  SIRI-STYLE WAVEFORM WIDGET
# ══════════════════════════════════════════════════════
class SiriWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(460, 460)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._t = 0.0
        self._breathing = 0.0

        t = QtCore.QTimer(self)
        t.timeout.connect(self._tick)
        t.start(16)              # ~60fps

    def _tick(self):
        self._t += 0.052                  # medium-fast speed
        self._breathing = 0.5 + 0.5 * math.sin(self._t * 0.55)
        self.update()

    _COLORS = [
        (0,   220, 255),
        (0,   140, 255),
        (60,  80,  255),
        (0,   255, 200),
        (140, 80,  255),
        (0,   255, 160),
    ]

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)
        cx = self.width()  / 2
        cy = self.height() / 2
        R  = 190

        sphere = QtGui.QRadialGradient(cx, cy, R)
        sphere.setColorAt(0.0,  QtGui.QColor(8,  18, 45, 220))
        sphere.setColorAt(0.55, QtGui.QColor(4,  10, 30, 210))
        sphere.setColorAt(0.85, QtGui.QColor(0,   5, 18, 190))
        sphere.setColorAt(1.0,  QtGui.QColor(0,   0,  0,   0))
        p.setBrush(sphere); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)

        for width, alpha in [(18, 6), (10, 18), (5, 45), (2, 90), (1, 150)]:
            pen = QtGui.QPen(QtGui.QColor(0, 180, 255, alpha))
            pen.setWidth(width); p.setPen(pen); p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)

        clip_path = QtGui.QPainterPath()
        clip_path.addEllipse(QtCore.QRectF(cx - R, cy - R, R * 2, R * 2))
        p.setClipPath(clip_path)

        steps = 400; n = len(self._COLORS)
        for i, (r, g, b) in enumerate(self._COLORS):
            phase_off = i * (2 * math.pi / n)
            amp_base  = 28 + i * 4
            freq      = 2.0 + i * 0.42
            speed     = 0.9 + i * 0.15
            path = QtGui.QPainterPath(); first = True
            for s in range(steps + 1):
                x  = (cx - R) + s / steps * (R * 2)
                nx = (x - cx) / R
                ellipse_h = math.sqrt(max(0.0, 1.0 - nx * nx))
                envelope  = ellipse_h * 0.55 * (1.0 + 0.20 * self._breathing)
                y_off = (
                    math.sin(nx * math.pi * freq        + self._t * speed        + phase_off) * amp_base * envelope
                    + math.sin(nx * math.pi * freq * 1.9 + self._t * speed * 1.4 + phase_off * 1.6) * amp_base * 0.40 * envelope
                    + math.sin(nx * math.pi * freq * 0.55 + self._t * speed * 0.6 + phase_off * 0.8) * amp_base * 0.28 * envelope
                )
                if first: path.moveTo(x, cy + y_off); first = False
                else:     path.lineTo(x, cy + y_off)
            for gw, ga in [(5, 12), (2, 25)]:
                gp = QtGui.QPen(QtGui.QColor(r, g, b, ga))
                gp.setWidth(gw); gp.setCapStyle(QtCore.Qt.RoundCap)
                p.setPen(gp); p.setBrush(QtCore.Qt.NoBrush); p.drawPath(path)
            al = int(205 + 50 * math.sin(self._t + phase_off))
            lp = QtGui.QPen(QtGui.QColor(r, g, b, al))
            lp.setWidth(1); lp.setCapStyle(QtCore.Qt.RoundCap)
            p.setPen(lp); p.drawPath(path)

        p.setClipping(False)
        dot_r = int(6 + 5 * self._breathing)
        dot_a = int(180 + 75 * self._breathing)
        dg = QtGui.QRadialGradient(cx, cy, dot_r * 4)
        dg.setColorAt(0.0, QtGui.QColor(100, 180, 255, dot_a))
        dg.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.setBrush(dg); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - dot_r*4), int(cy - dot_r*4), dot_r*8, dot_r*8)
        p.setBrush(QtGui.QColor(200, 230, 255, dot_a))
        p.drawEllipse(int(cx - dot_r), int(cy - dot_r), dot_r*2, dot_r*2)
        shine = QtGui.QRadialGradient(cx - R*0.3, cy - R*0.35, R*0.5)
        shine.setColorAt(0.0, QtGui.QColor(255, 255, 255, 22))
        shine.setColorAt(1.0, QtGui.QColor(255, 255, 255,  0))
        p.setBrush(shine); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)


# ══════════════════════════════════════════════════════
#  THINKING SPINNER  (3 orbiting arcs + pulse dot)
# ══════════════════════════════════════════════════════
class ThinkingSpinner(QtWidgets.QWidget):
    def __init__(self, size=280, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._t = 0.0; self._pulse = 0.0
        t = QtCore.QTimer(self); t.timeout.connect(self._tick); t.start(16)

    def _tick(self):
        self._t    += 0.045
        self._pulse = 0.5 + 0.5 * math.sin(self._t * 1.8)
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)
        cx, cy = self.width() / 2, self.height() / 2
        scale  = self.width() / 200.0
        arcs = [
            (72, 4, 200,   0, 220, 255,  1.00,   0),   # bright cyan
            (50, 3, 160,   0, 255, 160, -1.45,  40),   # mint
            (30, 2, 120, 140,  80, 255,  2.10,  80),   # violet
        ]
        for radius, pen_w, alpha, r, g, b, speed, span_off in arcs:
            radius = radius * scale; pen_w = max(1, int(pen_w * scale))
            angle  = math.degrees(self._t * speed) % 360
            span   = 260 + span_off
            rect   = QtCore.QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            gpen   = QtGui.QPen(QtGui.QColor(r, g, b, alpha // 4))
            gpen.setWidth(pen_w + int(6 * scale)); gpen.setCapStyle(QtCore.Qt.RoundCap)
            p.setPen(gpen); p.setBrush(QtCore.Qt.NoBrush)
            p.drawArc(rect, int(angle * 16), int(span * 16))
            pen = QtGui.QPen(QtGui.QColor(r, g, b, alpha))
            pen.setWidth(pen_w); pen.setCapStyle(QtCore.Qt.RoundCap)
            p.setPen(pen); p.drawArc(rect, int(angle * 16), int(span * 16))

        dot_r  = int((7 + 5 * self._pulse) * scale)
        dot_al = int(160 + 95 * self._pulse)
        dg = QtGui.QRadialGradient(cx, cy, dot_r * 3)
        dg.setColorAt(0.0, QtGui.QColor(0, 220, 255, dot_al))
        dg.setColorAt(1.0, QtGui.QColor(0,   0,   0,  0))
        p.setBrush(dg); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - dot_r*3), int(cy - dot_r*3), dot_r*6, dot_r*6)
        p.setBrush(QtGui.QColor(180, 230, 255, dot_al))
        p.drawEllipse(int(cx - dot_r), int(cy - dot_r), dot_r*2, dot_r*2)


# ══════════════════════════════════════════════════════
#  SCAN BAR
# ══════════════════════════════════════════════════════
class _ScanBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._t = 0.0
        t = QtCore.QTimer(self); t.timeout.connect(self._tick); t.start(16)

    def _tick(self):
        self._t = (self._t + 0.022) % 1.0
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QtGui.QColor(0, 60, 90, 80)); p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, h//2, h//2)
        blob_w = int(w * 0.35)
        x = int((self._t * (w + blob_w)) - blob_w)
        g = QtGui.QLinearGradient(x, 0, x + blob_w, 0)
        g.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        g.setColorAt(0.4, QtGui.QColor(0, 220, 255, 200))
        g.setColorAt(0.6, QtGui.QColor(0, 255, 180, 180))
        g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.setBrush(g)
        p.drawRoundedRect(max(0, x), 0, min(blob_w, w - max(0, x)), h, h//2, h//2)


# ══════════════════════════════════════════════════════
#  LISTEN WINDOW  — fullscreen popup while stt.py runs
# ══════════════════════════════════════════════════════
class ListenWindow(QtWidgets.QDialog):
    stop_requested = QtCore.Signal()
    _PHASES_RECORDING   = ["LISTENING"]
    _PHASES_PROCESSING  = ["THINKING", "TRANSCRIBING"]
    _PHASES = ["LISTENING"]  # default = recording phase

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AURA — Listen Mode")
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._phase = 0; self._dots = 0
        self._build_ui()
        self._cycle_timer = QtCore.QTimer(self)
        self._cycle_timer.timeout.connect(self._cycle_text)
        self._cycle_timer.start(400)
        self.showMaximized()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setAlignment(QtCore.Qt.AlignCenter)

        # top label
        top = QtWidgets.QLabel("◎  AURA  —  LISTEN MODE  —  AUDIO PROCESSING")
        top.setAlignment(QtCore.Qt.AlignCenter)
        top.setStyleSheet("""
            color: rgba(0,200,255,160); font-family: 'Courier New';
            font-size: 13px; font-weight: bold; letter-spacing: 6px;
            padding-top: 50px;
        """)
        root.addWidget(top)
        root.addSpacing(50)

        # spinner
        self.spinner = ThinkingSpinner(size=320)
        root.addWidget(self.spinner, alignment=QtCore.Qt.AlignCenter)
        root.addSpacing(44)

        # animated status label
        self.status_lbl = QtWidgets.QLabel("RECORDING")
        self.status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)           # ← FIX: wrap long status text
        self.status_lbl.setFixedWidth(700)
        self.status_lbl.setMinimumHeight(48)        # ← FIX: allow height to expand
        self.status_lbl.setStyleSheet("""
            color: rgba(0,255,180,240); font-family: 'Courier New';
            font-size: 32px; font-weight: bold; letter-spacing: 8px;
        """)
        fx = QtWidgets.QGraphicsDropShadowEffect()
        fx.setOffset(0, 0); fx.setBlurRadius(28)
        fx.setColor(QtGui.QColor(0, 255, 180, 130))
        self.status_lbl.setGraphicsEffect(fx)
        root.addWidget(self.status_lbl, alignment=QtCore.Qt.AlignCenter)
        root.addSpacing(14)

        # sub label — shows live stt.py / school_queries.py output
        self.sub_lbl = QtWidgets.QLabel("Loading Speech Model...")
        self.sub_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.sub_lbl.setWordWrap(True)              # ← FIX: wrap long output lines
        self.sub_lbl.setFixedWidth(720)             # ← FIX: constrain width
        self.sub_lbl.setMinimumHeight(52)           # ← FIX: room for 2–3 wrapped lines
        self.sub_lbl.setStyleSheet("""
            color: rgba(0,160,220,180); font-family: 'Courier New';
            font-size: 11px; letter-spacing: 3px;
        """)
        root.addWidget(self.sub_lbl, alignment=QtCore.Qt.AlignCenter)
        root.addSpacing(40)

        # scan bar
        self.bar = _ScanBar()
        self.bar.setFixedSize(520, 7)
        root.addWidget(self.bar, alignment=QtCore.Qt.AlignCenter)
        root.addSpacing(52)

        # STOP button
        self.btn_stop = QtWidgets.QPushButton("  ■   STOP RECORDING")
        self.btn_stop.setFixedSize(280, 52)
        self.btn_stop.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_stop.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(180,20,20,210), stop:1 rgba(120,10,10,230));
                border: 1px solid rgba(255,60,60,180);
                border-left: 4px solid rgba(255,80,80,255);
                border-radius: 8px; color: rgba(255,110,110,240);
                font-family: 'Courier New'; font-size: 15px;
                font-weight: bold; letter-spacing: 3px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(255,50,50,230), stop:1 rgba(200,20,20,250));
                border: 2px solid rgba(255,80,80,255);
                color: rgba(255,255,255,255);
            }
            QPushButton:pressed { background: rgba(255,30,30,210); }
        """)
        sfx = QtWidgets.QGraphicsDropShadowEffect(self.btn_stop)
        sfx.setOffset(0, 0); sfx.setBlurRadius(18)
        sfx.setColor(QtGui.QColor(255, 50, 50, 160))
        self.btn_stop.setGraphicsEffect(sfx)
        self.btn_stop.clicked.connect(self._on_stop)
        root.addWidget(self.btn_stop, alignment=QtCore.Qt.AlignCenter)
        root.addStretch()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        # deep space background
        p.fillRect(self.rect(), QtGui.QColor(2, 5, 15, 248))
        # nebula glows
        g1 = QtGui.QRadialGradient(self.width()*0.8, self.height()*0.1, self.width()*0.4)
        g1.setColorAt(0.0, QtGui.QColor(0, 20, 60, 60)); g1.setColorAt(1.0, QtGui.QColor(0,0,0,0))
        p.fillRect(self.rect(), g1)
        g2 = QtGui.QRadialGradient(self.width()*0.1, self.height()*0.85, self.width()*0.35)
        g2.setColorAt(0.0, QtGui.QColor(0, 40, 60, 40)); g2.setColorAt(1.0, QtGui.QColor(0,0,0,0))
        p.fillRect(self.rect(), g2)
        # horizontal scan lines
        pen = QtGui.QPen(QtGui.QColor(0, 180, 255, 4))
        pen.setWidth(1); p.setPen(pen)
        for y in range(0, self.height(), 4):
            p.drawLine(0, y, self.width(), y)
        # border glow
        for bw, ba in [(12, 4), (6, 12), (2, 40), (1, 100)]:
            pen2 = QtGui.QPen(QtGui.QColor(0, 200, 255, ba))
            pen2.setWidth(bw); p.setPen(pen2); p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(bw//2, bw//2, self.width()-bw, self.height()-bw)
        # top accent line
        accent = QtGui.QLinearGradient(0, 0, self.width(), 0)
        accent.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        accent.setColorAt(0.3, QtGui.QColor(0, 220, 255, 200))
        accent.setColorAt(0.7, QtGui.QColor(0, 160, 255, 180))
        accent.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.setPen(QtGui.QPen(QtGui.QBrush(accent), 2))
        p.drawLine(40, 2, self.width()-40, 2)

    def _cycle_text(self):
        self._dots = (self._dots + 1) % 4
        if self._dots == 0:
            self._phase = (self._phase + 1) % len(self._PHASES)
        self.status_lbl.setText(self._PHASES[self._phase] + "." * self._dots + " " * (3 - self._dots))

    def switch_to_processing(self):
        """Call when stt.py finishes recording — switch to processing phases."""
        self._PHASES = self._PHASES_PROCESSING
        self._phase  = 0
        self._dots   = 0
        self.sub_lbl.setText("TRANSCRIBING AUDIO  ·  PLEASE WAIT")

    def set_status_line(self, text):
        """Live output from stt.py / school_queries.py → sub label.
        Text wraps automatically; no horizontal drift."""
        self.sub_lbl.setText(text)

    def _on_stop(self):
        self._cycle_timer.stop()
        self.status_lbl.setText("STOPPED")
        self.stop_requested.emit()
        QtCore.QTimer.singleShot(500, self.close)


# ══════════════════════════════════════════════════════
#  QUERY MODE SELECTION WINDOW
#  Shows when "◎ QUERY MODE" is clicked.
#  6 category cards matching the school_queries.py FACTS.
#  Emits subject_selected(category_str) on click.
# ══════════════════════════════════════════════════════
class QueryModeWindow(QtWidgets.QDialog):

    # (display_label, icon, accent_rgb, category_hint)
    # Categories mirror the FACTS sections in school_queries.py
    SUBJECTS = [
        ("SCHOOL INFO",     "🏫",  (0,   210, 255), "school info"),
        ("MANAGEMENT",      "👤",  (0,   255, 160), "management"),
        ("FACILITIES",      "🏊",  (0,   180, 255), "facilities"),
        ("ADMISSION",       "📝",  (255, 180,   0), "admission"),
        ("CURRICULUM",      "📚",  (180,  80, 255), "curriculum"),
        ("CO-CURRICULAR",   "🎭",  (255, 120,  60), "co-curricular"),
    ]

    subject_selected = QtCore.Signal(str)   # emits category hint string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AURA — Query Mode")
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._build_ui()
        self.showMaximized()

    # ── background paint ───────────────────────────────
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(2, 5, 15, 252))

        # nebula corner glows
        for rx, ry, rr, rc in [
            (0.85, 0.10, 0.40, QtGui.QColor(0,  30,  90,  55)),
            (0.10, 0.88, 0.38, QtGui.QColor(0,  55,  80,  40)),
            (0.50, 0.50, 0.55, QtGui.QColor(0,  10,  50,  28)),
        ]:
            g = QtGui.QRadialGradient(self.width()*rx, self.height()*ry, self.width()*rr)
            g.setColorAt(0.0, rc); g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), g)

        # CRT scanlines
        pen = QtGui.QPen(QtGui.QColor(0, 160, 255, 3))
        pen.setWidth(1); p.setPen(pen)
        for y in range(0, self.height(), 4):
            p.drawLine(0, y, self.width(), y)

        # border glow (layered)
        for bw, ba in [(14, 3), (7, 10), (2, 36), (1, 95)]:
            bp = QtGui.QPen(QtGui.QColor(0, 200, 255, ba))
            bp.setWidth(bw); p.setPen(bp); p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(bw//2, bw//2, self.width()-bw, self.height()-bw)

        # top accent gradient line
        acc = QtGui.QLinearGradient(0, 0, self.width(), 0)
        acc.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        acc.setColorAt(0.25, QtGui.QColor(0, 220, 255, 210))
        acc.setColorAt(0.75, QtGui.QColor(0, 160, 255, 170))
        acc.setColorAt(1.0,  QtGui.QColor(0, 0, 0, 0))
        p.setPen(QtGui.QPen(QtGui.QBrush(acc), 2))
        p.drawLine(40, 2, self.width()-40, 2)

    # ── build UI ──────────────────────────────────────
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── top system label ──────────────────────────
        top = QtWidgets.QLabel("◎  AURA  ·  QUERY MODE  ·  KOTHARI INTERNATIONAL SCHOOL")
        top.setAlignment(QtCore.Qt.AlignCenter)
        top.setStyleSheet("""
            color: rgba(0,200,255,155); font-family: 'Courier New';
            font-size: 13px; font-weight: bold; letter-spacing: 6px;
            padding-top: 42px; padding-bottom: 4px;
        """)
        root.addWidget(top)

        # ── headline ──────────────────────────────────
        title = QtWidgets.QLabel("SELECT QUERY CATEGORY")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("""
            color: rgba(0,230,255,255); font-family: 'Courier New';
            font-size: 36px; font-weight: bold; letter-spacing: 14px;
        """)
        fx = QtWidgets.QGraphicsDropShadowEffect()
        fx.setOffset(0, 0); fx.setBlurRadius(36)
        fx.setColor(QtGui.QColor(0, 200, 255, 170))
        title.setGraphicsEffect(fx)
        root.addWidget(title)
        root.addSpacing(6)

        sub = QtWidgets.QLabel(
            "CHOOSE A CATEGORY BELOW  ·  SPEAK YOUR QUESTION  ·  AI WILL ANSWER")
        sub.setAlignment(QtCore.Qt.AlignCenter)
        sub.setStyleSheet("""
            color: rgba(0,140,200,125); font-family: 'Courier New';
            font-size: 11px; letter-spacing: 4px;
        """)
        root.addWidget(sub)
        root.addSpacing(34)

        # ── 2-row × 3-col grid of subject cards ───────
        grid_container = QtWidgets.QWidget()
        grid_container.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        grid = QtWidgets.QGridLayout(grid_container)
        grid.setSpacing(20)
        grid.setContentsMargins(100, 0, 100, 0)

        for idx, (label, icon, rgb, hint) in enumerate(self.SUBJECTS):
            row, col = divmod(idx, 3)
            grid.addWidget(self._make_card(label, icon, rgb, hint), row, col)

        root.addWidget(grid_container, alignment=QtCore.Qt.AlignCenter)
        root.addStretch()

        # ── animated scan bar ─────────────────────────
        scan = _ScanBar()
        scan.setFixedSize(540, 6)
        root.addWidget(scan, alignment=QtCore.Qt.AlignCenter)
        root.addSpacing(28)

        # ── BACK button ───────────────────────────────
        back = QtWidgets.QPushButton("◀   BACK TO MAIN MENU")
        back.setFixedSize(270, 48)
        back.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        back.setFocusPolicy(QtCore.Qt.NoFocus)
        back.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,35,55,200), stop:1 rgba(8,20,35,200));
                border: 1px solid rgba(0,160,220,135);
                border-left: 4px solid rgba(0,185,255,215);
                border-radius: 8px; color: rgba(0,180,255,195);
                font-family: 'Courier New'; font-size: 13px;
                font-weight: bold; letter-spacing: 3px;
            }
            QPushButton:hover {
                background: rgba(0,55,95,220);
                border: 2px solid rgba(0,210,255,255);
                color: rgba(255,255,255,255);
            }
            QPushButton:pressed { background: rgba(0,35,65,230); }
        """)
        bshadow = QtWidgets.QGraphicsDropShadowEffect(back)
        bshadow.setOffset(0, 0); bshadow.setBlurRadius(0)
        bshadow.setColor(QtGui.QColor(0, 180, 255, 150))
        back.setGraphicsEffect(bshadow)

        def _back_enter(ev):
            a = QtCore.QPropertyAnimation(bshadow, b"blurRadius")
            a.setDuration(160); a.setStartValue(0); a.setEndValue(22)
            a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
            QtWidgets.QPushButton.enterEvent(back, ev)

        def _back_leave(ev):
            a = QtCore.QPropertyAnimation(bshadow, b"blurRadius")
            a.setDuration(200); a.setStartValue(22); a.setEndValue(0)
            a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
            QtWidgets.QPushButton.leaveEvent(back, ev)

        back.enterEvent = _back_enter
        back.leaveEvent = _back_leave
        back.clicked.connect(self.close)
        root.addWidget(back, alignment=QtCore.Qt.AlignCenter)
        root.addSpacing(42)

    # ── build one subject card ─────────────────────────
    def _make_card(self, label, icon, rgb, hint):
        r, g, b = rgb
        card = QtWidgets.QPushButton()
        card.setFixedSize(320, 115)
        card.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        card.setFocusPolicy(QtCore.Qt.NoFocus)

        # inner layout
        hl = QtWidgets.QHBoxLayout(card)
        hl.setContentsMargins(20, 0, 16, 0)
        hl.setSpacing(16)

        # icon
        icon_lbl = QtWidgets.QLabel(icon)
        icon_lbl.setStyleSheet(f"""
            color: rgba({r},{g},{b},235); font-size: 38px;
            background: transparent;
        """)
        icon_lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        hl.addWidget(icon_lbl)

        # text column
        vcol = QtWidgets.QVBoxLayout()
        vcol.setSpacing(5)

        name_lbl = QtWidgets.QLabel(label)
        name_lbl.setStyleSheet(f"""
            color: rgba({r},{g},{b},245); font-family: 'Courier New';
            font-size: 18px; font-weight: bold; letter-spacing: 3px;
            background: transparent;
        """)
        name_lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        hint_lbl = QtWidgets.QLabel(f"ASK ABOUT  ·  {label}  ·  VOICE ENABLED")
        hint_lbl.setStyleSheet(f"""
            color: rgba({r},{g},{b},105); font-family: 'Courier New';
            font-size: 9px; letter-spacing: 2px; background: transparent;
        """)
        hint_lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        vcol.addWidget(name_lbl)
        vcol.addWidget(hint_lbl)
        hl.addLayout(vcol)
        hl.addStretch()

        # arrow indicator
        arr = QtWidgets.QLabel("▶")
        arr.setStyleSheet(f"""
            color: rgba({r},{g},{b},115); font-size: 15px;
            background: transparent;
        """)
        arr.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        hl.addWidget(arr)

        # stylesheet
        card.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba({r//6},{g//6},{b//6},215),
                    stop:1 rgba({r//8},{g//8},{b//8},195));
                border: 1px solid rgba({r},{g},{b},125);
                border-left: 5px solid rgba({r},{g},{b},255);
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba({min(r//2,255)},{min(g//2,255)},{min(b//2,255)},235),
                    stop:1 rgba({r//3},{g//3},{b//3},215));
                border: 1px solid rgba({r},{g},{b},225);
                border-left: 5px solid rgba(255,255,255,235);
            }}
            QPushButton:pressed {{
                background: rgba({r//5},{g//5},{b//5},240);
                border-left: 5px solid rgba({r},{g},{b},195);
            }}
        """)

        # hover glow animation
        shadow = QtWidgets.QGraphicsDropShadowEffect(card)
        shadow.setOffset(0, 4); shadow.setBlurRadius(0)
        shadow.setColor(QtGui.QColor(r, g, b, 110))
        card.setGraphicsEffect(shadow)

        def _enter(ev, s=shadow):
            a = QtCore.QPropertyAnimation(s, b"blurRadius")
            a.setDuration(175); a.setStartValue(0); a.setEndValue(38)
            a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
            QtWidgets.QPushButton.enterEvent(card, ev)

        def _leave(ev, s=shadow):
            a = QtCore.QPropertyAnimation(s, b"blurRadius")
            a.setDuration(215); a.setStartValue(38); a.setEndValue(0)
            a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
            QtWidgets.QPushButton.leaveEvent(card, ev)

        card.enterEvent = _enter
        card.leaveEvent = _leave
        card.clicked.connect(lambda checked=False, h=hint: self._on_select(h))
        return card

    def _on_select(self, hint):
        self.subject_selected.emit(hint)
        self.close()


# ══════════════════════════════════════════════════════
#  SPACE BACKGROUND
# ══════════════════════════════════════════════════════
class SpaceBackground(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stars = []
        for _ in range(200):
            self.stars.append([
                random.randint(0, 1920),
                random.randint(0, 1080),
                random.randint(140, 255),
                random.uniform(0, 2 * math.pi),
                random.choice([1, 1, 1, 2])
            ])
        t = QtCore.QTimer(self)
        t.timeout.connect(self.update)
        t.start(80)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(2, 5, 15))
        for rx, ry, rr, rc in [
            (0.8, 0.15, 0.35, QtGui.QColor(0, 20, 60, 50)),
            (0.1, 0.80, 0.30, QtGui.QColor(0, 40, 60, 35)),
        ]:
            g = QtGui.QRadialGradient(self.width()*rx, self.height()*ry, self.width()*rr)
            g.setColorAt(0.0, rc); g.setColorAt(1.0, QtGui.QColor(0,0,0,0))
            p.fillRect(self.rect(), g)

        now = time.time()
        for x, y, br, phase, size in self.stars:
            b = max(80, min(255, int(br + 40 * math.sin(now * 0.7 + phase))))
            col = QtGui.QColor(b, b, min(255, b+15))
            if size == 1:
                p.setPen(col); p.drawPoint(x % self.width(), y % self.height())
            else:
                p.setBrush(col); p.setPen(QtCore.Qt.NoPen)
                p.drawEllipse(x % self.width(), y % self.height(), 2, 2)


# ══════════════════════════════════════════════════════
#  GLOW BUTTON
# ══════════════════════════════════════════════════════
class GlowButton(QtWidgets.QPushButton):
    def __init__(self, text, accent=None, parent=None):
        super().__init__(text, parent)
        self.accent = accent or QtGui.QColor(0, 180, 255)
        self.setFixedHeight(54)
        self.setMinimumWidth(280)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0); self.shadow.setBlurRadius(0)
        self.shadow.setColor(QtGui.QColor(self.accent.red(),
                                          self.accent.green(),
                                          self.accent.blue(), 180))
        self.setGraphicsEffect(self.shadow)
        self._apply_style(False)

    def _apply_style(self, h):
        r, g, b = self.accent.red(), self.accent.green(), self.accent.blue()
        if h:
            self.setStyleSheet(f"""QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba({r},{g},{b},200),
                    stop:1 rgba({max(r-60,0)},{max(g-60,0)},{max(b-60,0)},230));
                border: 2px solid rgba({r},{g},{b},255);
                border-left: 5px solid rgba(255,255,255,220);
                border-radius: 8px;
                color: rgba(255,255,255,255);
                font-family: 'Courier New'; font-size: 15px; font-weight: bold;
                letter-spacing: 2px; text-align: left; padding-left: 20px;
            }}""")
        else:
            self.setStyleSheet(f"""QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba({r//5},{g//5},{b//5},200),
                    stop:1 rgba({r//6},{g//6},{b//6},180));
                border: 1px solid rgba({r},{g},{b},160);
                border-left: 4px solid rgba({r},{g},{b},255);
                border-radius: 8px;
                color: rgba({r},{g},{b},230);
                font-family: 'Courier New'; font-size: 15px; font-weight: bold;
                letter-spacing: 2px; text-align: left; padding-left: 20px;
            }}""")

    def enterEvent(self, e):
        self._apply_style(True)
        a = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        a.setDuration(160); a.setStartValue(0); a.setEndValue(30)
        a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._apply_style(False)
        a = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        a.setDuration(200); a.setStartValue(30); a.setEndValue(0)
        a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        super().leaveEvent(e)


# ══════════════════════════════════════════════════════
#  BLINKING DOT
# ══════════════════════════════════════════════════════
class BlinkDot(QtWidgets.QWidget):
    def __init__(self, label="ONLINE", color=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = color or QtGui.QColor(0, 255, 120)
        self.setFixedSize(200, 22)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._a = 255; self._d = -7
        t = QtCore.QTimer(self); t.timeout.connect(self._tick); t.start(28)

    def _tick(self):
        self._a += self._d
        if self._a <= 50:  self._d =  7
        if self._a >= 255: self._d = -7
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        g = QtGui.QRadialGradient(10, 11, 9)
        c = QtGui.QColor(self.color); c.setAlpha(self._a // 3)
        g.setColorAt(0, c); g.setColorAt(1, QtGui.QColor(0,0,0,0))
        p.setBrush(g); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(1, 2, 18, 18)
        c2 = QtGui.QColor(self.color); c2.setAlpha(self._a)
        p.setBrush(c2); p.drawEllipse(5, 6, 10, 10)
        p.setFont(QtGui.QFont("Courier New", 9, QtGui.QFont.Bold))
        lc = QtGui.QColor(self.color); lc.setAlpha(170)
        p.setPen(lc)
        p.drawText(QtCore.QRect(22, 0, 178, 22), QtCore.Qt.AlignVCenter, self.label)


# ══════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════
class AuraMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA — Kotharis")
        self.resize(1280, 720)
        self._listening   = False
        self._stt_process = None
        self._listen_win  = None   # ListenWindow reference
        self._sq = None

        self.bg = SpaceBackground()
        self.setCentralWidget(self.bg)

        self.overlay = QtWidgets.QWidget(self.bg)
        self.overlay.setGeometry(self.bg.rect())
        self.overlay.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._build_ui()
        self.bg.installEventFilter(self)
        self.showMaximized()

    def eventFilter(self, s, e):
        if e.type() == QtCore.QEvent.Resize and s is self.bg:
            self.overlay.setGeometry(self.bg.rect())
        return super().eventFilter(s, e)

    # ──────────────────────────────────────────────────
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self.overlay)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_top_bar())

        mid = QtWidgets.QWidget()
        mid.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        hl = QtWidgets.QHBoxLayout(mid)
        hl.setContentsMargins(60, 10, 60, 10)
        hl.setSpacing(0)

        hl.addWidget(self._make_left_info(),    alignment=QtCore.Qt.AlignVCenter)
        hl.addStretch(1)
        hl.addWidget(SiriWidget(),              alignment=QtCore.Qt.AlignVCenter)
        hl.addStretch(1)
        hl.addWidget(self._make_right_buttons(), alignment=QtCore.Qt.AlignVCenter)

        root.addWidget(mid, stretch=1)
        root.addWidget(self._make_bottom_bar())

    # ──────────────────────────────────────────────────
    def _make_top_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(78)

        class _BG(QtWidgets.QWidget):
            def paintEvent(self_, ev):
                p = QtGui.QPainter(self_)
                p.fillRect(self_.rect(), QtGui.QColor(2, 6, 18, 230))
                for w2, a in [(8, 8), (4, 22), (1, 110)]:
                    pen = QtGui.QPen(QtGui.QColor(0, 180, 255, a))
                    pen.setWidth(w2); p.setPen(pen)
                    p.drawLine(0, self_.height()-1, self_.width(), self_.height()-1)

        bg = _BG(bar); bg.setGeometry(0, 0, 4000, 78); bg.lower()

        hl = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(36, 0, 36, 0)

        aura = QtWidgets.QLabel("AURA")
        aura.setStyleSheet("""
            color: rgba(0,200,255,230); font-family:'Courier New';
            font-size:30px; font-weight:bold; letter-spacing:8px;""")
        hl.addWidget(aura)

        school = QtWidgets.QLabel("KOTHARIS")
        school.setAlignment(QtCore.Qt.AlignCenter)
        school.setStyleSheet("""
            color: rgba(0,230,255,255); font-family:'Courier New';
            font-size:40px; font-weight:bold; letter-spacing:16px;""")
        fx = QtWidgets.QGraphicsDropShadowEffect()
        fx.setOffset(0,0); fx.setBlurRadius(28)
        fx.setColor(QtGui.QColor(0, 200, 255, 180))
        school.setGraphicsEffect(fx)
        hl.addWidget(school, stretch=1)

        col = QtWidgets.QVBoxLayout(); col.setSpacing(3)
        self.clock_lbl = QtWidgets.QLabel()
        self.clock_lbl.setStyleSheet("""
            color:rgba(0,180,255,180); font-family:'Courier New';
            font-size:12px; letter-spacing:2px;""")
        col.addWidget(self.clock_lbl, alignment=QtCore.Qt.AlignRight)
        col.addWidget(BlinkDot("SYS ONLINE", QtGui.QColor(0,220,255)),
                      alignment=QtCore.Qt.AlignRight)
        hl.addLayout(col)

        self._clk = QtCore.QTimer(self)
        self._clk.timeout.connect(lambda: self.clock_lbl.setText(
            time.strftime("%Y-%m-%d  %H:%M:%S")))
        self._clk.start(1000)
        self.clock_lbl.setText(time.strftime("%Y-%m-%d  %H:%M:%S"))
        return bar

    # ──────────────────────────────────────────────────
    def _make_left_info(self):
        w = QtWidgets.QWidget()
        w.setFixedWidth(210)
        w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        vl = QtWidgets.QVBoxLayout(w)
        vl.setSpacing(20); vl.setContentsMargins(0,0,0,0)
        vl.setAlignment(QtCore.Qt.AlignTop)

        def card(title, value, vc="rgba(0,210,255,210)"):
            c = QtWidgets.QWidget()
            c.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            cl = QtWidgets.QVBoxLayout(c)
            cl.setSpacing(1); cl.setContentsMargins(0,0,0,0)
            t = QtWidgets.QLabel(title)
            t.setStyleSheet("color:rgba(0,140,200,130);font-family:'Courier New';"
                            "font-size:9px;letter-spacing:3px;")
            v = QtWidgets.QLabel(value)
            v.setStyleSheet(f"color:{vc};font-family:'Courier New';"
                            "font-size:16px;font-weight:bold;letter-spacing:1px;")
            sep = QtWidgets.QFrame()
            sep.setFrameShape(QtWidgets.QFrame.HLine)
            sep.setStyleSheet("color:rgba(0,160,220,35);")
            cl.addWidget(t); cl.addWidget(v); cl.addWidget(sep)
            return c

        vl.addWidget(card("SYSTEM",    "AURA v2.0"))
        vl.addWidget(card("INSTITUTE", "KOTHARIS"))
        vl.addWidget(card("MODE",      "STANDBY",  "rgba(0,255,180,230)"))
        vl.addWidget(card("SUBJECTS",  f"{random.randint(4,12)} LOADED"))
        vl.addSpacing(10)
        vl.addWidget(BlinkDot("ACTIVE",    QtGui.QColor(0, 200, 255)))
        vl.addWidget(BlinkDot("CAMERA OK", QtGui.QColor(0, 255, 160)))
        vl.addStretch()
        return w

    # ──────────────────────────────────────────────────
    def _make_right_buttons(self):
        w = QtWidgets.QWidget()
        w.setFixedWidth(320)
        w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        vl = QtWidgets.QVBoxLayout(w)
        vl.setSpacing(12); vl.setContentsMargins(0,0,0,0)
        vl.setAlignment(QtCore.Qt.AlignVCenter)

        hdr = QtWidgets.QLabel("── OPERATIONS ──")
        hdr.setStyleSheet("color:rgba(0,160,220,110);font-family:'Courier New';"
                          "font-size:10px;letter-spacing:4px;")
        vl.addWidget(hdr, alignment=QtCore.Qt.AlignCenter)
        vl.addSpacing(6)

        self.btn_start  = GlowButton("▶   START RECOGNITION", QtGui.QColor(0, 210, 255))
        self.btn_train  = GlowButton("◈   TRAIN DATA",        QtGui.QColor(255, 180, 0))
        self.btn_manage = GlowButton("⬡   MANAGE DATASET",    QtGui.QColor(180, 80, 255))
        self.btn_sq     = GlowButton("◎   QUERY MODE",        QtGui.QColor(0, 180, 255))
        self.btn_stop   = GlowButton("⏹   STOP LISTENING",   QtGui.QColor(255, 80, 80))
        self.btn_exit   = GlowButton("✕   EXIT",              QtGui.QColor(255, 50, 70))

        for b in [self.btn_start, self.btn_train,
                  self.btn_manage, self.btn_sq, self.btn_stop, self.btn_exit]:
            b.setFixedWidth(300)
            vl.addWidget(b)

        self.btn_start.clicked.connect(self._run_start)
        self.btn_train.clicked.connect(self._run_train)
        self.btn_manage.clicked.connect(self._run_manage)
        self.btn_sq.clicked.connect(self._run_sq)
        self.btn_stop.clicked.connect(self._run_stop)
        self.btn_exit.clicked.connect(self._run_exit)
        return w

    # ──────────────────────────────────────────────────
    def _make_bottom_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(40)

        class _BG(QtWidgets.QWidget):
            def paintEvent(self_, ev):
                p = QtGui.QPainter(self_)
                p.fillRect(self_.rect(), QtGui.QColor(2,6,18,215))
                for w2,a in [(5,8),(2,25),(1,90)]:
                    pen = QtGui.QPen(QtGui.QColor(0,160,255,a))
                    pen.setWidth(w2); p.setPen(pen)
                    p.drawLine(0,0,self_.width(),0)

        bg = _BG(bar); bg.setGeometry(0,0,4000,40); bg.lower()

        hl = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(30,0,30,0)

        self.status_lbl = QtWidgets.QLabel("● SYSTEM READY")
        self.status_lbl.setFixedWidth(900)           # ← FIX: cap width so bar never stretches
        self.status_lbl.setStyleSheet("""
            color:rgba(0,200,255,180); font-family:'Courier New';
            font-size:12px; letter-spacing:3px;""")
        hl.addWidget(self.status_lbl)
        hl.addStretch()

        ver = QtWidgets.QLabel("AURA/2.0  ·  KOTHARIS INSTITUTE  ·  AI RECOGNITION SYSTEM")
        ver.setStyleSheet("color:rgba(0,120,180,90);font-family:'Courier New';"
                          "font-size:10px;letter-spacing:2px;")
        hl.addWidget(ver)
        return bar

    # ── helpers ───────────────────────────────────────
    def _status(self, msg, color="rgba(0,200,255,180)"):
        self.status_lbl.setStyleSheet(f"color:{color};font-family:'Courier New';"
                                       "font-size:12px;letter-spacing:3px;")
        # ← FIX: truncate very long lines so the bottom bar never gets pushed right
        max_chars = 90
        display = msg if len(msg) <= max_chars else msg[:max_chars - 3] + "..."
        self.status_lbl.setText(f"● {display}")

    def _status_reset(self):
        self._status("SYSTEM READY")

    # ══════════════════════════════════════════════════
    #  BUTTON ACTIONS  — original logic preserved
    # ══════════════════════════════════════════════════
    def _run_start(self):
        script_path = os.path.join(os.path.dirname(__file__), "recognise-vertical.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "recognise.py not found in the app folder.")
            return
        try:
            self._status("RECOGNIZING...", "rgba(0,200,255,220)")
            subprocess.Popen([sys.executable, script_path])
            QtCore.QTimer.singleShot(3000, self._status_reset)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run recognise.py:\n{e}")

    def _run_train(self):
        script_path = os.path.join(os.path.dirname(__file__), "train.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "train.py not found in the app folder.")
            return
        person_name, ok = QtWidgets.QInputDialog.getText(
            self, "Enter Name", "Enter the person's name for training:")
        if ok and person_name.strip():
            try:
                name = person_name.strip()
                self._status(f"REGISTERING {name.upper()}...", "rgba(0,255,180,220)")
                self._train_proc = QtCore.QProcess(self)
                self._train_proc.finished.connect(lambda: self._train_done(name))
                self._train_proc.start(sys.executable, [script_path, name])
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run train.py:\n{e}")

    def _train_done(self, name):
        self._status(f"{name.upper()} REGISTRATION COMPLETE!", "rgba(0,255,120,230)")
        QtCore.QTimer.singleShot(3000, self._status_reset)

    # def _run_manage(self):
    #     subprocess.run(["sudo", "systemctl", "stop", "face-recognition.service"])
    #     self._status("OPENING DATASET FOLDER...", "rgba(120,100,255,220)")
    #     data_path = os.path.join(os.path.dirname(__file__), "data")
    #     if not os.path.exists(data_path):
    #         os.makedirs(data_path, exist_ok=True)
    #     if sys.platform.startswith("win"):
    #         os.startfile(data_path)
    #     elif sys.platform.startswith("darwin"):
    #         subprocess.Popen(["open", data_path])
    #     else:
    #         subprocess.Popen(["xdg-open", data_path])
    #     QtCore.QTimer.singleShot(1500, self._status_reset)
    #     # QtCore.QTimer.singleShot(3000, lambda: subprocess.run(["sudo", "systemctl", "start", "face-recognition.service"]))
    #     subprocess.run(["sudo", "systemctl", "start", "face-recognition.service"])
    # # ── QUERY MODE: launch school_queries.py + open ListenWindow popup



    
    def _run_manage(self):
        subprocess.run(["sudo", "systemctl", "stop", "face-recognition.service"])
        self._status("OPENING DATASET FOLDER...", "rgba(120,100,255,220)")
        data_path = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(data_path):
            os.makedirs(data_path, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(data_path)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", data_path])
        else:
            subprocess.Popen(["xdg-open", data_path])
        # time.sleep(2)
        # Wait for user to finish
        # msg = QtWidgets.QMessageBox(self)
        # msg.setWindowTitle("Managing Dataset")
        # msg.setText("Dataset folder is open.\n\nClick OK when you are done to resume the system.")
        # msg.setWindowFlags(msg.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        # msg.exec_()
        # QtWidgets.QMessageBox.information(
        # self, "Managing Dataset",
        # "Dataset folder is open.\n\nClick OK when you are done to resume the system.")
        
        # subprocess.run(["sudo", "systemctl", "start", "face-recognition.service"])
        self._status("SYSTEM RESUMED", "rgba(0,255,180,220)")
        QtCore.QTimer.singleShot(2000, self._status_reset)




    def _run_sq(self):
        """Open the QueryModeWindow category picker first."""
        self._query_win = QueryModeWindow(self)
        self._query_win.subject_selected.connect(self._launch_sq_for_subject)
        self._query_win.show()

    def _launch_sq_for_subject(self, category):
        """Called when user picks a category — stop service and launch school_queries.py."""
        subprocess.run(["sudo", "systemctl", "stop", "face-recognition.service"])

        if sys.platform.startswith("win"):
            project_dir = r"C:\DataAnalysis\Batadal"
            venv_python = os.path.join(project_dir, "venv", "Scripts", "python.exe")
        else:
            project_dir = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main"
            venv_python = os.path.join(project_dir, "venv", "bin", "python")

        script_path = os.path.join(project_dir, "school_queries.py")
        python_exe  = venv_python if os.path.exists(venv_python) else sys.executable

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", f"Script not found at:\n{script_path}")
            subprocess.run(["sudo", "systemctl", "start", "face-recognition.service"])
            return

        if self._sq and self._sq.state() != QtCore.QProcess.NotRunning:
            self._sq.kill()

        self._listen_win = ListenWindow(self)
        self._listen_win.stop_requested.connect(self._run_sq_stop)

        self._status(f"QUERY MODE  ·  {category.upper()}...", "rgba(0,180,255,220)")
        self._sq = QtCore.QProcess(self)
        self._sq.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._sq.readyReadStandardOutput.connect(self._on_sq_output)
        self._sq.finished.connect(self._on_sq_finished)
        self._sq.setWorkingDirectory(project_dir)
        self._sq.start(python_exe, ["-u", script_path])

    def _on_sq_output(self):
        data = self._sq.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.strip().splitlines():
            line = line.strip()
            if line:
                self._status(line, "rgba(0,180,255,220)")
                if self._listen_win and self._listen_win.isVisible():
                    self._listen_win.set_status_line(line.upper())

    def _on_sq_finished(self):
        subprocess.run(["sudo", "systemctl", "start", "face-recognition.service"])
        if self._listen_win and self._listen_win.isVisible():
            self._listen_win.switch_to_processing()
            QtCore.QTimer.singleShot(2500, self._close_listen_win)
        self._status("DONE", "rgba(0,180,255,220)")

    def _run_sq_stop(self):
        if self._sq and self._sq.state() != QtCore.QProcess.NotRunning:
            self._sq.kill()
        if self._listen_win and self._listen_win.isVisible():
            self._listen_win.close()
        subprocess.run(["sudo", "systemctl", "start", "face-recognition.service"])
        self._status("STOPPED", "rgba(255,80,80,220)")
        QtCore.QTimer.singleShot(2000, self._status_reset)

    def _close_listen_win(self):
        if self._listen_win and self._listen_win.isVisible():
            self._listen_win.close()
        self._status_reset()

    def _run_stop(self):
        if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
            self._stt_process.kill()
        if self._listen_win and self._listen_win.isVisible():
            self._listen_win.close()
        self._status("STOPPED", "rgba(255,80,80,220)")
        QtCore.QTimer.singleShot(2000, self._status_reset)

    def _run_exit(self):
        self._status("EXITING...", "rgba(255,60,80,220)")
        reply = QtWidgets.QMessageBox.question(
            self, "Exit AURA", "Exit AURA Interface?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
                self._stt_process.kill()
            QtWidgets.QApplication.quit()
        else:
            self._status_reset()


# ══════════════════════════════════════════════════════
def main():
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    w = AuraMain()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
























# try:
#     from PyQt5 import QtCore, QtGui, QtWidgets
# except ImportError:
#     from PySide6 import QtCore, QtGui, QtWidgets

# import threading
# import sys, os, time, math, random, subprocess

# # ─────────────────────────────────────────────
# #  PAUSE FLAG  (shared with distancerecognition11.py)
# # ─────────────────────────────────────────────
# PAUSE_FLAG = "/tmp/aura_pause"


# # ══════════════════════════════════════════════════════
# #  SIRI-STYLE WAVEFORM WIDGET
# # ══════════════════════════════════════════════════════
# class SiriWidget(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setFixedSize(460, 460)
#         self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         self._t = 0.0
#         self._breathing = 0.0

#         t = QtCore.QTimer(self)
#         t.timeout.connect(self._tick)
#         t.start(16)              # ~60fps

#     def _tick(self):
#         self._t += 0.052                  # medium-fast speed
#         self._breathing = 0.5 + 0.5 * math.sin(self._t * 0.55)
#         self.update()

#     _COLORS = [
#         (0,   220, 255),
#         (0,   140, 255),
#         (60,  80,  255),
#         (0,   255, 200),
#         (140, 80,  255),
#         (0,   255, 160),
#     ]

#     def paintEvent(self, _):
#         p = QtGui.QPainter(self)
#         p.setRenderHint(QtGui.QPainter.Antialiasing)
#         p.fillRect(self.rect(), QtCore.Qt.transparent)
#         cx = self.width()  / 2
#         cy = self.height() / 2
#         R  = 190

#         sphere = QtGui.QRadialGradient(cx, cy, R)
#         sphere.setColorAt(0.0,  QtGui.QColor(8,  18, 45, 220))
#         sphere.setColorAt(0.55, QtGui.QColor(4,  10, 30, 210))
#         sphere.setColorAt(0.85, QtGui.QColor(0,   5, 18, 190))
#         sphere.setColorAt(1.0,  QtGui.QColor(0,   0,  0,   0))
#         p.setBrush(sphere); p.setPen(QtCore.Qt.NoPen)
#         p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)

#         for width, alpha in [(18, 6), (10, 18), (5, 45), (2, 90), (1, 150)]:
#             pen = QtGui.QPen(QtGui.QColor(0, 180, 255, alpha))
#             pen.setWidth(width); p.setPen(pen); p.setBrush(QtCore.Qt.NoBrush)
#             p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)

#         clip_path = QtGui.QPainterPath()
#         clip_path.addEllipse(QtCore.QRectF(cx - R, cy - R, R * 2, R * 2))
#         p.setClipPath(clip_path)

#         steps = 400; n = len(self._COLORS)
#         for i, (r, g, b) in enumerate(self._COLORS):
#             phase_off = i * (2 * math.pi / n)
#             amp_base  = 28 + i * 4
#             freq      = 2.0 + i * 0.42
#             speed     = 0.9 + i * 0.15
#             path = QtGui.QPainterPath(); first = True
#             for s in range(steps + 1):
#                 x  = (cx - R) + s / steps * (R * 2)
#                 nx = (x - cx) / R
#                 ellipse_h = math.sqrt(max(0.0, 1.0 - nx * nx))
#                 envelope  = ellipse_h * 0.55 * (1.0 + 0.20 * self._breathing)
#                 y_off = (
#                     math.sin(nx * math.pi * freq        + self._t * speed        + phase_off) * amp_base * envelope
#                     + math.sin(nx * math.pi * freq * 1.9 + self._t * speed * 1.4 + phase_off * 1.6) * amp_base * 0.40 * envelope
#                     + math.sin(nx * math.pi * freq * 0.55 + self._t * speed * 0.6 + phase_off * 0.8) * amp_base * 0.28 * envelope
#                 )
#                 if first: path.moveTo(x, cy + y_off); first = False
#                 else:     path.lineTo(x, cy + y_off)
#             for gw, ga in [(5, 12), (2, 25)]:
#                 gp = QtGui.QPen(QtGui.QColor(r, g, b, ga))
#                 gp.setWidth(gw); gp.setCapStyle(QtCore.Qt.RoundCap)
#                 p.setPen(gp); p.setBrush(QtCore.Qt.NoBrush); p.drawPath(path)
#             al = int(205 + 50 * math.sin(self._t + phase_off))
#             lp = QtGui.QPen(QtGui.QColor(r, g, b, al))
#             lp.setWidth(1); lp.setCapStyle(QtCore.Qt.RoundCap)
#             p.setPen(lp); p.drawPath(path)

#         p.setClipping(False)
#         dot_r = int(6 + 5 * self._breathing)
#         dot_a = int(180 + 75 * self._breathing)
#         dg = QtGui.QRadialGradient(cx, cy, dot_r * 4)
#         dg.setColorAt(0.0, QtGui.QColor(100, 180, 255, dot_a))
#         dg.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
#         p.setBrush(dg); p.setPen(QtCore.Qt.NoPen)
#         p.drawEllipse(int(cx - dot_r*4), int(cy - dot_r*4), dot_r*8, dot_r*8)
#         p.setBrush(QtGui.QColor(200, 230, 255, dot_a))
#         p.drawEllipse(int(cx - dot_r), int(cy - dot_r), dot_r*2, dot_r*2)
#         shine = QtGui.QRadialGradient(cx - R*0.3, cy - R*0.35, R*0.5)
#         shine.setColorAt(0.0, QtGui.QColor(255, 255, 255, 22))
#         shine.setColorAt(1.0, QtGui.QColor(255, 255, 255,  0))
#         p.setBrush(shine); p.setPen(QtCore.Qt.NoPen)
#         p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)


# # ══════════════════════════════════════════════════════
# #  THINKING SPINNER  (3 orbiting arcs + pulse dot)
# # ══════════════════════════════════════════════════════
# class ThinkingSpinner(QtWidgets.QWidget):
#     def __init__(self, size=280, parent=None):
#         super().__init__(parent)
#         self.setFixedSize(size, size)
#         self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         self._t = 0.0; self._pulse = 0.0
#         t = QtCore.QTimer(self); t.timeout.connect(self._tick); t.start(16)

#     def _tick(self):
#         self._t    += 0.045
#         self._pulse = 0.5 + 0.5 * math.sin(self._t * 1.8)
#         self.update()

#     def paintEvent(self, _):
#         p = QtGui.QPainter(self)
#         p.setRenderHint(QtGui.QPainter.Antialiasing)
#         p.fillRect(self.rect(), QtCore.Qt.transparent)
#         cx, cy = self.width() / 2, self.height() / 2
#         scale  = self.width() / 200.0
#         arcs = [
#             (72, 4, 200,   0, 220, 255,  1.00,   0),   # bright cyan
#             (50, 3, 160,   0, 255, 160, -1.45,  40),   # mint
#             (30, 2, 120, 140,  80, 255,  2.10,  80),   # violet
#         ]
#         for radius, pen_w, alpha, r, g, b, speed, span_off in arcs:
#             radius = radius * scale; pen_w = max(1, int(pen_w * scale))
#             angle  = math.degrees(self._t * speed) % 360
#             span   = 260 + span_off
#             rect   = QtCore.QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
#             gpen   = QtGui.QPen(QtGui.QColor(r, g, b, alpha // 4))
#             gpen.setWidth(pen_w + int(6 * scale)); gpen.setCapStyle(QtCore.Qt.RoundCap)
#             p.setPen(gpen); p.setBrush(QtCore.Qt.NoBrush)
#             p.drawArc(rect, int(angle * 16), int(span * 16))
#             pen = QtGui.QPen(QtGui.QColor(r, g, b, alpha))
#             pen.setWidth(pen_w); pen.setCapStyle(QtCore.Qt.RoundCap)
#             p.setPen(pen); p.drawArc(rect, int(angle * 16), int(span * 16))

#         dot_r  = int((7 + 5 * self._pulse) * scale)
#         dot_al = int(160 + 95 * self._pulse)
#         dg = QtGui.QRadialGradient(cx, cy, dot_r * 3)
#         dg.setColorAt(0.0, QtGui.QColor(0, 220, 255, dot_al))
#         dg.setColorAt(1.0, QtGui.QColor(0,   0,   0,  0))
#         p.setBrush(dg); p.setPen(QtCore.Qt.NoPen)
#         p.drawEllipse(int(cx - dot_r*3), int(cy - dot_r*3), dot_r*6, dot_r*6)
#         p.setBrush(QtGui.QColor(180, 230, 255, dot_al))
#         p.drawEllipse(int(cx - dot_r), int(cy - dot_r), dot_r*2, dot_r*2)


# # ══════════════════════════════════════════════════════
# #  SCAN BAR
# # ══════════════════════════════════════════════════════
# class _ScanBar(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         self._t = 0.0
#         t = QtCore.QTimer(self); t.timeout.connect(self._tick); t.start(16)

#     def _tick(self):
#         self._t = (self._t + 0.022) % 1.0
#         self.update()

#     def paintEvent(self, _):
#         p = QtGui.QPainter(self)
#         p.setRenderHint(QtGui.QPainter.Antialiasing)
#         w, h = self.width(), self.height()
#         p.setBrush(QtGui.QColor(0, 60, 90, 80)); p.setPen(QtCore.Qt.NoPen)
#         p.drawRoundedRect(0, 0, w, h, h//2, h//2)
#         blob_w = int(w * 0.35)
#         x = int((self._t * (w + blob_w)) - blob_w)
#         g = QtGui.QLinearGradient(x, 0, x + blob_w, 0)
#         g.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
#         g.setColorAt(0.4, QtGui.QColor(0, 220, 255, 200))
#         g.setColorAt(0.6, QtGui.QColor(0, 255, 180, 180))
#         g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
#         p.setBrush(g)
#         p.drawRoundedRect(max(0, x), 0, min(blob_w, w - max(0, x)), h, h//2, h//2)


# # ══════════════════════════════════════════════════════
# #  LISTEN WINDOW  — fullscreen popup while stt.py runs
# # ══════════════════════════════════════════════════════
# class ListenWindow(QtWidgets.QDialog):
#     # stop_requested = QtCore.pyqtSignal()
#     try:
#         stop_requested = QtCore.pyqtSignal()
#     except AttributeError:
#         stop_requested = QtCore.Signal()
#     _PHASES_RECORDING   = ["RECORDING", "LISTENING"]
#     _PHASES_PROCESSING  = ["PROCESSING", "ANALYZING", "THINKING", "TRANSCRIBING"]
#     _PHASES = ["RECORDING", "LISTENING"]  # default = recording phase

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("AURA — Listen Mode")
#         self.setWindowFlags(
#             QtCore.Qt.Window |
#             QtCore.Qt.FramelessWindowHint |
#             QtCore.Qt.WindowStaysOnTopHint
#         )
#         self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         self._phase = 0; self._dots = 0
#         self._build_ui()
#         self._cycle_timer = QtCore.QTimer(self)
#         self._cycle_timer.timeout.connect(self._cycle_text)
#         self._cycle_timer.start(400)
#         self.showMaximized()

#     def _build_ui(self):
#         root = QtWidgets.QVBoxLayout(self)
#         root.setContentsMargins(0, 0, 0, 0)
#         root.setSpacing(0)
#         root.setAlignment(QtCore.Qt.AlignCenter)

#         # top label
#         top = QtWidgets.QLabel("◎  AURA  —  LISTEN MODE  —  AUDIO PROCESSING")
#         top.setAlignment(QtCore.Qt.AlignCenter)
#         top.setStyleSheet("""
#             color: rgba(0,200,255,160); font-family: 'Courier New';
#             font-size: 13px; font-weight: bold; letter-spacing: 6px;
#             padding-top: 50px;
#         """)
#         root.addWidget(top)
#         root.addSpacing(50)

#         # spinner
#         self.spinner = ThinkingSpinner(size=320)
#         root.addWidget(self.spinner, alignment=QtCore.Qt.AlignCenter)
#         root.addSpacing(44)

#         # animated status label
#         self.status_lbl = QtWidgets.QLabel("RECORDING")
#         self.status_lbl.setAlignment(QtCore.Qt.AlignCenter)
#         self.status_lbl.setWordWrap(True)
#         self.status_lbl.setFixedWidth(700)
#         self.status_lbl.setMinimumHeight(48)
#         self.status_lbl.setStyleSheet("""
#             color: rgba(0,255,180,240); font-family: 'Courier New';
#             font-size: 32px; font-weight: bold; letter-spacing: 8px;
#         """)
#         fx = QtWidgets.QGraphicsDropShadowEffect()
#         fx.setOffset(0, 0); fx.setBlurRadius(28)
#         fx.setColor(QtGui.QColor(0, 255, 180, 130))
#         self.status_lbl.setGraphicsEffect(fx)
#         root.addWidget(self.status_lbl, alignment=QtCore.Qt.AlignCenter)
#         root.addSpacing(14)

#         # sub label
#         self.sub_lbl = QtWidgets.QLabel("SPEAK NOW  ·  AUDIO CAPTURE IN PROGRESS")
#         self.sub_lbl.setAlignment(QtCore.Qt.AlignCenter)
#         self.sub_lbl.setWordWrap(True)
#         self.sub_lbl.setFixedWidth(720)
#         self.sub_lbl.setMinimumHeight(52)
#         self.sub_lbl.setStyleSheet("""
#             color: rgba(0,160,220,180); font-family: 'Courier New';
#             font-size: 11px; letter-spacing: 3px;
#         """)
#         root.addWidget(self.sub_lbl, alignment=QtCore.Qt.AlignCenter)
#         root.addSpacing(40)

#         # scan bar
#         self.bar = _ScanBar()
#         self.bar.setFixedSize(520, 7)
#         root.addWidget(self.bar, alignment=QtCore.Qt.AlignCenter)
#         root.addSpacing(52)

#         # STOP button
#         self.btn_stop = QtWidgets.QPushButton("  ■   STOP RECORDING")
#         self.btn_stop.setFixedSize(280, 52)
#         self.btn_stop.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
#         self.btn_stop.setFocusPolicy(QtCore.Qt.NoFocus)
#         self.btn_stop.setStyleSheet("""
#             QPushButton {
#                 background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
#                     stop:0 rgba(180,20,20,210), stop:1 rgba(120,10,10,230));
#                 border: 1px solid rgba(255,60,60,180);
#                 border-left: 4px solid rgba(255,80,80,255);
#                 border-radius: 8px; color: rgba(255,110,110,240);
#                 font-family: 'Courier New'; font-size: 15px;
#                 font-weight: bold; letter-spacing: 3px;
#             }
#             QPushButton:hover {
#                 background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
#                     stop:0 rgba(255,50,50,230), stop:1 rgba(200,20,20,250));
#                 border: 2px solid rgba(255,80,80,255);
#                 color: rgba(255,255,255,255);
#             }
#             QPushButton:pressed { background: rgba(255,30,30,210); }
#         """)
#         sfx = QtWidgets.QGraphicsDropShadowEffect(self.btn_stop)
#         sfx.setOffset(0, 0); sfx.setBlurRadius(18)
#         sfx.setColor(QtGui.QColor(255, 50, 50, 160))
#         self.btn_stop.setGraphicsEffect(sfx)
#         self.btn_stop.clicked.connect(self._on_stop)
#         root.addWidget(self.btn_stop, alignment=QtCore.Qt.AlignCenter)
#         root.addStretch()

#     def paintEvent(self, _):
#         p = QtGui.QPainter(self)
#         p.setRenderHint(QtGui.QPainter.Antialiasing)
#         p.fillRect(self.rect(), QtGui.QColor(2, 5, 15, 248))
#         g1 = QtGui.QRadialGradient(self.width()*0.8, self.height()*0.1, self.width()*0.4)
#         g1.setColorAt(0.0, QtGui.QColor(0, 20, 60, 60)); g1.setColorAt(1.0, QtGui.QColor(0,0,0,0))
#         p.fillRect(self.rect(), g1)
#         g2 = QtGui.QRadialGradient(self.width()*0.1, self.height()*0.85, self.width()*0.35)
#         g2.setColorAt(0.0, QtGui.QColor(0, 40, 60, 40)); g2.setColorAt(1.0, QtGui.QColor(0,0,0,0))
#         p.fillRect(self.rect(), g2)
#         pen = QtGui.QPen(QtGui.QColor(0, 180, 255, 4))
#         pen.setWidth(1); p.setPen(pen)
#         for y in range(0, self.height(), 4):
#             p.drawLine(0, y, self.width(), y)
#         for bw, ba in [(12, 4), (6, 12), (2, 40), (1, 100)]:
#             pen2 = QtGui.QPen(QtGui.QColor(0, 200, 255, ba))
#             pen2.setWidth(bw); p.setPen(pen2); p.setBrush(QtCore.Qt.NoBrush)
#             p.drawRect(bw//2, bw//2, self.width()-bw, self.height()-bw)
#         accent = QtGui.QLinearGradient(0, 0, self.width(), 0)
#         accent.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
#         accent.setColorAt(0.3, QtGui.QColor(0, 220, 255, 200))
#         accent.setColorAt(0.7, QtGui.QColor(0, 160, 255, 180))
#         accent.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
#         p.setPen(QtGui.QPen(QtGui.QBrush(accent), 2))
#         p.drawLine(40, 2, self.width()-40, 2)

#     def _cycle_text(self):
#         self._dots = (self._dots + 1) % 4
#         if self._dots == 0:
#             self._phase = (self._phase + 1) % len(self._PHASES)
#         self.status_lbl.setText(self._PHASES[self._phase] + "." * self._dots + " " * (3 - self._dots))

#     def switch_to_processing(self):
#         self._PHASES = self._PHASES_PROCESSING
#         self._phase  = 0
#         self._dots   = 0
#         self.sub_lbl.setText("TRANSCRIBING AUDIO  ·  PLEASE WAIT")

#     def set_status_line(self, text):
#         self.sub_lbl.setText(text)

#     def _on_stop(self):
#         self._cycle_timer.stop()
#         self.status_lbl.setText("STOPPED")
#         self.stop_requested.emit()
#         QtCore.QTimer.singleShot(500, self.close)


# # ══════════════════════════════════════════════════════
# #  SPACE BACKGROUND
# # ══════════════════════════════════════════════════════
# class SpaceBackground(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.stars = []
#         for _ in range(200):
#             self.stars.append([
#                 random.randint(0, 1920),
#                 random.randint(0, 1080),
#                 random.randint(140, 255),
#                 random.uniform(0, 2 * math.pi),
#                 random.choice([1, 1, 1, 2])
#             ])
#         t = QtCore.QTimer(self)
#         t.timeout.connect(self.update)
#         t.start(80)

#     def paintEvent(self, _):
#         p = QtGui.QPainter(self)
#         p.fillRect(self.rect(), QtGui.QColor(2, 5, 15))
#         for rx, ry, rr, rc in [
#             (0.8, 0.15, 0.35, QtGui.QColor(0, 20, 60, 50)),
#             (0.1, 0.80, 0.30, QtGui.QColor(0, 40, 60, 35)),
#         ]:
#             g = QtGui.QRadialGradient(self.width()*rx, self.height()*ry, self.width()*rr)
#             g.setColorAt(0.0, rc); g.setColorAt(1.0, QtGui.QColor(0,0,0,0))
#             p.fillRect(self.rect(), g)

#         now = time.time()
#         for x, y, br, phase, size in self.stars:
#             b = max(80, min(255, int(br + 40 * math.sin(now * 0.7 + phase))))
#             col = QtGui.QColor(b, b, min(255, b+15))
#             if size == 1:
#                 p.setPen(col); p.drawPoint(x % self.width(), y % self.height())
#             else:
#                 p.setBrush(col); p.setPen(QtCore.Qt.NoPen)
#                 p.drawEllipse(x % self.width(), y % self.height(), 2, 2)


# # ══════════════════════════════════════════════════════
# #  GLOW BUTTON
# # ══════════════════════════════════════════════════════
# class GlowButton(QtWidgets.QPushButton):
#     def __init__(self, text, accent=None, parent=None):
#         super().__init__(text, parent)
#         self.accent = accent or QtGui.QColor(0, 180, 255)
#         self.setFixedHeight(54)
#         self.setMinimumWidth(280)
#         self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
#         self.setFocusPolicy(QtCore.Qt.NoFocus)
#         self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
#         self.shadow.setOffset(0, 0); self.shadow.setBlurRadius(0)
#         self.shadow.setColor(QtGui.QColor(self.accent.red(),
#                                           self.accent.green(),
#                                           self.accent.blue(), 180))
#         self.setGraphicsEffect(self.shadow)
#         self._apply_style(False)

#     def _apply_style(self, h):
#         r, g, b = self.accent.red(), self.accent.green(), self.accent.blue()
#         if h:
#             self.setStyleSheet(f"""QPushButton {{
#                 background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
#                     stop:0 rgba({r},{g},{b},200),
#                     stop:1 rgba({max(r-60,0)},{max(g-60,0)},{max(b-60,0)},230));
#                 border: 2px solid rgba({r},{g},{b},255);
#                 border-left: 5px solid rgba(255,255,255,220);
#                 border-radius: 8px;
#                 color: rgba(255,255,255,255);
#                 font-family: 'Courier New'; font-size: 15px; font-weight: bold;
#                 letter-spacing: 2px; text-align: left; padding-left: 20px;
#             }}""")
#         else:
#             self.setStyleSheet(f"""QPushButton {{
#                 background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
#                     stop:0 rgba({r//5},{g//5},{b//5},200),
#                     stop:1 rgba({r//6},{g//6},{b//6},180));
#                 border: 1px solid rgba({r},{g},{b},160);
#                 border-left: 4px solid rgba({r},{g},{b},255);
#                 border-radius: 8px;
#                 color: rgba({r},{g},{b},230);
#                 font-family: 'Courier New'; font-size: 15px; font-weight: bold;
#                 letter-spacing: 2px; text-align: left; padding-left: 20px;
#             }}""")

#     def enterEvent(self, e):
#         self._apply_style(True)
#         a = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
#         a.setDuration(160); a.setStartValue(0); a.setEndValue(30)
#         a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
#         super().enterEvent(e)

#     def leaveEvent(self, e):
#         self._apply_style(False)
#         a = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
#         a.setDuration(200); a.setStartValue(30); a.setEndValue(0)
#         a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
#         super().leaveEvent(e)


# # ══════════════════════════════════════════════════════
# #  BLINKING DOT
# # ══════════════════════════════════════════════════════
# class BlinkDot(QtWidgets.QWidget):
#     def __init__(self, label="ONLINE", color=None, parent=None):
#         super().__init__(parent)
#         self.label = label
#         self.color = color or QtGui.QColor(0, 255, 120)
#         self.setFixedSize(200, 22)
#         self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         self._a = 255; self._d = -7
#         t = QtCore.QTimer(self); t.timeout.connect(self._tick); t.start(28)

#     def _tick(self):
#         self._a += self._d
#         if self._a <= 50:  self._d =  7
#         if self._a >= 255: self._d = -7
#         self.update()

#     def paintEvent(self, _):
#         p = QtGui.QPainter(self)
#         p.setRenderHint(QtGui.QPainter.Antialiasing)
#         g = QtGui.QRadialGradient(10, 11, 9)
#         c = QtGui.QColor(self.color); c.setAlpha(self._a // 3)
#         g.setColorAt(0, c); g.setColorAt(1, QtGui.QColor(0,0,0,0))
#         p.setBrush(g); p.setPen(QtCore.Qt.NoPen)
#         p.drawEllipse(1, 2, 18, 18)
#         c2 = QtGui.QColor(self.color); c2.setAlpha(self._a)
#         p.setBrush(c2); p.drawEllipse(5, 6, 10, 10)
#         p.setFont(QtGui.QFont("Courier New", 9, QtGui.QFont.Bold))
#         lc = QtGui.QColor(self.color); lc.setAlpha(170)
#         p.setPen(lc)
#         p.drawText(QtCore.QRect(22, 0, 178, 22), QtCore.Qt.AlignVCenter, self.label)


# # ══════════════════════════════════════════════════════
# #  MAIN WINDOW
# # ══════════════════════════════════════════════════════
# class AuraMain(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("AURA — Kotharis")
#         self.resize(1280, 720)
#         self._listening   = False
#         self._stt_process = None
#         self._listen_win  = None
#         self._sq = None

#         self.bg = SpaceBackground()
#         self.setCentralWidget(self.bg)

#         self.overlay = QtWidgets.QWidget(self.bg)
#         self.overlay.setGeometry(self.bg.rect())
#         self.overlay.setAttribute(QtCore.Qt.WA_TranslucentBackground)

#         self._build_ui()
#         self.bg.installEventFilter(self)
#         self.showMaximized()

#     def eventFilter(self, s, e):
#         if e.type() == QtCore.QEvent.Resize and s is self.bg:
#             self.overlay.setGeometry(self.bg.rect())
#         return super().eventFilter(s, e)

#     # ──────────────────────────────────────────────────
#     def _build_ui(self):
#         root = QtWidgets.QVBoxLayout(self.overlay)
#         root.setContentsMargins(0, 0, 0, 0)
#         root.setSpacing(0)

#         root.addWidget(self._make_top_bar())

#         mid = QtWidgets.QWidget()
#         mid.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         hl = QtWidgets.QHBoxLayout(mid)
#         hl.setContentsMargins(60, 10, 60, 10)
#         hl.setSpacing(0)

#         hl.addWidget(self._make_left_info(),    alignment=QtCore.Qt.AlignVCenter)
#         hl.addStretch(1)
#         hl.addWidget(SiriWidget(),              alignment=QtCore.Qt.AlignVCenter)
#         hl.addStretch(1)
#         hl.addWidget(self._make_right_buttons(), alignment=QtCore.Qt.AlignVCenter)

#         root.addWidget(mid, stretch=1)
#         root.addWidget(self._make_bottom_bar())

#     # ──────────────────────────────────────────────────
#     def _make_top_bar(self):
#         bar = QtWidgets.QWidget()
#         bar.setFixedHeight(78)

#         class _BG(QtWidgets.QWidget):
#             def paintEvent(self_, ev):
#                 p = QtGui.QPainter(self_)
#                 p.fillRect(self_.rect(), QtGui.QColor(2, 6, 18, 230))
#                 for w2, a in [(8, 8), (4, 22), (1, 110)]:
#                     pen = QtGui.QPen(QtGui.QColor(0, 180, 255, a))
#                     pen.setWidth(w2); p.setPen(pen)
#                     p.drawLine(0, self_.height()-1, self_.width(), self_.height()-1)

#         bg = _BG(bar); bg.setGeometry(0, 0, 4000, 78); bg.lower()

#         hl = QtWidgets.QHBoxLayout(bar)
#         hl.setContentsMargins(36, 0, 36, 0)

#         aura = QtWidgets.QLabel("AURA")
#         aura.setStyleSheet("""
#             color: rgba(0,200,255,230); font-family:'Courier New';
#             font-size:30px; font-weight:bold; letter-spacing:8px;""")
#         hl.addWidget(aura)

#         school = QtWidgets.QLabel("KOTHARIS")
#         school.setAlignment(QtCore.Qt.AlignCenter)
#         school.setStyleSheet("""
#             color: rgba(0,230,255,255); font-family:'Courier New';
#             font-size:40px; font-weight:bold; letter-spacing:16px;""")
#         fx = QtWidgets.QGraphicsDropShadowEffect()
#         fx.setOffset(0,0); fx.setBlurRadius(28)
#         fx.setColor(QtGui.QColor(0, 200, 255, 180))
#         school.setGraphicsEffect(fx)
#         hl.addWidget(school, stretch=1)

#         col = QtWidgets.QVBoxLayout(); col.setSpacing(3)
#         self.clock_lbl = QtWidgets.QLabel()
#         self.clock_lbl.setStyleSheet("""
#             color:rgba(0,180,255,180); font-family:'Courier New';
#             font-size:12px; letter-spacing:2px;""")
#         col.addWidget(self.clock_lbl, alignment=QtCore.Qt.AlignRight)
#         col.addWidget(BlinkDot("SYS ONLINE", QtGui.QColor(0,220,255)),
#                       alignment=QtCore.Qt.AlignRight)
#         hl.addLayout(col)

#         self._clk = QtCore.QTimer(self)
#         self._clk.timeout.connect(lambda: self.clock_lbl.setText(
#             time.strftime("%Y-%m-%d  %H:%M:%S")))
#         self._clk.start(1000)
#         self.clock_lbl.setText(time.strftime("%Y-%m-%d  %H:%M:%S"))
#         return bar

#     # ──────────────────────────────────────────────────
#     def _make_left_info(self):
#         w = QtWidgets.QWidget()
#         w.setFixedWidth(210)
#         w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         vl = QtWidgets.QVBoxLayout(w)
#         vl.setSpacing(20); vl.setContentsMargins(0,0,0,0)
#         vl.setAlignment(QtCore.Qt.AlignTop)

#         def card(title, value, vc="rgba(0,210,255,210)"):
#             c = QtWidgets.QWidget()
#             c.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#             cl = QtWidgets.QVBoxLayout(c)
#             cl.setSpacing(1); cl.setContentsMargins(0,0,0,0)
#             t = QtWidgets.QLabel(title)
#             t.setStyleSheet("color:rgba(0,140,200,130);font-family:'Courier New';"
#                             "font-size:9px;letter-spacing:3px;")
#             v = QtWidgets.QLabel(value)
#             v.setStyleSheet(f"color:{vc};font-family:'Courier New';"
#                             "font-size:16px;font-weight:bold;letter-spacing:1px;")
#             sep = QtWidgets.QFrame()
#             sep.setFrameShape(QtWidgets.QFrame.HLine)
#             sep.setStyleSheet("color:rgba(0,160,220,35);")
#             cl.addWidget(t); cl.addWidget(v); cl.addWidget(sep)
#             return c

#         vl.addWidget(card("SYSTEM",    "AURA v2.0"))
#         vl.addWidget(card("INSTITUTE", "KOTHARIS"))
#         vl.addWidget(card("MODE",      "STANDBY",  "rgba(0,255,180,230)"))
#         vl.addWidget(card("SUBJECTS",  f"{random.randint(4,12)} LOADED"))
#         vl.addSpacing(10)
#         vl.addWidget(BlinkDot("ACTIVE",    QtGui.QColor(0, 200, 255)))
#         vl.addWidget(BlinkDot("CAMERA OK", QtGui.QColor(0, 255, 160)))
#         vl.addStretch()
#         return w

#     # ──────────────────────────────────────────────────
#     def _make_right_buttons(self):
#         w = QtWidgets.QWidget()
#         w.setFixedWidth(320)
#         w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         vl = QtWidgets.QVBoxLayout(w)
#         vl.setSpacing(12); vl.setContentsMargins(0,0,0,0)
#         vl.setAlignment(QtCore.Qt.AlignVCenter)

#         hdr = QtWidgets.QLabel("── OPERATIONS ──")
#         hdr.setStyleSheet("color:rgba(0,160,220,110);font-family:'Courier New';"
#                           "font-size:10px;letter-spacing:4px;")
#         vl.addWidget(hdr, alignment=QtCore.Qt.AlignCenter)
#         vl.addSpacing(6)

#         self.btn_start  = GlowButton("▶   START RECOGNITION", QtGui.QColor(0, 210, 255))
#         self.btn_train  = GlowButton("◈   TRAIN DATA",        QtGui.QColor(255, 180, 0))
#         self.btn_manage = GlowButton("⬡   MANAGE DATASET",    QtGui.QColor(180, 80, 255))
#         self.btn_sq     = GlowButton("◎   QUERY MODE",        QtGui.QColor(0, 180, 255))
#         self.btn_stop   = GlowButton("⏹   STOP LISTENING",   QtGui.QColor(255, 80, 80))
#         self.btn_exit   = GlowButton("✕   EXIT",              QtGui.QColor(255, 50, 70))

#         for b in [self.btn_start, self.btn_train,
#                   self.btn_manage, self.btn_sq, self.btn_stop, self.btn_exit]:
#             b.setFixedWidth(300)
#             vl.addWidget(b)

#         self.btn_start.clicked.connect(self._run_start)
#         self.btn_train.clicked.connect(self._run_train)
#         self.btn_manage.clicked.connect(self._run_manage)
#         self.btn_sq.clicked.connect(self._run_sq)
#         self.btn_stop.clicked.connect(self._run_stop)
#         self.btn_exit.clicked.connect(self._run_exit)
#         return w

#     # ──────────────────────────────────────────────────
#     def _make_bottom_bar(self):
#         bar = QtWidgets.QWidget()
#         bar.setFixedHeight(40)

#         class _BG(QtWidgets.QWidget):
#             def paintEvent(self_, ev):
#                 p = QtGui.QPainter(self_)
#                 p.fillRect(self_.rect(), QtGui.QColor(2,6,18,215))
#                 for w2,a in [(5,8),(2,25),(1,90)]:
#                     pen = QtGui.QPen(QtGui.QColor(0,160,255,a))
#                     pen.setWidth(w2); p.setPen(pen)
#                     p.drawLine(0,0,self_.width(),0)

#         bg = _BG(bar); bg.setGeometry(0,0,4000,40); bg.lower()

#         hl = QtWidgets.QHBoxLayout(bar)
#         hl.setContentsMargins(30,0,30,0)

#         self.status_lbl = QtWidgets.QLabel("● SYSTEM READY")
#         self.status_lbl.setFixedWidth(900)
#         self.status_lbl.setStyleSheet("""
#             color:rgba(0,200,255,180); font-family:'Courier New';
#             font-size:12px; letter-spacing:3px;""")
#         hl.addWidget(self.status_lbl)
#         hl.addStretch()

#         ver = QtWidgets.QLabel("AURA/2.0  ·  KOTHARIS INSTITUTE  ·  AI RECOGNITION SYSTEM")
#         ver.setStyleSheet("color:rgba(0,120,180,90);font-family:'Courier New';"
#                           "font-size:10px;letter-spacing:2px;")
#         hl.addWidget(ver)
#         return bar

#     # ── helpers ───────────────────────────────────────
#     def _status(self, msg, color="rgba(0,200,255,180)"):
#         self.status_lbl.setStyleSheet(f"color:{color};font-family:'Courier New';"
#                                        "font-size:12px;letter-spacing:3px;")
#         max_chars = 90
#         display = msg if len(msg) <= max_chars else msg[:max_chars - 3] + "..."
#         self.status_lbl.setText(f"● {display}")

#     def _status_reset(self):
#         self._status("SYSTEM READY")

#     # ── PAUSE / RESUME detection ──────────────────────
#     def _pause_detection(self):
#         """Create flag file → distancerecognition11.py pauses sensor loop."""
#         try:
#             open(PAUSE_FLAG, 'w').close()
#             print("[GUI] Sensor detection PAUSED")
#         except Exception as e:
#             print(f"[GUI] Could not create pause flag: {e}")

#     def _resume_detection(self):
#         """Delete flag file → distancerecognition11.py resumes sensor loop."""
#         try:
#             if os.path.exists(PAUSE_FLAG):
#                 os.remove(PAUSE_FLAG)
#             print("[GUI] Sensor detection RESUMED")
#         except Exception as e:
#             print(f"[GUI] Could not remove pause flag: {e}")

#     # ══════════════════════════════════════════════════
#     #  BUTTON ACTIONS
#     # ══════════════════════════════════════════════════
#     def _run_start(self):
#         script_path = os.path.join(os.path.dirname(__file__), "recognise-vertical.py")
#         if not os.path.exists(script_path):
#             QtWidgets.QMessageBox.warning(self, "Error", "recognise.py not found in the app folder.")
#             return
#         try:
#             self._status("RECOGNIZING...", "rgba(0,200,255,220)")
#             subprocess.Popen([sys.executable, script_path])
#             QtCore.QTimer.singleShot(3000, self._status_reset)
#         except Exception as e:
#             QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run recognise.py:\n{e}")

#     def _run_train(self):
#         script_path = os.path.join(os.path.dirname(__file__), "train.py")
#         if not os.path.exists(script_path):
#             QtWidgets.QMessageBox.warning(self, "Error", "train.py not found in the app folder.")
#             return
#         person_name, ok = QtWidgets.QInputDialog.getText(
#             self, "Enter Name", "Enter the person's name for training:")
#         if ok and person_name.strip():
#             try:
#                 name = person_name.strip()
#                 self._status(f"REGISTERING {name.upper()}...", "rgba(0,255,180,220)")
#                 self._train_proc = QtCore.QProcess(self)
#                 self._train_proc.finished.connect(lambda: self._train_done(name))
#                 self._train_proc.start(sys.executable, [script_path, name])
#             except Exception as e:
#                 QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run train.py:\n{e}")

#     def _train_done(self, name):
#         self._status(f"{name.upper()} REGISTRATION COMPLETE!", "rgba(0,255,120,230)")
#         QtCore.QTimer.singleShot(3000, self._status_reset)

#     def _run_manage(self):
#         self._status("OPENING DATASET FOLDER...", "rgba(120,100,255,220)")
#         data_path = os.path.join(os.path.dirname(__file__), "data")
#         if not os.path.exists(data_path):
#             os.makedirs(data_path, exist_ok=True)
#         if sys.platform.startswith("win"):
#             os.startfile(data_path)
#         elif sys.platform.startswith("darwin"):
#             subprocess.Popen(["open", data_path])
#         else:
#             subprocess.Popen(["xdg-open", data_path])
#         QtCore.QTimer.singleShot(1500, self._status_reset)

#     # ── QUERY MODE ────────────────────────────────────
#     def _run_sq(self):
#         self._pause_detection()   # ← PAUSE sensor while query runs

#         if sys.platform.startswith("win"):
#             project_dir = r"C:\DataAnalysis\Batadal"
#             venv_python = os.path.join(project_dir, "venv", "Scripts", "python.exe")
#         else:
#             project_dir = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main"
#             venv_python = os.path.join(project_dir, "venv", "bin", "python")

#         script_path = os.path.join(project_dir, "school_queries.py")
#         python_exe  = venv_python if os.path.exists(venv_python) else sys.executable

#         if not os.path.exists(script_path):
#             QtWidgets.QMessageBox.warning(self, "Error", f"Script not found at:\n{script_path}")
#             self._resume_detection()  # resume if we can't even start
#             return

#         if self._sq and self._sq.state() != QtCore.QProcess.NotRunning:
#             self._sq.kill()

#         self._listen_win = ListenWindow(self)
#         self._listen_win.stop_requested.connect(self._run_sq_stop)

#         self._status("QUERY MODE...", "rgba(0,180,255,220)")
#         self._sq = QtCore.QProcess(self)
#         self._sq.setProcessChannelMode(QtCore.QProcess.MergedChannels)
#         self._sq.readyReadStandardOutput.connect(self._on_sq_output)
#         self._sq.finished.connect(self._on_sq_finished)
#         self._sq.setWorkingDirectory(project_dir)
#         self._sq.start(python_exe, ["-u", script_path])

#     def _on_sq_output(self):
#         data = self._sq.readAllStandardOutput().data().decode("utf-8", errors="replace")
#         for line in data.strip().splitlines():
#             line = line.strip()
#             if line:
#                 self._status(line, "rgba(0,180,255,220)")
#                 if self._listen_win and self._listen_win.isVisible():
#                     self._listen_win.set_status_line(line.upper())

#     def _on_sq_finished(self):
#         self._resume_detection()  # ← RESUME sensor when query finishes naturally
#         if self._listen_win and self._listen_win.isVisible():
#             self._listen_win.switch_to_processing()
#             QtCore.QTimer.singleShot(2500, self._close_listen_win)
#         self._status("DONE", "rgba(0,180,255,220)")

#     def _run_sq_stop(self):
#         if self._sq and self._sq.state() != QtCore.QProcess.NotRunning:
#             self._sq.kill()
#         if self._listen_win and self._listen_win.isVisible():
#             self._listen_win.close()
#         self._status("STOPPED", "rgba(255,80,80,220)")
#         QtCore.QTimer.singleShot(2000, self._status_reset)
#         self._resume_detection()  # ← RESUME sensor when stop button in ListenWindow clicked

#     def _close_listen_win(self):
#         if self._listen_win and self._listen_win.isVisible():
#             self._listen_win.close()
#         self._status_reset()

#     def _run_stop(self):
#         if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
#             self._stt_process.kill()
#         if self._listen_win and self._listen_win.isVisible():
#             self._listen_win.close()
#         self._status("STOPPED", "rgba(255,80,80,220)")
#         QtCore.QTimer.singleShot(2000, self._status_reset)
#         self._resume_detection()  # ← RESUME sensor when main STOP button clicked

#     def _run_exit(self):
#         self._status("EXITING...", "rgba(255,60,80,220)")
#         reply = QtWidgets.QMessageBox.question(
#             self, "Exit AURA", "Exit AURA Interface?",
#             QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
#         if reply == QtWidgets.QMessageBox.Yes:
#             if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
#                 self._stt_process.kill()
#             self._resume_detection()  # ← clean up flag on exit
#             QtWidgets.QApplication.quit()
#         else:
#             self._status_reset()


# # ══════════════════════════════════════════════════════
# def main():
#     QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
#     QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
#     app = QtWidgets.QApplication(sys.argv)
#     w = AuraMain()
#     w.show()
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()


