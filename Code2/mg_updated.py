try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets
import sys, os, time, math, random, subprocess

# ----------------------------- Worker for background tasks -----------------------------
class WorkerSignals(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal()
    message = QtCore.pyqtSignal(str)

class FakeLongTask(QtCore.QRunnable):
    def __init__(self, duration=5, message_prefix="Working"):
        super().__init__()
        self.duration = duration
        self.signals = WorkerSignals()
        self.message_prefix = message_prefix

    def run(self):
        steps = max(10, int(self.duration * 5))
        for i in range(steps + 1):
            pct = int(i * 100 / steps)
            self.signals.progress.emit(pct)
            if i % (max(1, steps // 5)) == 0:
                self.signals.message.emit(f"{self.message_prefix}... {pct}%")
            time.sleep(self.duration / steps)
        self.signals.message.emit(f"{self.message_prefix} complete.")
        self.signals.finished.emit()


# ----------------------------- Space Background -----------------------------
class SpaceBackground(QtWidgets.QWidget):
    def __init__(self, star_count=145, parent=None):
        super().__init__(parent)
        self.star_count = star_count
        self.stars = []
        for _ in range(star_count):
            x = random.randint(0, 1920)
            y = random.randint(0, 1080)
            base_brightness = random.randint(180, 255)
            phase = random.random() * math.pi * 2
            self.stars.append([x, y, base_brightness, phase])
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(100)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(0, 0, 0))
        grad = QtGui.QLinearGradient(self.width() * 0.5, 0, self.width(), self.height())
        grad.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QtGui.QColor(100, 0, 160, 40))
        p.fillRect(self.rect(), grad)
        for x, y, base_brightness, phase in self.stars:
            brightness = base_brightness + 50 * math.sin(time.time() * 0.8 + phase)
            brightness = max(100, min(255, int(brightness)))
            p.setPen(QtGui.QColor(brightness, brightness, brightness))
            p.drawPoint(x % self.width(), y % self.height())


# ----------------------------- Glow Button -----------------------------
class GlowButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(70)
        self.setMinimumWidth(300)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QtGui.QColor(170, 0, 255, 160))
        self.setGraphicsEffect(self.shadow)

        self._scale = 1.0
        self.anim_group = QtCore.QParallelAnimationGroup(self)
        self.blur_anim = QtCore.QPropertyAnimation(self.shadow, b"blurRadius")
        self.scale_anim = QtCore.QPropertyAnimation(self, b"_scale_prop")

        for anim in (self.blur_anim, self.scale_anim):
            anim.setDuration(220)
            anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim_group.addAnimation(self.blur_anim)
        self.anim_group.addAnimation(self.scale_anim)

        self.setStyleSheet(self.base_stylesheet())

    def get_scale(self):
        return self._scale

    def set_scale(self, v):
        self._scale = v
        self.setStyleSheet(self.base_stylesheet(scale=v))

    _scale_prop = QtCore.pyqtProperty(float, fget=get_scale, fset=set_scale)

    def enterEvent(self, e):
        self.blur_anim.setStartValue(self.shadow.blurRadius())
        self.blur_anim.setEndValue(36)
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
        base1 = "rgba(10, 40, 90, 220)"
        base2 = "rgba(25, 90, 160, 240)"
        hover1 = "rgba(20, 70, 140, 240)"
        hover2 = "rgba(70, 150, 255, 255)"
        border_normal = "rgba(30,150,255,0.35)"
        border_hover  = "rgba(80,200,255,0.70)"
        text_color = "rgb(235,245,255)"

        return f"""
        QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {base1},
            stop:1 {base2});
        border: 2px solid {border_normal};
        border-radius: 18px;
        padding: 10px 18px;
        color: {text_color};
        font-size: 24px;
        font-weight: 600;
        letter-spacing: 0.6px;
        text-align: center;
        transform: scale({scale});
        }}
        QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {hover1},
            stop:1 {hover2});
        border: 2px solid {border_hover};
        }}
        QPushButton:pressed {{
        transform: scale({max(0.98, scale - 0.02)});
        }}
        """


