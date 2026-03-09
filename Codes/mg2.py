try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    pyqt = 5
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets
    pyqt = 6

import sys, os, time, math, random, subprocess


# ══════════════════════════════════════════════════════
#  RADAR WIDGET  — the blinking centrepiece
# ══════════════════════════════════════════════════════
class RadarWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(380, 380)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.sweep_angle = 0.0
        self.blink_phase = 0.0
        self.blips = []

        for _ in range(6):
            self._spawn_blip()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(22)

    def _spawn_blip(self):
        cx, cy, r = 190, 190, 155
        angle = random.uniform(0, 2 * math.pi)
        dist  = random.uniform(30, r - 10)
        x = cx + dist * math.cos(angle)
        y = cy + dist * math.sin(angle)
        life = random.randint(60, 180)
        self.blips.append([x, y, life, life])

    def _tick(self):
        self.sweep_angle = (self.sweep_angle + 1.2) % 360
        self.blink_phase += 0.07
        alive = []
        for b in self.blips:
            b[2] -= 1
            if b[2] > 0:
                alive.append(b)
        self.blips = alive
        while len(self.blips) < 6:
            self._spawn_blip()
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)

        cx, cy = 190, 190
        R = 155

        # Background circle
        bg = QtGui.QRadialGradient(cx, cy, R)
        bg.setColorAt(0.0, QtGui.QColor(0, 28, 18, 230))
        bg.setColorAt(0.7, QtGui.QColor(0, 16, 10, 220))
        bg.setColorAt(1.0, QtGui.QColor(0,  8,  4, 200))
        p.setBrush(bg)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # Concentric rings
        for i in range(1, 5):
            r2 = int(R * i / 4)
            pen = QtGui.QPen(QtGui.QColor(0, 210, 100, 50 + i * 14))
            pen.setWidth(1)
            p.setPen(pen)
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(cx - r2, cy - r2, r2 * 2, r2 * 2)

        # Crosshairs
        pen = QtGui.QPen(QtGui.QColor(0, 180, 80, 50))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawLine(cx - R, cy, cx + R, cy)
        p.drawLine(cx, cy - R, cx, cy + R)
        d = int(R * 0.707)
        pen.setColor(QtGui.QColor(0, 180, 80, 22))
        p.setPen(pen)
        p.drawLine(cx - d, cy - d, cx + d, cy + d)
        p.drawLine(cx - d, cy + d, cx + d, cy - d)

        # Sweep cone
        sweep_rad = math.radians(self.sweep_angle)
        cone = QtGui.QConicalGradient(cx, cy, -self.sweep_angle)
        cone.setColorAt(0.000,        QtGui.QColor(0, 255, 120, 160))
        cone.setColorAt(55.0 / 360.0, QtGui.QColor(0, 255, 120,   0))
        cone.setColorAt(1.000,        QtGui.QColor(0, 255, 120,   0))
        p.setBrush(cone)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # Leading edge line
        ex = cx + R * math.cos(sweep_rad)
        ey = cy - R * math.sin(sweep_rad)
        pen2 = QtGui.QPen(QtGui.QColor(80, 255, 160, 220))
        pen2.setWidth(2)
        p.setPen(pen2)
        p.drawLine(int(cx), int(cy), int(ex), int(ey))

        # Blips
        for bx, by, life, max_life in self.blips:
            ratio = life / max_life
            blink = 0.5 + 0.5 * math.sin(self.blink_phase * 3 + bx)
            alpha = int(ratio * blink * 255)
            size  = 5 + int((1 - ratio) * 3)
            glow = QtGui.QRadialGradient(bx, by, size * 3)
            glow.setColorAt(0.0, QtGui.QColor(0, 255, 120, alpha))
            glow.setColorAt(1.0, QtGui.QColor(0, 255, 120, 0))
            p.setBrush(glow)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(int(bx - size * 3), int(by - size * 3), size * 6, size * 6)
            p.setBrush(QtGui.QColor(180, 255, 200, alpha))
            p.drawEllipse(int(bx - size // 2), int(by - size // 2), size, size)

        # Outer rim
        for w2, a in [(6, 18), (3, 35), (1, 100)]:
            gp = QtGui.QPen(QtGui.QColor(0, 220, 100, a))
            gp.setWidth(w2)
            p.setPen(gp)
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # Centre blinking dot
        blink_a = int(180 + 75 * math.sin(self.blink_phase))
        p.setBrush(QtGui.QColor(0, 255, 140, blink_a))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - 5, cy - 5, 10, 10)


# ══════════════════════════════════════════════════════
#  SCANLINE OVERLAY
# ══════════════════════════════════════════════════════
class ScanlineOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._offset = 0
        t = QtCore.QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def _tick(self):
        self._offset = (self._offset + 2) % 6
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 16))
        pen.setWidth(1)
        p.setPen(pen)
        y = self._offset
        while y < self.height():
            p.drawLine(0, y, self.width(), y)
            y += 4


