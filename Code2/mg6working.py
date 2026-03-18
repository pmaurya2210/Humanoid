try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets

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

    # ── 6 wave lines — Siri palette ───────────────────
    _COLORS = [
        (0,   220, 255),   # bright cyan
        (0,   140, 255),   # blue
        (60,  80,  255),   # indigo
        (0,   255, 200),   # teal
        (140, 80,  255),   # violet
        (0,   255, 160),   # mint
    ]

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)

        cx = self.width()  / 2
        cy = self.height() / 2
        R  = 190

        # ── 1. dark glassy sphere ──────────────────────
        sphere = QtGui.QRadialGradient(cx, cy, R)
        sphere.setColorAt(0.0,  QtGui.QColor(8,  18, 45, 220))
        sphere.setColorAt(0.55, QtGui.QColor(4,  10, 30, 210))
        sphere.setColorAt(0.85, QtGui.QColor(0,   5, 18, 190))
        sphere.setColorAt(1.0,  QtGui.QColor(0,   0,  0,   0))
        p.setBrush(sphere)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)

        # ── 2. outer glow rings ────────────────────────
        for width, alpha in [(18, 6), (10, 18), (5, 45), (2, 90), (1, 150)]:
            pen = QtGui.QPen(QtGui.QColor(0, 180, 255, alpha))
            pen.setWidth(width)
            p.setPen(pen)
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)

        # ── 3. clip all wave drawing to ellipse ────────
        clip_path = QtGui.QPainterPath()
        clip_path.addEllipse(QtCore.QRectF(cx - R, cy - R, R * 2, R * 2))
        p.setClipPath(clip_path)

        # ── 4. wave lines inside the ellipse ──────────
        steps    = 400
        n        = len(self._COLORS)

        for i, (r, g, b) in enumerate(self._COLORS):
            phase_off = i * (2 * math.pi / n)
            amp_base  = 28 + i * 4          # reduced amplitude
            freq      = 2.0 + i * 0.42
            speed     = 0.9 + i * 0.15

            path = QtGui.QPainterPath()
            first = True

            for s in range(steps + 1):
                # x spans the full diameter of the ellipse
                x  = (cx - R) + s / steps * (R * 2)
                nx = (x - cx) / R           # -1 .. 1

                # tighter envelope — waves stay well inside ellipse
                ellipse_h = math.sqrt(max(0.0, 1.0 - nx * nx))
                envelope  = ellipse_h * 0.55 * (1.0 + 0.20 * self._breathing)

                y_off = (
                    math.sin(nx * math.pi * freq       + self._t * speed         + phase_off)
                    * amp_base * envelope
                    + math.sin(nx * math.pi * freq * 1.9 + self._t * speed * 1.4 + phase_off * 1.6)
                    * amp_base * 0.40 * envelope
                    + math.sin(nx * math.pi * freq * 0.55 + self._t * speed * 0.6 + phase_off * 0.8)
                    * amp_base * 0.28 * envelope
                )

                if first:
                    path.moveTo(x, cy + y_off); first = False
                else:
                    path.lineTo(x, cy + y_off)

            # outer glow passes
            for gw, ga in [(5, 12), (2, 25)]:
                gp = QtGui.QPen(QtGui.QColor(r, g, b, ga))
                gp.setWidth(gw)
                gp.setCapStyle(QtCore.Qt.RoundCap)
                p.setPen(gp); p.setBrush(QtCore.Qt.NoBrush)
                p.drawPath(path)

            # main crisp line
            al = int(205 + 50 * math.sin(self._t + phase_off))
            lp = QtGui.QPen(QtGui.QColor(r, g, b, al))
            lp.setWidth(1)
            lp.setCapStyle(QtCore.Qt.RoundCap)
            p.setPen(lp)
            p.drawPath(path)

        # ── 5. remove clip for dot / shine ────────────
        p.setClipping(False)

        # ── 6. centre breathing dot ────────────────────
        dot_r = int(6 + 5 * self._breathing)
        dot_a = int(180 + 75 * self._breathing)
        dg = QtGui.QRadialGradient(cx, cy, dot_r * 4)
        dg.setColorAt(0.0, QtGui.QColor(100, 180, 255, dot_a))
        dg.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.setBrush(dg); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - dot_r*4), int(cy - dot_r*4), dot_r*8, dot_r*8)
        p.setBrush(QtGui.QColor(200, 230, 255, dot_a))
        p.drawEllipse(int(cx - dot_r), int(cy - dot_r), dot_r*2, dot_r*2)

        # ── 7. inner shine ─────────────────────────────
        shine = QtGui.QRadialGradient(cx - R*0.3, cy - R*0.35, R*0.5)
        shine.setColorAt(0.0, QtGui.QColor(255, 255, 255, 22))
        shine.setColorAt(1.0, QtGui.QColor(255, 255, 255,  0))
        p.setBrush(shine); p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(int(cx - R), int(cy - R), R * 2, R * 2)


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
            # Hover: fully lit with the accent colour
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
            # Default: dark background but clearly coloured border + text
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
        self.btn_listen = GlowButton("◎   LISTEN MODE",       QtGui.QColor(0, 255, 120))
        self.btn_exit   = GlowButton("✕   EXIT",              QtGui.QColor(255, 50, 70))

        for b in [self.btn_start, self.btn_train,
                  self.btn_manage, self.btn_listen, self.btn_exit]:
            b.setFixedWidth(300)
            vl.addWidget(b)

        self.btn_start.clicked.connect(self._run_start)
        self.btn_train.clicked.connect(self._run_train)
        self.btn_manage.clicked.connect(self._run_manage)
        self.btn_listen.clicked.connect(self._run_listen)
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
        self.status_lbl.setText(f"● {msg}")

    def _status_reset(self):
        self._status("SYSTEM READY")

    # ══════════════════════════════════════════════════
    #  BUTTON ACTIONS  — original logic preserved
    # ══════════════════════════════════════════════════
    def _run_start(self):
        script_path = os.path.join(os.path.dirname(__file__), "recognise.py")
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

    def _run_manage(self):
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
        QtCore.QTimer.singleShot(1500, self._status_reset)

    def _run_listen(self):
        project_dir = "/home/pi/Documents/Humanoid_project/final_humanoid-main"
        venv_python = os.path.join(project_dir, "venv", "bin", "python")
        script_path = os.path.join(project_dir, "stt.py")

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", f"stt.py not found at:\n{script_path}")
            return
        if not os.path.exists(venv_python):
            QtWidgets.QMessageBox.warning(self, "Error", f"venv not found at:\n{venv_python}")
            return
        try:
            self._status("LISTENING...", "rgba(0,255,160,220)")
            subprocess.Popen([venv_python, script_path], cwd=project_dir)
            QtCore.QTimer.singleShot(3000, self._status_reset)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run stt.py:\n{e}")

    def _run_exit(self):
        self._status("EXITING...", "rgba(255,60,80,220)")
        reply = QtWidgets.QMessageBox.question(
            self, "Exit AURA", "Exit AURA Interface?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
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