# ----------------------------- AURA Core -----------------------------
class AuraCore(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(420, 420)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._color = QtGui.QColor(100, 220, 255)
        self._opacity = 180
        self._scale = 1.0
        self.phase = 0.0
        self.speed = 0.04
        self.saturn_angle = 0.0

        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self.animate_pulse)
        self.anim_timer.start(30)

    def animate_pulse(self):
        self.phase += self.speed
        self._scale = 1.0 + 0.12 * math.sin(self.phase)
        self._opacity = 130 + 110 * (1 + math.sin(self.phase)) / 2
        self.saturn_angle = (self.saturn_angle + 0.8) % 360
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QtCore.Qt.transparent)

        orb_size = 320
        ox = (self.width() - orb_size) / 2
        oy = (self.height() - orb_size) / 2
        r = orb_size / 2
        cx = self.width() / 2
        cy = self.height() / 2

        p.save()
        p.translate(cx, cy)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        brightness_factor = 1.0 + ((self._scale - 1.0) * 2.5)
        brightness_factor = min(1.8, max(0.6, brightness_factor))

        glow_color = QtGui.QColor(
            min(int(self._color.red() * brightness_factor), 255),
            min(int(self._color.green() * brightness_factor), 255),
            min(int(self._color.blue() * brightness_factor), 255)
        )

        grad = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), r)
        c = QtGui.QColor(glow_color)
        c.setAlpha(int(self._opacity))
        grad.setColorAt(0.0, c)
        grad.setColorAt(0.5, QtGui.QColor(c.red(), c.green(), c.blue(), 180))
        grad.setColorAt(0.8, QtGui.QColor(c.red(), c.green(), c.blue(), 80))
        grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))

        p.setBrush(grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QRectF(ox, oy, orb_size, orb_size))
        p.restore()

    def pulse_react(self, color: QtGui.QColor):
        self._color = color
        anim = QtCore.QPropertyAnimation(self, b"geometry")
        anim.setDuration(600)
        start_rect = self.geometry()
        end_rect = QtCore.QRect(start_rect.x() - 25, start_rect.y() - 25,
                                start_rect.width() + 50, start_rect.height() + 50)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.finished.connect(lambda: self.reset_pulse(start_rect))
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def reset_pulse(self, rect):
        anim = QtCore.QPropertyAnimation(self, b"geometry")
        anim.setDuration(800)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        anim.setStartValue(self.geometry())
        anim.setEndValue(rect)
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)


# ----------------------------- Terminal Panel -----------------------------
class TerminalPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(420)

        vl = QtWidgets.QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)

        # Header label
        hdr = QtWidgets.QLabel("◈  LIVE OUTPUT")
        hdr.setStyleSheet("""
            color: rgba(0,200,255,160);
            font-family: 'Courier New';
            font-size: 13px;
            letter-spacing: 4px;
            font-weight: bold;
        """)
        vl.addWidget(hdr, alignment=QtCore.Qt.AlignCenter)

        # Text output area
        self.output = QtWidgets.QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFixedHeight(300)
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: rgba(2, 8, 25, 210);
                border: 1px solid rgba(0, 150, 255, 80);
                border-left: 3px solid rgba(0, 150, 255, 160);
                border-radius: 12px;
                color: rgba(0, 220, 255, 220);
                font-family: 'Courier New';
                font-size: 13px;
                padding: 10px;
            }
            QScrollBar:vertical {
                background: rgba(0,0,0,0);
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,160,255,100);
                border-radius: 3px;
            }
        """)
        vl.addWidget(self.output)

        # Stop button (hidden by default)
        self.btn_stop = QtWidgets.QPushButton("⏹  STOP LISTENING")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_stop.setVisible(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(120,0,40,220), stop:1 rgba(200,0,60,240));
                border: 2px solid rgba(255,80,80,0.5);
                border-radius: 12px;
                color: rgb(255,200,200);
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(180,0,60,240), stop:1 rgba(255,60,60,255));
            }
        """)
        vl.addWidget(self.btn_stop)

    def append(self, text, color="cyan"):
        colors = {
            "cyan":   "rgba(0,220,255,220)",
            "green":  "rgba(0,255,160,220)",
            "yellow": "rgba(255,220,0,220)",
            "red":    "rgba(255,80,80,220)",
            "white":  "rgba(200,220,255,180)",
        }
        c = colors.get(color, colors["cyan"])
        self.output.append(f'<span style="color:{c};">{text}</span>')
        sb = self.output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self):
        self.output.clear()