# ══════════════════════════════════════════════════════
#  HEX GRID BACKGROUND
# ══════════════════════════════════════════════════════
class HexBackground(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._phase = 0.0
        t = QtCore.QTimer(self)
        t.timeout.connect(self._tick)
        t.start(50)

    def _tick(self):
        self._phase = (self._phase + 0.02) % (2 * math.pi)
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(2, 6, 14))

        vig = QtGui.QRadialGradient(self.width() / 2, self.height() / 2,
                                    max(self.width(), self.height()) * 0.7)
        vig.setColorAt(0.0, QtGui.QColor(0, 20, 40, 0))
        vig.setColorAt(1.0, QtGui.QColor(0,  5, 12, 160))
        p.fillRect(self.rect(), vig)

        size = 38
        w_hex = size * 2
        h_hex = math.sqrt(3) * size
        cols = int(self.width()  / (w_hex * 0.75)) + 3
        rows = int(self.height() / h_hex) + 3

        for row in range(-1, rows):
            for col in range(-1, cols):
                x = col * w_hex * 0.75
                y = row * h_hex + (col % 2) * h_hex / 2
                dx = x - self.width()  / 2
                dy = y - self.height() / 2
                dist = math.sqrt(dx * dx + dy * dy)
                wave = math.sin(self._phase - dist * 0.012)
                alpha = max(3, min(22, int(8 + 10 * wave)))

                pts = [QtCore.QPointF(
                    x + size * math.cos(math.radians(60 * i - 30)),
                    y + size * math.sin(math.radians(60 * i - 30))
                ) for i in range(6)]
                pen = QtGui.QPen(QtGui.QColor(0, 160, 80, alpha))
                pen.setWidth(1)
                p.setPen(pen)
                p.setBrush(QtCore.Qt.NoBrush)
                p.drawPolygon(QtGui.QPolygonF(pts))


# ══════════════════════════════════════════════════════
#  TERMINAL BUTTON
# ══════════════════════════════════════════════════════
class TermButton(QtWidgets.QPushButton):
    def __init__(self, code, label, parent=None):
        super().__init__(label, parent)
        self.code = code
        self._hovered = False
        self.setFixedSize(300, 54)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QtGui.QColor(0, 230, 120, 160))
        self.setGraphicsEffect(self.shadow)
        self._apply_style(False)

    def _apply_style(self, h):
        if h:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 40, 22, 240);
                    border-left: 3px solid rgba(0,255,120,220);
                    border-top: 1px solid rgba(0,255,120,60);
                    border-right: 1px solid rgba(0,255,120,30);
                    border-bottom: 1px solid rgba(0,255,120,30);
                    border-radius: 4px;
                    color: rgba(0,255,140,255);
                    font-family: 'Courier New';
                    font-size: 15px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    text-align: left;
                    padding-left: 18px;
                }""")
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 18, 10, 200);
                    border-left: 3px solid rgba(0,180,80,100);
                    border-top: 1px solid rgba(0,180,80,25);
                    border-right: 1px solid rgba(0,180,80,15);
                    border-bottom: 1px solid rgba(0,180,80,15);
                    border-radius: 4px;
                    color: rgba(0,200,100,180);
                    font-family: 'Courier New';
                    font-size: 15px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    text-align: left;
                    padding-left: 18px;
                }""")

    def enterEvent(self, e):
        self._hovered = True
        self._apply_style(True)
        a = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        a.setDuration(150); a.setStartValue(0); a.setEndValue(28)
        a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._apply_style(False)
        a = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        a.setDuration(200); a.setStartValue(28); a.setEndValue(0)
        a.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QtGui.QPainter(self)
        p.setFont(QtGui.QFont("Courier New", 8))
        c = QtGui.QColor(0, 255, 120, 120) if self._hovered else QtGui.QColor(0, 180, 80, 70)
        p.setPen(c)
        p.drawText(QtCore.QRect(0, 4, self.width() - 8, 20),
                   QtCore.Qt.AlignRight, self.code)


