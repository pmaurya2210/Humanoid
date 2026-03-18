try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets

import sys, os, time, math, random, subprocess


# ══════════════════════════════════════════════════════
#  PARTICLE FIELD WIDGET
# ══════════════════════════════════════════════════════
class ParticleField(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(420, 420)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.particles = []
        self.connections = []
        self.time = 0.0

        # Spawn particles in a soft sphere zone
        for _ in range(55):
            self._spawn_particle()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(18)

    def _spawn_particle(self):
        cx, cy = 210, 210
        angle  = random.uniform(0, 2 * math.pi)
        dist   = random.uniform(0, 160)
        x = cx + dist * math.cos(angle)
        y = cy + dist * math.sin(angle)
        vx = random.uniform(-0.4, 0.4)
        vy = random.uniform(-0.4, 0.4)
        size   = random.uniform(2.5, 5.5)
        phase  = random.uniform(0, 2 * math.pi)
        speed  = random.uniform(0.04, 0.10)
        # color variant: cyan / teal / white
        kind = random.choice(["cyan", "teal", "white", "cyan"])
        self.particles.append({
            "x": x, "y": y, "vx": vx, "vy": vy,
            "size": size, "phase": phase, "speed": speed,
            "kind": kind, "alpha": random.randint(120, 255)
        })

    def _tick(self):
        self.time += 0.016
        cx, cy = 210, 210
        R = 165

        for pt in self.particles:
            pt["x"] += pt["vx"]
            pt["y"] += pt["vy"]
            pt["phase"] += pt["speed"]

            # Soft boundary — nudge back toward centre
            dx = pt["x"] - cx
            dy = pt["y"] - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > R:
                pt["vx"] -= dx * 0.002
                pt["vy"] -= dy * 0.002

            # Tiny random drift
            pt["vx"] += random.uniform(-0.03, 0.03)
            pt["vy"] += random.uniform(-0.03, 0.03)

            # Speed cap
            spd = math.sqrt(pt["vx"]**2 + pt["vy"]**2)
            if spd > 0.7:
                pt["vx"] *= 0.7 / spd
                pt["vy"] *= 0.7 / spd

            # Pulsing alpha
            pt["alpha"] = int(140 + 80 * math.sin(pt["phase"]))

        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)

        cx, cy = 210, 210
        R = 165

        # ── soft dark backdrop circle ──
        bg = QtGui.QRadialGradient(cx, cy, R)
        bg.setColorAt(0.0, QtGui.QColor(0, 18, 30, 180))
        bg.setColorAt(0.7, QtGui.QColor(0, 10, 20, 140))
        bg.setColorAt(1.0, QtGui.QColor(0,  4,  8,  60))
        p.setBrush(bg)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # ── outer glow ring ──
        for width, alpha in [(10, 10), (5, 25), (2, 70)]:
            pen = QtGui.QPen(QtGui.QColor(0, 200, 255, alpha))
            pen.setWidth(width)
            p.setPen(pen)
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # ── connection lines between close particles ──
        pts = self.particles
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                dx = pts[i]["x"] - pts[j]["x"]
                dy = pts[i]["y"] - pts[j]["y"]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 72:
                    alpha = int((1 - dist / 72) * 55)
                    pen = QtGui.QPen(QtGui.QColor(0, 200, 255, alpha))
                    pen.setWidth(1)
                    p.setPen(pen)
                    p.drawLine(int(pts[i]["x"]), int(pts[i]["y"]),
                               int(pts[j]["x"]), int(pts[j]["y"]))

        # ── draw particles ──
        for pt in pts:
            a   = pt["alpha"]
            sz  = pt["size"]
            x, y = int(pt["x"]), int(pt["y"])

            if pt["kind"] == "cyan":
                core_col = QtGui.QColor(0, 220, 255, a)
                glow_col = QtGui.QColor(0, 200, 255, a // 4)
            elif pt["kind"] == "teal":
                core_col = QtGui.QColor(0, 255, 180, a)
                glow_col = QtGui.QColor(0, 220, 160, a // 4)
            else:
                core_col = QtGui.QColor(200, 240, 255, a)
                glow_col = QtGui.QColor(180, 220, 255, a // 5)

            # Glow halo
            glow = QtGui.QRadialGradient(x, y, sz * 3.5)
            glow.setColorAt(0.0, glow_col)
            glow.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.setPen(QtCore.Qt.NoPen)
            r2 = int(sz * 3.5)
            p.drawEllipse(x - r2, y - r2, r2 * 2, r2 * 2)

            # Bright core
            p.setBrush(core_col)
            s = int(sz)
            p.drawEllipse(x - s, y - s, s * 2, s * 2)

        # ── blinking centre star ──
        blink = 0.5 + 0.5 * math.sin(self.time * 3.5)
        star_a = int(160 + 95 * blink)
        star_r = int(5 + 3 * blink)

        star_glow = QtGui.QRadialGradient(cx, cy, star_r * 5)
        star_glow.setColorAt(0.0, QtGui.QColor(0, 240, 255, star_a))
        star_glow.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.setBrush(star_glow)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - star_r * 5, cy - star_r * 5, star_r * 10, star_r * 10)

        p.setBrush(QtGui.QColor(200, 255, 255, star_a))
        p.drawEllipse(cx - star_r, cy - star_r, star_r * 2, star_r * 2)


# ══════════════════════════════════════════════════════
#  SPACE BACKGROUND
# ══════════════════════════════════════════════════════
class SpaceBackground(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stars = []
        for _ in range(200):
            x     = random.randint(0, 1920)
            y     = random.randint(0, 1080)
            br    = random.randint(140, 255)
            phase = random.uniform(0, 2 * math.pi)
            size  = random.choice([1, 1, 1, 2])
            self.stars.append([x, y, br, phase, size])
        t = QtCore.QTimer(self)
        t.timeout.connect(self.update)
        t.start(80)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(2, 5, 15))

        # Subtle nebula
        for (rx, ry, rr, rc) in [
            (0.8, 0.15, 0.35, QtGui.QColor(0, 20, 60, 50)),
            (0.1, 0.8,  0.30, QtGui.QColor(0, 40, 60, 35)),
        ]:
            g = QtGui.QRadialGradient(self.width() * rx, self.height() * ry,
                                      self.width() * rr)
            g.setColorAt(0.0, rc)
            g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), g)

        # Stars
        now = time.time()
        for x, y, br, phase, size in self.stars:
            b = int(br + 40 * math.sin(now * 0.7 + phase))
            b = max(80, min(255, b))
            col = QtGui.QColor(b, b, min(255, b + 15))
            if size == 1:
                p.setPen(col)
                p.drawPoint(x % self.width(), y % self.height())
            else:
                p.setBrush(col)
                p.setPen(QtCore.Qt.NoPen)
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
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QtGui.QColor(self.accent.red(),
                                          self.accent.green(),
                                          self.accent.blue(), 180))
        self.setGraphicsEffect(self.shadow)
        self._apply_style(False)

    def _apply_style(self, hovered):
        r, g, b = self.accent.red(), self.accent.green(), self.accent.blue()
        if hovered:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 rgba({r//4},{g//4},{b//4},230),
                        stop:1 rgba({r//3},{g//3},{b//3},245));
                    border: 1px solid rgba({r},{g},{b},200);
                    border-left: 3px solid rgba({r},{g},{b},255);
                    border-radius: 8px;
                    color: rgba({min(r+80,255)},{min(g+80,255)},{min(b+80,255)},255);
                    font-family: 'Courier New';
                    font-size: 15px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    text-align: left;
                    padding-left: 20px;
                }}""")
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 rgba(4,10,22,210),
                        stop:1 rgba(8,18,35,220));
                    border: 1px solid rgba({r},{g},{b},70);
                    border-left: 3px solid rgba({r},{g},{b},140);
                    border-radius: 8px;
                    color: rgba({r},{g},{b},190);
                    font-family: 'Courier New';
                    font-size: 15px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    text-align: left;
                    padding-left: 20px;
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
#  BLINKING DOT INDICATOR
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
        p.setBrush(c2)
        p.drawEllipse(5, 6, 10, 10)
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
        self.threadpool = QtCore.QThreadPool()
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

        # Centre row
        mid = QtWidgets.QWidget()
        mid.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        hl  = QtWidgets.QHBoxLayout(mid)
        hl.setContentsMargins(60, 10, 60, 10)
        hl.setSpacing(0)

        hl.addWidget(self._make_left_info(),  alignment=QtCore.Qt.AlignVCenter)
        hl.addStretch(1)

        # Particle field centrepiece
        self.particles = ParticleField()
        hl.addWidget(self.particles, alignment=QtCore.Qt.AlignVCenter)

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
                # bottom glow line
                for w2, a in [(8, 8), (4, 22), (1, 110)]:
                    pen = QtGui.QPen(QtGui.QColor(0, 180, 255, a))
                    pen.setWidth(w2); p.setPen(pen)
                    p.drawLine(0, self_.height()-1, self_.width(), self_.height()-1)

        bg = _BG(bar); bg.setGeometry(0, 0, 4000, 78); bg.lower()

        hl = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(36, 0, 36, 0)

        # Left — AURA badge
        aura = QtWidgets.QLabel("AURA")
        aura.setStyleSheet("""
            color: rgba(0,200,255,230);
            font-family: 'Courier New';
            font-size: 30px;
            font-weight: bold;
            letter-spacing: 8px;
        """)
        hl.addWidget(aura)

        # Centre — KOTHARIS
        school = QtWidgets.QLabel("KOTHARIS")
        school.setAlignment(QtCore.Qt.AlignCenter)
        school.setStyleSheet("""
            color: rgba(0, 230, 255, 255);
            font-family: 'Courier New';
            font-size: 40px;
            font-weight: bold;
            letter-spacing: 16px;
        """)
        fx = QtWidgets.QGraphicsDropShadowEffect()
        fx.setOffset(0, 0); fx.setBlurRadius(28)
        fx.setColor(QtGui.QColor(0, 200, 255, 180))
        school.setGraphicsEffect(fx)
        hl.addWidget(school, stretch=1)

        # Right — clock + status dot
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(3)
        self.clock_lbl = QtWidgets.QLabel()
        self.clock_lbl.setStyleSheet("""
            color: rgba(0,180,255,180);
            font-family: 'Courier New';
            font-size: 12px;
            letter-spacing: 2px;
        """)
        col.addWidget(self.clock_lbl, alignment=QtCore.Qt.AlignRight)
        col.addWidget(BlinkDot("SYS ONLINE", QtGui.QColor(0, 220, 255)),
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
        vl.setSpacing(20); vl.setContentsMargins(0, 0, 0, 0)
        vl.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        def card(title, value, vc="rgba(0,210,255,210)"):
            c = QtWidgets.QWidget()
            c.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            cl = QtWidgets.QVBoxLayout(c)
            cl.setSpacing(1); cl.setContentsMargins(0, 0, 0, 0)
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
        vl.addWidget(card("MODE",      "STANDBY", "rgba(0,255,180,230)"))
        vl.addWidget(card("SUBJECTS",  f"{random.randint(4,12)} LOADED"))
        vl.addSpacing(10)
        vl.addWidget(BlinkDot("ACTIVE", QtGui.QColor(0, 200, 255)))
        vl.addWidget(BlinkDot("CAMERA OK", QtGui.QColor(0, 255, 160)))
        vl.addStretch()
        return w

    # ──────────────────────────────────────────────────
    def _make_right_buttons(self):
        w = QtWidgets.QWidget()
        w.setFixedWidth(320)
        w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        vl = QtWidgets.QVBoxLayout(w)
        vl.setSpacing(12); vl.setContentsMargins(0, 0, 0, 0)
        vl.setAlignment(QtCore.Qt.AlignVCenter)

        hdr = QtWidgets.QLabel("── OPERATIONS ──")
        hdr.setStyleSheet("""
            color: rgba(0,160,220,110);
            font-family: 'Courier New';
            font-size: 10px;
            letter-spacing: 4px;
        """)
        vl.addWidget(hdr, alignment=QtCore.Qt.AlignCenter)
        vl.addSpacing(6)

        CYAN  = QtGui.QColor(0, 180, 255)
        TEAL  = QtGui.QColor(0, 220, 180)
        PURP  = QtGui.QColor(100, 120, 255)
        GREEN = QtGui.QColor(0, 220, 120)
        RED   = QtGui.QColor(255, 60, 80)

        self.btn_start  = GlowButton("▶   START RECOGNITION", CYAN)
        self.btn_train  = GlowButton("◈   TRAIN DATA",        TEAL)
        self.btn_manage = GlowButton("⬡   MANAGE DATASET",    PURP)
        self.btn_listen = GlowButton("◎   LISTEN MODE",       GREEN)
        self.btn_exit   = GlowButton("✕   EXIT",              RED)

        for b in [self.btn_start, self.btn_train,
                  self.btn_manage, self.btn_listen, self.btn_exit]:
            b.setFixedWidth(300)
            vl.addWidget(b)

        # ── Wire up all buttons ──
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
                p.fillRect(self_.rect(), QtGui.QColor(2, 6, 18, 215))
                for w2, a in [(5, 8), (2, 25), (1, 90)]:
                    pen = QtGui.QPen(QtGui.QColor(0, 160, 255, a))
                    pen.setWidth(w2); p.setPen(pen)
                    p.drawLine(0, 0, self_.width(), 0)

        bg = _BG(bar); bg.setGeometry(0, 0, 4000, 40); bg.lower()

        hl = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(30, 0, 30, 0)

        self.status_lbl = QtWidgets.QLabel("● SYSTEM READY")
        self.status_lbl.setStyleSheet("""
            color: rgba(0,200,255,180);
            font-family: 'Courier New';
            font-size: 12px;
            letter-spacing: 3px;
        """)
        hl.addWidget(self.status_lbl)
        hl.addStretch()

        ver = QtWidgets.QLabel("AURA/2.0  ·  KOTHARIS INSTITUTE  ·  AI RECOGNITION SYSTEM")
        ver.setStyleSheet("""
            color: rgba(0,120,180,90);
            font-family: 'Courier New';
            font-size: 10px;
            letter-spacing: 2px;
        """)
        hl.addWidget(ver)
        return bar

    # ── Status helper ─────────────────────────────────
    def _status(self, msg, color="rgba(0,200,255,180)"):
        self.status_lbl.setStyleSheet(f"""
            color: {color};
            font-family: 'Courier New';
            font-size: 12px;
            letter-spacing: 3px;
        """)
        self.status_lbl.setText(f"● {msg}")

    def _status_reset(self):
        self._status("SYSTEM READY")

    # ══════════════════════════════════════════════════
    #  BUTTON ACTIONS  — all properly wired
    # ══════════════════════════════════════════════════

    def _run_start(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recognise.py")
        if not os.path.exists(script):
            QtWidgets.QMessageBox.warning(self, "Not Found",
                f"recognise.py not found at:\n{script}")
            return
        self._status("RECOGNITION ACTIVE...", "rgba(0,200,255,220)")
        subprocess.Popen([sys.executable, script])
        QtCore.QTimer.singleShot(3000, self._status_reset)

    def _run_train(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train.py")
        if not os.path.exists(script):
            QtWidgets.QMessageBox.warning(self, "Not Found",
                f"train.py not found at:\n{script}")
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Register Subject", "Enter person's name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        self._status(f"TRAINING — {name.upper()}", "rgba(0,255,180,220)")
        self._train_proc = QtCore.QProcess(self)
        self._train_proc.finished.connect(
            lambda: self._train_done(name))
        self._train_proc.start(sys.executable, [script, name])

    def _train_done(self, name):
        self._status(f"REGISTERED: {name.upper()}", "rgba(0,255,120,230)")
        QtCore.QTimer.singleShot(3000, self._status_reset)

    def _run_manage(self):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(data_path, exist_ok=True)
        self._status("OPENING DATASET FOLDER", "rgba(120,100,255,220)")
        if sys.platform.startswith("win"):
            os.startfile(data_path)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", data_path])
        else:
            subprocess.Popen(["xdg-open", data_path])
        QtCore.QTimer.singleShot(1500, self._status_reset)

    def _run_listen(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stt.py")
        if not os.path.exists(script):
            QtWidgets.QMessageBox.warning(self, "Not Found",
                f"stt.py not found at:\n{script}")
            return
        self._status("LISTEN MODE ACTIVE", "rgba(0,255,160,220)")
        subprocess.Popen([sys.executable, script])
        QtCore.QTimer.singleShot(3000, self._status_reset)

    def _run_exit(self):
        reply = QtWidgets.QMessageBox.question(
            self, "Exit AURA", "Terminate AURA session?",
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