# ----------------------------- Main Window -----------------------------
class AuraMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA — Interface")
        self.resize(1024, 600)
        self._stt_process = None  # track stt.py process

        self.background = SpaceBackground()
        self.setCentralWidget(self.background)

        self.overlay = QtWidgets.QWidget(self.background)
        self.overlay.setGeometry(self.background.rect())
        self.overlay.raise_()

        layout = QtWidgets.QVBoxLayout(self.overlay)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        header = self.header_widget()
        layout.addWidget(header, alignment=QtCore.Qt.AlignHCenter)

        content = self.center_controls()
        layout.addWidget(content, alignment=QtCore.Qt.AlignHCenter)

        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 600;
            color: rgba(150,200,255,0.8);
            letter-spacing: 2px;
        """)
        layout.addWidget(self.status_label, alignment=QtCore.Qt.AlignHCenter)

        self.background.installEventFilter(self)
        self.threadpool = QtCore.QThreadPool()
        self.showMaximized()

    def eventFilter(self, s, e):
        if e.type() == QtCore.QEvent.Resize:
            self.overlay.setGeometry(self.background.rect())
        return super().eventFilter(s, e)

    # ----------------------------- HEADER -----------------------------
    def header_widget(self):
        w = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(w)

        from PyQt5.QtGui import QFontDatabase, QFont
        font_path = os.path.join(os.path.dirname(__file__), "Centauri", "Centauri.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        else:
            font_family = "Segoe UI"

        title = QtWidgets.QLabel("AURA")
        title.setFont(QFont(font_family, 110, QFont.Bold))
        title.setStyleSheet("""
            color: #1C6EDC;
            letter-spacing: 10px;
        """)
        title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        h.addWidget(title)
        h.addStretch()
        return w

    # ----------------------------- CENTER CONTROLS -----------------------------
    def center_controls(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setSpacing(40)
        layout.setContentsMargins(80, 0, 60, 40)

        # Orb
        self.aura_core = AuraCore()
        layout.addWidget(self.aura_core, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Buttons column
        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setSpacing(25)
        btn_col.setAlignment(QtCore.Qt.AlignVCenter)

        self.btn_start  = GlowButton("Start recognition")
        self.btn_train  = GlowButton("Train data")
        self.btn_manage = GlowButton("Manage dataset")
        self.btn_listen = GlowButton("Listen")

        for b in [self.btn_start, self.btn_train, self.btn_manage, self.btn_listen]:
            btn_col.addWidget(b)

        self.btn_start.clicked.connect(self.start_recognition)
        self.btn_train.clicked.connect(self.train_data)
        self.btn_manage.clicked.connect(self.manage_dataset)
        self.btn_listen.clicked.connect(self.run_queries)

        layout.addLayout(btn_col)

        # Terminal panel
        self.terminal = TerminalPanel()
        self.terminal.btn_stop.clicked.connect(self._stop_listen)
        layout.addWidget(self.terminal, alignment=QtCore.Qt.AlignVCenter)

        # Exit button floating bottom-right
        self.btn_exit = GlowButton("Exit")
        self.btn_exit.clicked.connect(self.exit_app)
        self.btn_exit.setFixedSize(120, 45)
        self.btn_exit.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(100,0,60,220), stop:1 rgba(200,0,100,255));
            border: 2px solid rgba(255,120,120,0.6);
            border-radius: 14px;
            color: rgb(255,230,230);
            font-size: 22px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(150,0,80,240), stop:1 rgba(255,80,80,255));
        }
        """)

        exit_container = QtWidgets.QWidget(self.overlay)
        exit_layout = QtWidgets.QHBoxLayout(exit_container)
        exit_layout.setContentsMargins(0, 0, 40, 40)
        exit_layout.addStretch()
        exit_layout.addWidget(self.btn_exit, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        exit_container.setLayout(exit_layout)
        exit_container.setGeometry(0, 0, self.overlay.width(), self.overlay.height())
        exit_container.raise_()

        def overlay_resize(event):
            exit_container.setGeometry(0, 0, self.overlay.width(), self.overlay.height())
        self.overlay.resizeEvent = overlay_resize

        return container

    # ----------------------------- BUTTON ACTIONS -----------------------------
    def start_recognition(self):
        script_path = os.path.join(os.path.dirname(__file__), "recognise.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "recognise.py not found."); return
        self.aura_core.pulse_react(QtGui.QColor(38, 103, 255))
        self.status_label.setText("Recognizing...")
        subprocess.Popen([sys.executable, script_path])
        QtCore.QTimer.singleShot(3000, lambda: self.status_label.clear())

    def train_data(self):
        script_path = os.path.join(os.path.dirname(__file__), "train.py")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", "train.py not found."); return
        person_name, ok = QtWidgets.QInputDialog.getText(self, "Enter Name", "Enter the person's name for training:")
        if ok and person_name.strip():
            name = person_name.strip()
            self.aura_core.pulse_react(QtGui.QColor(255, 220, 60))
            self.status_label.setText(f"Registering {name}...")
            self.training_process = QtCore.QProcess(self)
            self.training_process.finished.connect(lambda: self.training_done(name))
            self.training_process.start(sys.executable, [script_path, name])

    def training_done(self, name):
        self.aura_core.pulse_react(QtGui.QColor(80, 255, 120))
        self.status_label.setText(f"{name} Registration complete!")
        QtCore.QTimer.singleShot(3000, lambda: self.status_label.clear())

    def run_queries(self):
        """Launch stt.py and show live output in terminal panel."""
        project_dir = "/home/pi/Documents/Humanoid_project/final_humanoid-main"
        venv_python = os.path.join(project_dir, "venv", "bin", "python")
        script_path = os.path.join(project_dir, "stt.py")

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.warning(self, "Error", f"stt.py not found at:\n{script_path}"); return
        if not os.path.exists(venv_python):
            QtWidgets.QMessageBox.warning(self, "Error", f"venv not found at:\n{venv_python}"); return

        # Stop any existing process first
        if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
            self._stt_process.kill()

        self.terminal.clear()
        self.terminal.append("▶ Starting LISTEN MODE...", "green")
        self.terminal.btn_stop.setVisible(True)
        self.aura_core.pulse_react(QtGui.QColor(0, 255, 255))
        self.status_label.setText("Listening...")

        # Use QProcess to capture output in real time
        self._stt_process = QtCore.QProcess(self)
        self._stt_process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._stt_process.readyReadStandardOutput.connect(self._on_stt_output)
        self._stt_process.finished.connect(self._on_stt_finished)
        self._stt_process.setWorkingDirectory(project_dir)
        self._stt_process.start(venv_python, [script_path])

    def _on_stt_output(self):
        """Stream stt.py output into the terminal panel."""
        data = self._stt_process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "You said:" in line:
                self.terminal.append(line, "cyan")
            elif "AI:" in line:
                self.terminal.append(line, "green")
            elif "Listening" in line:
                self.terminal.append(line, "white")
            elif "Recording" in line:
                self.terminal.append(line, "yellow")
            elif "error" in line.lower():
                self.terminal.append(line, "red")
            else:
                self.terminal.append(line, "white")

    def _on_stt_finished(self):
        self.terminal.append("⏹ Listen mode stopped.", "red")
        self.terminal.btn_stop.setVisible(False)
        self.status_label.clear()

    def _stop_listen(self):
        if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
            self._stt_process.kill()
        self.terminal.append("⏹ Stopped by user.", "red")
        self.terminal.btn_stop.setVisible(False)
        self.status_label.clear()

    def manage_dataset(self):
        self.status_label.setText("Opening dataset folder...")
        self.aura_core.pulse_react(QtGui.QColor(180, 100, 255))
        data_path = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(data_path):
            os.makedirs(data_path, exist_ok=True)
        if sys.platform.startswith("win"):      os.startfile(data_path)
        elif sys.platform.startswith("darwin"): subprocess.Popen(["open", data_path])
        else:                                   subprocess.Popen(["xdg-open", data_path])
        QtCore.QTimer.singleShot(1500, lambda: self.status_label.clear())

    def exit_app(self):
        self.status_label.setText("Exiting...")
        self.aura_core.pulse_react(QtGui.QColor(255, 70, 70))
        if self._stt_process and self._stt_process.state() != QtCore.QProcess.NotRunning:
            self._stt_process.kill()
        reply = QtWidgets.QMessageBox.question(
            self, "Exit", "Exit AURA Interface?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            QtWidgets.QApplication.quit()
        else:
            self.status_label.clear()


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