# ══════════════════════════════════════════════════════
#  BLINKING STATUS DOT
# ══════════════════════════════════════════════════════
class BlinkDot(QtWidgets.QWidget):
    def __init__(self, label="ONLINE", color=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = color or QtGui.QColor(0, 255, 120)
        self.setFixedSize(180, 24)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._alpha = 255
        self._dir   = -6
        t = QtCore.QTimer(self)
        t.timeout.connect(self._tick)
        t.start(30)

    def _tick(self):
        self._alpha += self._dir
        if self._alpha <= 60:  self._dir =  6
        if self._alpha >= 255: self._dir = -6
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        glow = QtGui.QRadialGradient(10, 12, 10)
        c = QtGui.QColor(self.color); c.setAlpha(self._alpha // 3)
        glow.setColorAt(0, c); glow.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        p.setBrush(glow); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(0, 2, 20, 20)
        c2 = QtGui.QColor(self.color); c2.setAlpha(self._alpha)
        p.setBrush(c2)
        p.drawEllipse(5, 7, 10, 10)
        p.setFont(QtGui.QFont("Courier New", 9, QtGui.QFont.Bold))
        lc = QtGui.QColor(self.color); lc.setAlpha(180)
        p.setPen(lc)
        p.drawText(QtCore.QRect(22, 0, 160, 24), QtCore.Qt.AlignVCenter, self.label)


# ══════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════
class AuraMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA — Kotharis Mission Control")
        self.resize(1280, 720)

        self.bg = HexBackground()
        self.setCentralWidget(self.bg)

        self.scanlines = ScanlineOverlay(self.bg)
        self.scanlines.setGeometry(self.bg.rect())
        self.scanlines.raise_()

        self.overlay = QtWidgets.QWidget(self.bg)
        self.overlay.setGeometry(self.bg.rect())
        self.overlay.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._build_ui()
        self.bg.installEventFilter(self)
        self.showMaximized()

    def eventFilter(self, s, e):
        if e.type() == QtCore.QEvent.Resize and s is self.bg:
            self.overlay.setGeometry(self.bg.rect())
            self.scanlines.setGeometry(self.bg.rect())
            self.scanlines.raise_()
        return super().eventFilter(s, e)

    # ──────────────────────────────────────────────────
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self.overlay)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_top_bar())

        centre = QtWidgets.QWidget()
        centre.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        hl = QtWidgets.QHBoxLayout(centre)
        hl.setContentsMargins(50, 10, 50, 10)
        hl.setSpacing(0)

        hl.addWidget(self._make_left_panel(), alignment=QtCore.Qt.AlignVCenter)
        hl.addStretch()

        self.radar = RadarWidget()
        hl.addWidget(self.radar, alignment=QtCore.Qt.AlignVCenter)

        hl.addStretch()
        hl.addWidget(self._make_right_panel(), alignment=QtCore.Qt.AlignVCenter)

        root.addWidget(centre, stretch=1)
        root.addWidget(self._make_bottom_bar())

    # ──────────────────────────────────────────────────
    def _make_top_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(80)
        bar.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Dark band + glow line (painted)
        class _BG(QtWidgets.QWidget):
            def paintEvent(self_, ev):
                p = QtGui.QPainter(self_)
                p.fillRect(self_.rect(), QtGui.QColor(0, 8, 4, 215))
                for w2, a in [(6, 12), (3, 30), (1, 100)]:
                    pen = QtGui.QPen(QtGui.QColor(0, 220, 100, a))
                    pen.setWidth(w2); p.setPen(pen)
                    p.drawLine(0, self_.height()-1, self_.width(), self_.height()-1)

        bg = _BG(bar); bg.setGeometry(0, 0, 4000, 80); bg.lower()

        hl = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(30, 0, 30, 0)

        aura_lbl = QtWidgets.QLabel("AURA")
        aura_lbl.setStyleSheet("""
            color: rgba(0,240,120,220); font-family:'Courier New';
            font-size:32px; font-weight:bold; letter-spacing:8px;""")
        hl.addWidget(aura_lbl)

        school_lbl = QtWidgets.QLabel("KOTHARIS")
        school_lbl.setAlignment(QtCore.Qt.AlignCenter)
        school_lbl.setStyleSheet("""
            color: rgba(0,255,140,255); font-family:'Courier New';
            font-size:38px; font-weight:bold; letter-spacing:14px;""")
        glow_fx = QtWidgets.QGraphicsDropShadowEffect()
        glow_fx.setOffset(0,0); glow_fx.setBlurRadius(22)
        glow_fx.setColor(QtGui.QColor(0,255,120,160))
        school_lbl.setGraphicsEffect(glow_fx)
        hl.addWidget(school_lbl, stretch=1)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(2)

        self.clock_lbl = QtWidgets.QLabel()
        self.clock_lbl.setStyleSheet("""
            color:rgba(0,200,100,180); font-family:'Courier New';
            font-size:13px; letter-spacing:2px;""")
        right_col.addWidget(self.clock_lbl, alignment=QtCore.Qt.AlignRight)
        right_col.addWidget(
            BlinkDot("SYS ONLINE", QtGui.QColor(0,255,120)),
            alignment=QtCore.Qt.AlignRight)
        hl.addLayout(right_col)

        self._clock_timer = QtCore.QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()
        return bar

    def _update_clock(self):
        self.clock_lbl.setText(time.strftime("%Y-%m-%d  %H:%M:%S"))

    # ──────────────────────────────────────────────────
    def _make_left_panel(self):
        w = QtWidgets.QWidget()
        w.setFixedWidth(220)
        w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        vl = QtWidgets.QVBoxLayout(w)
        vl.setSpacing(18); vl.setContentsMargins(0,0,0,0)
        vl.setAlignment(QtCore.Qt.AlignTop)

        def readout(title, value, color="rgba(0,220,100,200)"):
            c = QtWidgets.QWidget()
            c.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            cl = QtWidgets.QVBoxLayout(c)
            cl.setSpacing(2); cl.setContentsMargins(0,0,0,0)
            t = QtWidgets.QLabel(title)
            t.setStyleSheet("color:rgba(0,160,70,140);font-family:'Courier New';"
                            "font-size:9px;letter-spacing:3px;")
            v = QtWidgets.QLabel(value)
            v.setStyleSheet(f"color:{color};font-family:'Courier New';"
                            "font-size:15px;font-weight:bold;letter-spacing:1px;")
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)
            line.setStyleSheet("color:rgba(0,180,70,40);")
            cl.addWidget(t); cl.addWidget(v); cl.addWidget(line)
            return c

        vl.addWidget(readout("SYSTEM",    "AURA v2.0"))
        vl.addWidget(readout("INSTITUTE", "KOTHARIS"))
        vl.addWidget(readout("MODE",      "ACTIVE SCAN","rgba(0,255,160,230)"))
        vl.addWidget(readout("TARGETS",   f"{random.randint(3,9)} DETECTED"))
        vl.addWidget(readout("UPTIME",    "00:00:00"))
        vl.addWidget(BlinkDot("SCANNING", QtGui.QColor(0,220,255)))
        vl.addStretch()
        return w

    # ──────────────────────────────────────────────────
    def _make_right_panel(self):
        w = QtWidgets.QWidget()
        w.setFixedWidth(330)
        w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        vl = QtWidgets.QVBoxLayout(w)
        vl.setSpacing(14); vl.setContentsMargins(0,0,0,0)
        vl.setAlignment(QtCore.Qt.AlignVCenter)

        hdr = QtWidgets.QLabel("── OPERATIONS ──")
        hdr.setStyleSheet("color:rgba(0,180,80,120);font-family:'Courier New';"
                          "font-size:10px;letter-spacing:4px;")
        vl.addWidget(hdr, alignment=QtCore.Qt.AlignCenter)

        self.btn_start  = TermButton("[F1]",  "▶  START RECOGNITION")
        self.btn_train  = TermButton("[F2]",  "◈  TRAIN DATA")
        self.btn_manage = TermButton("[F3]",  "⬡  MANAGE DATASET")
        self.btn_listen = TermButton("[F4]",  "◎  LISTEN MODE")
        self.btn_exit   = TermButton("[ESC]", "✕  TERMINATE")

        self.btn_exit.shadow.setColor(QtGui.QColor(255,60,60,160))
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background:rgba(28,4,4,200);
                border-left:3px solid rgba(255,60,60,100);
                border-top:1px solid rgba(255,60,60,25);
                border-right:1px solid rgba(255,60,60,15);
                border-bottom:1px solid rgba(255,60,60,15);
                border-radius:4px; color:rgba(255,120,120,180);
                font-family:'Courier New'; font-size:15px; font-weight:bold;
                letter-spacing:2px; text-align:left; padding-left:18px;
            }
            QPushButton:hover {
                background:rgba(50,6,6,220);
                border-left:3px solid rgba(255,80,80,220);
                color:rgba(255,160,160,240);
            }""")

        for b in [self.btn_start, self.btn_train,
                  self.btn_manage, self.btn_listen, self.btn_exit]:
            vl.addWidget(b)

        self.btn_start.clicked.connect(self.start_recognition)
        self.btn_train.clicked.connect(self.train_data)
        self.btn_manage.clicked.connect(self.manage_dataset)
        self.btn_listen.clicked.connect(self.run_queries)
        self.btn_exit.clicked.connect(self.exit_app)
        return w

    # ──────────────────────────────────────────────────
    def _make_bottom_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(42)
        bar.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        class _BG(QtWidgets.QWidget):
            def paintEvent(self_, ev):
                p = QtGui.QPainter(self_)
                p.fillRect(self_.rect(), QtGui.QColor(0,8,4,200))
                for w2, a in [(5,10),(2,30),(1,90)]:
                    pen = QtGui.QPen(QtGui.QColor(0,200,80,a))
                    pen.setWidth(w2); p.setPen(pen)
                    p.drawLine(0,0,self_.width(),0)

        bg = _BG(bar); bg.setGeometry(0,0,4000,42); bg.lower()

        hl = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(30,0,30,0)

        self.status_lbl = QtWidgets.QLabel("► SYSTEM READY")
        self.status_lbl.setStyleSheet("""
            color:rgba(0,220,100,180); font-family:'Courier New';
            font-size:12px; letter-spacing:3px;""")
        hl.addWidget(self.status_lbl)
        hl.addStretch()

        ver = QtWidgets.QLabel("AURA/2.0  |  KOTHARIS INSTITUTE")
        ver.setStyleSheet("color:rgba(0,140,60,100);font-family:'Courier New';"
                          "font-size:10px;letter-spacing:2px;")
        hl.addWidget(ver)
        return bar

    # ──────────────────────────────────────────────────
    def _set_status(self, msg, color="rgba(0,220,100,180)"):
        self.status_lbl.setStyleSheet(f"color:{color};font-family:'Courier New';"
                                       "font-size:12px;letter-spacing:3px;")
        self.status_lbl.setText(f"► {msg}")

    def _reset_status(self):
        self._set_status("SYSTEM READY")

    # ── Button Actions ────────────────────────────────
    def start_recognition(self):
        script = os.path.join(os.path.dirname(__file__), "recognise.py")
        if not os.path.exists(script):
            QtWidgets.QMessageBox.warning(self,"Error","recognise.py not found."); return
        self.radar.pulse()
        self._set_status("RECOGNITION ACTIVE...", "rgba(0,200,255,200)")
        subprocess.Popen([sys.executable, script])
        QtCore.QTimer.singleShot(3000, self._reset_status)

    def train_data(self):
        script = os.path.join(os.path.dirname(__file__), "train.py")
        if not os.path.exists(script):
            QtWidgets.QMessageBox.warning(self,"Error","train.py not found."); return
        name, ok = QtWidgets.QInputDialog.getText(self,"REGISTER SUBJECT","Enter subject name:")
        if ok and name.strip():
            self._set_status(f"TRAINING — {name.upper()}", "rgba(255,200,0,200)")
            self.training_process = QtCore.QProcess(self)
            self.training_process.finished.connect(lambda: self._training_done(name.strip()))
            self.training_process.start(sys.executable, [script, name.strip()])

    def _training_done(self, name):
        self._set_status(f"REGISTERED: {name.upper()}", "rgba(0,255,120,220)")
        QtCore.QTimer.singleShot(3000, self._reset_status)

    def run_queries(self):
        script = os.path.join(os.path.dirname(__file__), "stt.py")
        if not os.path.exists(script):
            QtWidgets.QMessageBox.warning(self,"Error","stt.py not found."); return
        self.radar.pulse()
        self._set_status("LISTENING MODE ACTIVE", "rgba(0,255,200,200)")
        subprocess.Popen([sys.executable, script])
        QtCore.QTimer.singleShot(3000, self._reset_status)

    def manage_dataset(self):
        self._set_status("OPENING DATASET DIR", "rgba(180,120,255,200)")
        data_path = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_path, exist_ok=True)
        if sys.platform.startswith("win"):   os.startfile(data_path)
        elif sys.platform.startswith("darwin"): subprocess.Popen(["open", data_path])
        else:                                subprocess.Popen(["xdg-open", data_path])
        QtCore.QTimer.singleShot(1500, self._reset_status)

    def exit_app(self):
        reply = QtWidgets.QMessageBox.question(
            self,"TERMINATE","Terminate AURA session?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            QtWidgets.QApplication.quit()


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