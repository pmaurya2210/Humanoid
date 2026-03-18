try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets
import sys, os, time, math, random, subprocess


# ----------------------------- Space Background -----------------------------
class SpaceBackground(QtWidgets.QWidget):
    def __init__(self, star_count=180, parent=None):
        super().__init__(parent)
        self.star_count = star_count
        self.stars = []
        for _ in range(star_count):
            x = random.randint(0, 1920)
            y = random.randint(0, 1080)
            base_brightness = random.randint(160, 255)
            phase = random.random() * math.pi * 2
            size = random.choice([1, 1, 1, 2])
            self.stars.append([x, y, base_brightness, phase, size])
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(80)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        # Deep space black background
        p.fillRect(self.rect(), QtGui.QColor(2, 4, 14))

        # Subtle nebula gradient top-right
        grad1 = QtGui.QRadialGradient(self.width() * 0.85, self.height() * 0.15, self.width() * 0.4)
        grad1.setColorAt(0.0, QtGui.QColor(10, 30, 80, 60))
        grad1.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), grad1)

        # Subtle nebula gradient bottom-left
        grad2 = QtGui.QRadialGradient(self.width() * 0.1, self.height() * 0.85, self.width() * 0.35)
        grad2.setColorAt(0.0, QtGui.QColor(0, 60, 80, 40))
        grad2.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), grad2)

        # Stars
        t = time.time()
        for x, y, base_brightness, phase, size in self.stars:
            brightness = base_brightness + 50 * math.sin(t * 0.6 + phase)
            brightness = max(100, min(255, int(brightness)))
            color = QtGui.QColor(brightness, brightness, min(255, brightness + 20))
            p.setPen(color)
            if size == 1:
                p.drawPoint(x % self.width(), y % self.height())
            else:
                p.setBrush(color)
                p.setPen(QtCore.Qt.NoPen)
                p.drawEllipse(x % self.width(), y % self.height(), size, size)
                p.setPen(color)


# ----------------------------- Glow Button -----------------------------
class GlowButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(58)
        self.setMinimumWidth(260)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QtGui.QColor(0, 180, 255, 180))
        self.setGraphicsEffect(self.shadow)

        self._scale = 1.0
        self.anim_group = QtCore.QParallelAnimationGroup(self)
        self.blur_anim = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        self.scale_anim = QtCore.QPropertyAnimation(self, b"_scale_prop")

        for anim in (self.blur_anim, self.scale_anim):
            anim.setDuration(200)
            anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim_group.addAnimation(self.blur_anim)
        self.anim_group.addAnimation(self.scale_anim)
        self.setStyleSheet(self.base_stylesheet())

    def get_scale(self): return self._scale
    def set_scale(self, v):
        self._scale = v
        self.setStyleSheet(self.base_stylesheet(scale=v))
    _scale_prop = QtCore.pyqtProperty(float, fget=get_scale, fset=set_scale)

    def enterEvent(self, e):
        self.blur_anim.setStartValue(self.shadow.blurRadius())
        self.blur_anim.setEndValue(32)
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(1.03)
        self.anim_group.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.blur_anim.setStartValue(self.shadow.blurRadius())
        self.blur_anim.setEndValue(0)
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(1.0)
        self.anim_group.start()
        super().leaveEvent(e)

    def base_stylesheet(self, scale=1.0):
        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(5, 25, 60, 210),
                stop:1 rgba(0, 80, 140, 230));
            border: 1px solid rgba(0, 160, 255, 0.45);
            border-radius: 14px;
            padding: 8px 20px;
            color: rgba(180, 230, 255, 0.95);
            font-size: 18px;
            font-weight: 500;
            letter-spacing: 1.5px;
            text-align: left;
            padding-left: 22px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0, 60, 130, 240),
                stop:1 rgba(0, 140, 220, 255));
            border: 1px solid rgba(0, 210, 255, 0.80);
            color: rgb(220, 245, 255);
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0, 40, 100, 255),
                stop:1 rgba(0, 100, 180, 255));
        }}
        """


# ----------------------------- AURA Core Orb -----------------------------
class AuraCore(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(340, 340)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._color = QtGui.QColor(0, 180, 255)
        self._opacity = 180
        self._scale = 1.0
        self.phase = 0.0
        self.speed = 0.035
        self.ring_angle = 0.0

        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self.animate_pulse)
        self.anim_timer.start(28)

    def animate_pulse(self):
        self.phase += self.speed
        self._scale = 1.0 + 0.10 * math.sin(self.phase)
        self._opacity = 120 + 100 * (1 + math.sin(self.phase)) / 2
        self.ring_angle = (self.ring_angle + 0.5) % 360
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtCore.Qt.transparent)

        orb_size = 260
        cx = self.width() / 2
        cy = self.height() / 2
        ox = cx - orb_size / 2
        oy = cy - orb_size / 2
        r = orb_size / 2

        # Outer glow ring
        p.save()
        p.translate(cx, cy)
        p.rotate(self.ring_angle)
        pen = QtGui.QPen(QtGui.QColor(0, 200, 255, 40))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawEllipse(QtCore.QRectF(-r - 28, -r - 28, (r + 28) * 2, (r + 28) * 2))
        pen2 = QtGui.QPen(QtGui.QColor(0, 140, 255, 25))
        pen2.setWidth(1)
        p.setPen(pen2)
        p.drawEllipse(QtCore.QRectF(-r - 44, -r - 44, (r + 44) * 2, (r + 44) * 2))
        p.restore()

        # Main orb
        p.save()
        p.translate(cx, cy)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        bf = 1.0 + (self._scale - 1.0) * 2.5
        bf = min(1.8, max(0.6, bf))
        gc = QtGui.QColor(
            min(int(self._color.red() * bf), 255),
            min(int(self._color.green() * bf), 255),
            min(int(self._color.blue() * bf), 255)
        )

        # Core radial gradient
        grad = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), r)
        c = QtGui.QColor(gc)
        c.setAlpha(int(self._opacity))
        grad.setColorAt(0.0, QtGui.QColor(200, 240, 255, int(self._opacity * 0.9)))
        grad.setColorAt(0.25, c)
        grad.setColorAt(0.6, QtGui.QColor(c.red(), c.green(), c.blue(), 120))
        grad.setColorAt(0.85, QtGui.QColor(c.red(), c.green(), c.blue(), 40))
        grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))

        p.setBrush(grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QRectF(ox, oy, orb_size, orb_size))
        p.restore()

        # Inner shine
        shine_grad = QtGui.QRadialGradient(QtCore.QPointF(cx - r * 0.28, cy - r * 0.28), r * 0.45)
        shine_grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 70))
        shine_grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        p.setBrush(shine_grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QRectF(ox, oy, orb_size, orb_size))

    def pulse_react(self, color: QtGui.QColor):
        self._color = color
        anim = QtCore.QPropertyAnimation(self, b"geometry")
        anim.setDuration(500)
        sr = self.geometry()
        er = QtCore.QRect(sr.x() - 20, sr.y() - 20, sr.width() + 40, sr.height() + 40)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.setStartValue(sr)
        anim.setEndValue(er)
        anim.finished.connect(lambda: self.reset_pulse(sr))
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def reset_pulse(self, rect):
        anim = QtCore.QPropertyAnimation(self, b"geometry")
        anim.setDuration(700)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        anim.setStartValue(self.geometry())
        anim.setEndValue(rect)
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)


# ----------------------------- Kotharis Banner -----------------------------
class KothariBanner(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # Banner background — dark glass panel
        bg_grad = QtGui.QLinearGradient(0, 0, self.width(), 0)
        bg_grad.setColorAt(0.0, QtGui.QColor(0, 10, 35, 230))
        bg_grad.setColorAt(0.5, QtGui.QColor(0, 25, 65, 245))
        bg_grad.setColorAt(1.0, QtGui.QColor(0, 10, 35, 230))
        p.setBrush(bg_grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(0, 0, self.width(), self.height())

        # Top border glow line
        line_grad = QtGui.QLinearGradient(0, 0, self.width(), 0)
        line_grad.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        line_grad.setColorAt(0.2, QtGui.QColor(0, 180, 255, 200))
        line_grad.setColorAt(0.5, QtGui.QColor(100, 220, 255, 255))
        line_grad.setColorAt(0.8, QtGui.QColor(0, 180, 255, 200))
        line_grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.setBrush(line_grad)
        p.drawRect(0, 0, self.width(), 2)

        # Bottom border glow line
        p.setBrush(line_grad)
        p.drawRect(0, self.height() - 2, self.width(), 2)

        # School name text
        font = QtGui.QFont("Courier New", 28, QtGui.QFont.Bold)
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 10)
        p.setFont(font)

        # Glow shadow layers
        for offset, alpha in [(4, 30), (2, 60), (1, 100)]:
            p.setPen(QtGui.QColor(0, 180, 255, alpha))
            p.drawText(QtCore.QRect(offset, offset, self.width(), self.height()),
                       QtCore.Qt.AlignCenter, "KOTHARIS")

        # Main text
        p.setPen(QtGui.QColor(180, 235, 255, 255))
        p.drawText(self.rect(), QtCore.Qt.AlignCenter, "KOTHARIS")

        # Decorative side lines
        side_pen = QtGui.QPen(QtGui.QColor(0, 160, 255, 80))
        side_pen.setWidth(1)
        p.setPen(side_pen)
        margin = 60
        mid_y = self.height() // 2
        p.drawLine(margin, mid_y, self.width() // 2 - 160, mid_y)
        p.drawLine(self.width() // 2 + 160, mid_y, self.width() - margin, mid_y)

        # Diamond decorators
        p.setBrush(QtGui.QColor(0, 200, 255, 160))
        p.setPen(QtCore.Qt.NoPen)
        for dx in [margin - 5, self.width() - margin + 5]:
            diamond = QtGui.QPolygon([
                QtCore.QPoint(dx, mid_y - 5),
                QtCore.QPoint(dx + 5, mid_y),
                QtCore.QPoint(dx, mid_y + 5),
                QtCore.QPoint(dx - 5, mid_y),
            ])
            p.drawPolygon(diamond)


# ----------------------------- Main Window -----------------------------
class AuraMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA — Kotharis")
        self.resize(1280, 720)

        self.background = SpaceBackground()
        self.setCentralWidget(self.background)

        self.overlay = QtWidgets.QWidget(self.background)
        self.overlay.setGeometry(self.background.rect())
        self.overlay.raise_()
        self.overlay.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        main_layout = QtWidgets.QVBoxLayout(self.overlay)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── TOP: Kotharis banner ──
        self.banner = KothariBanner()
        main_layout.addWidget(self.banner)

        # ── MIDDLE: AURA title + orb + buttons ──
        center_widget = QtWidgets.QWidget()
        center_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        center_layout = QtWidgets.QVBoxLayout(center_widget)
        center_layout.setContentsMargins(40, 20, 40, 10)
        center_layout.setSpacing(10)

        # AURA title
        title_label = QtWidgets.QLabel("AURA")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_font = QtGui.QFont("Courier New", 72, QtGui.QFont.Bold)
        title_font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 18)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            color: rgba(100, 200, 255, 220);
            text-shadow: 0 0 30px rgba(0,180,255,0.9), 0 0 80px rgba(0,140,255,0.5);
        """)
        center_layout.addWidget(title_label)

        # Subtitle
        sub_label = QtWidgets.QLabel("A U T O M A T E D   U N I V E R S A L   R E C O G N I T I O N   A I")
        sub_label.setAlignment(QtCore.Qt.AlignCenter)
        sub_label.setStyleSheet("""
            color: rgba(0, 160, 220, 160);
            font-size: 11px;
            letter-spacing: 3px;
            font-family: 'Courier New';
        """)
        center_layout.addWidget(sub_label)

        # Orb + Buttons row
        row_widget = QtWidgets.QWidget()
        row_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        row_layout = QtWidgets.QHBoxLayout(row_widget)
        row_layout.setContentsMargins(60, 10, 60, 10)
        row_layout.setSpacing(0)

        # Orb on left
        self.aura_core = AuraCore()
        row_layout.addWidget(self.aura_core, alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        row_layout.addStretch()

        # Buttons on right
        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setSpacing(14)
        btn_col.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.btn_start  = GlowButton("▶   Start Recognition")
        self.btn_train  = GlowButton("⬡   Train Data")
        self.btn_manage = GlowButton("◈   Manage Dataset")
        self.btn_listen = GlowButton("◎   Listen")

        for b in [self.btn_start, self.btn_train, self.btn_manage, self.btn_listen]:
            b.setFixedWidth(310)
            btn_col.addWidget(b)

        row_layout.addLayout(btn_col)
        center_layout.addWidget(row_widget)
        main_layout.addWidget(center_widget, stretch=1)

        # ── BOTTOM: status bar ──
        bottom = QtWidgets.QWidget()
        bottom.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        bottom.setFixedHeight(55)
        bottom_layout = QtWidgets.QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(30, 0, 30, 8)

        self.status_label = QtWidgets.QLabel("SYSTEM READY")
        self.status_label.setStyleSheet("""
            color: rgba(0, 200, 255, 180);
            font-size: 13px;
            font-family: 'Courier New';
            letter-spacing: 3px;
        """)
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()

        # Exit button bottom-right
        self.btn_exit = QtWidgets.QPushButton("✕  EXIT")
        self.btn_exit.setFixedSize(110, 36)
        self.btn_exit.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(80,0,30,220), stop:1 rgba(180,0,60,240));
                border: 1px solid rgba(255,80,100,0.5);
                border-radius: 10px;
                color: rgba(255,200,210,230);
                font-size: 13px;
                font-family: 'Courier New';
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(140,0,50,240), stop:1 rgba(255,50,80,255));
                border: 1px solid rgba(255,120,140,0.8);
            }
        """)
        bottom_layout.addWidget(self.btn_exit)
        main_layout.addWidget(bottom)

        # Connections
        self.btn_start.clicked.connect(self.start_recognition)
        self.btn_train.clicked.connect(self.train_data)
        self.btn_manage.clicked.connect(self.manage_dataset)
        self.btn_listen.clicked.connect(self.run_queries)
        self.btn_exit.clicked.connect(self.exit_app)

        self.background.installEventFilter(self)
        self.threadpool = QtCore.QThreadPool()
        self.showMaximized()

    def eventFilter(self, s, e):
        if e.type() == QtCore.QEvent.Resize:
            self.overlay.setGeometry(self.background.rect())
            self.banner.setFixedWidth(self.background.width())
        return super().eventFilter(s, e)

    def set_status(self, msg, color="rgba(0,200,255,180)"):
        self.status_label.setStyleSheet(f"""
            color: {color};
            font-size: 13px;
            font-family: 'Courier New';
            letter-spacing: 3px;
        """)
        self.status_label.setText(msg)

    # ── Button Actions (same logic as original) ──

    def start_recognition(self):
        script_path = os.path.join(os.path.dirname(__file__), "recognise.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "recognise.py not found.")
            return
        try:
            self.aura_core.pulse_react(QtGui.QColor(38, 103, 255))
            self.set_status("● RECOGNIZING...", "rgba(80,160,255,200)")
            subprocess.Popen([sys.executable, script_path])
            QtCore.QTimer.singleShot(3000, lambda: self.set_status("SYSTEM READY"))
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run recognise.py:\n{ex}")

    def train_data(self):
        script_path = os.path.join(os.path.dirname(__file__), "train.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "train.py not found.")
            return
        person_name, ok = QtWidgets.QInputDialog.getText(self, "Enter Name", "Enter the person's name for training:")
        if ok and person_name.strip():
            name = person_name.strip()
            self.aura_core.pulse_react(QtGui.QColor(255, 200, 40))
            self.set_status(f"● TRAINING — {name.upper()}...", "rgba(255,200,60,200)")
            self.training_process = QtCore.QProcess(self)
            self.training_process.finished.connect(lambda: self.training_done(name))
            self.training_process.start(sys.executable, [script_path, name])

    def training_done(self, name):
        self.aura_core.pulse_react(QtGui.QColor(60, 255, 120))
        self.set_status(f"✓ {name.upper()} REGISTERED", "rgba(60,255,120,200)")
        QtCore.QTimer.singleShot(3000, lambda: self.set_status("SYSTEM READY"))

    def run_queries(self):
        script_path = os.path.join(os.path.dirname(__file__), "stt.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "stt.py not found.")
            return
        try:
            self.aura_core.pulse_react(QtGui.QColor(0, 255, 220))
            self.set_status("● LISTENING...", "rgba(0,255,200,200)")
            subprocess.Popen([sys.executable, script_path])
            QtCore.QTimer.singleShot(3000, lambda: self.set_status("SYSTEM READY"))
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to run stt.py:\n{ex}")

    def manage_dataset(self):
        self.set_status("● OPENING DATASET...", "rgba(180,100,255,200)")
        self.aura_core.pulse_react(QtGui.QColor(160, 80, 255))
        data_path = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_path, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(data_path)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", data_path])
        else:
            subprocess.Popen(["xdg-open", data_path])
        QtCore.QTimer.singleShot(1500, lambda: self.set_status("SYSTEM READY"))

    def exit_app(self):
        self.aura_core.pulse_react(QtGui.QColor(255, 60, 60))
        reply = QtWidgets.QMessageBox.question(
            self, "Exit", "Exit AURA Interface?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            QtWidgets.QApplication.quit()
        else:
            self.set_status("SYSTEM READY")


# ----------------------------- Entrypoint -----------------------------
def main():
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    w = AuraMain()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()