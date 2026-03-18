import sys
import os
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QScrollArea, QFrame, QSpacerItem, QSizePolicy, QGraphicsOpacityEffect,
    QMessageBox, QInputDialog, QGridLayout
)
from PyQt5.QtGui import QPixmap, QFontDatabase
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QCoreApplication
import os
import threading
from queries import listen, get_answer, speak

os.environ["QT_QPA_PLATFORM"] = "xcb"



class ClosableWidget(QFrame):
    def __init__(self, title="Interactive Box", parent=None):
        super().__init__(parent)
        self.setObjectName("ClosableWidget")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setFixedHeight(0)
        self.hide()

        # Animations
        self.animation = QPropertyAnimation(self, b"minimumHeight")
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(400)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("ClosableWidgetTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(QSize(40, 40))
        self.close_button.setObjectName("CloseBoxButton")
        self.close_button.clicked.connect(self.close_box)
        header_layout.addWidget(self.close_button)
        self.main_layout.addLayout(header_layout)

        # Scrollable content area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("ClosableWidgetScrollArea")
        self.scroll_area.setMinimumHeight(200)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

    def close_box(self):
        self.animation.setStartValue(self.height())
        self.animation.setEndValue(0)
        self.animation.start()
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.start()
        QTimer.singleShot(400, self.hide)

    def show_box(self, desired_height=300):
        self.show()
        self.animation.setStartValue(0)
        self.animation.setEndValue(desired_height)
        self.animation.start()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

    def set_content_widget(self, widget):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.addWidget(widget)

    def set_title(self, title):
        self.title_label.setText(title)


class TextInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(0, 10, 0, 10)

        instruction_label = QLabel("Enter your command or question for AURA:")
        instruction_label.setObjectName("TextInputInstruction")
        self.main_layout.addWidget(instruction_label)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("e.g., ")
        self.text_input.setObjectName("TextInputArea")
        self.text_input.setFixedHeight(100)
        self.main_layout.addWidget(self.text_input)

        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.send_button = QPushButton("Send Query")
        self.send_button.setObjectName("SendQueryButton")
        self.send_button.clicked.connect(self.send_query)
        self.send_button.setMinimumWidth(150)
        self.send_button.setMinimumHeight(40)

        button_layout.addWidget(self.send_button)
        self.main_layout.addLayout(button_layout)

    def send_query(self):
        query = self.text_input.toPlainText().strip()
        if not query:
            self.text_input.setPlaceholderText("You must enter a query!")
            return
        print(f"--- Query Sent to AURA ---\nQuery: {query}")
        self.text_input.clear()
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, ClosableWidget):
            parent_widget = parent_widget.parent()
        if parent_widget:
            parent_widget.close_box()
        self.show_message("Query Sent", f"AURA is processing your request:\n\n{query[:200]}...")

    def show_message(self, title, message, icon=QMessageBox.Information):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec_()


class FaceRecognitionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(0, 10, 0, 10)
        self.main_layout.setAlignment(Qt.AlignCenter)

        instruction_label = QLabel("Select an action for the Face Recognition System:")
        instruction_label.setObjectName("TextInputInstruction")
        self.main_layout.addWidget(instruction_label, alignment=Qt.AlignCenter)

        button_layout = QGridLayout()
        button_layout.setSpacing(15)

        self.register_btn = QPushButton("Record / Register New Face")
        self.recognize_btn = QPushButton("Recognize Face (Live)")
        self.manage_btn = QPushButton("Manage Face Data")
        self.open_data_btn = QPushButton("Open Data Folder")

        for btn in [self.register_btn, self.recognize_btn, self.manage_btn, self.open_data_btn]:
            btn.setObjectName("FaceActionButton")

        button_layout.addWidget(self.register_btn, 0, 0)
        button_layout.addWidget(self.recognize_btn, 0, 1)
        button_layout.addWidget(self.manage_btn, 1, 0)
        button_layout.addWidget(self.open_data_btn, 1, 1)
        self.main_layout.addLayout(button_layout)

        self.register_btn.clicked.connect(self.register_face)
        self.recognize_btn.clicked.connect(self.recognize_face)
        self.manage_btn.clicked.connect(self.manage_dataset)
        self.open_data_btn.clicked.connect(self.open_data_folder)

    def show_message(self, title, message, icon=QMessageBox.Information):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec_()

    def _get_app_dir(self):
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        else:
            return Path(__file__).resolve().parent

    def _run_python_script(self, script_path: Path, args=None):
        base_dir = self._get_app_dir()
        exe_name = script_path.stem

        binary_name = exe_name + (".exe" if sys.platform.startswith("win") else "")
        binary_path = base_dir / binary_name
        py_path = base_dir / (exe_name + ".py")

        paths_to_try = [binary_path, py_path]
        if getattr(sys, 'frozen', False):
            try:
                tmp_dir = Path(sys._MEIPASS)
                paths_to_try.extend([tmp_dir / binary_name, tmp_dir / (exe_name + ".py")])
            except Exception:
                pass

        # Find a valid one
        target = next((p for p in paths_to_try if p.exists()), None)
        if not target:
            self.show_message("File Missing",
                              f"Cannot find {exe_name} script or binary.\nChecked:\n"
                              + "\n".join(str(p) for p in paths_to_try),
                              QMessageBox.Critical)
            return False

        
        if target.suffix == ".py":
            cmd = [sys.executable, str(target)]
        else:
            cmd = [str(target)]

        if args:
            cmd.extend(args)

        try:
            subprocess.Popen(cmd, close_fds=True)
            self.show_message("Launching", f"Running {os.path.basename(cmd[0])} ...")
            return True
        except Exception as e:
            self.show_message("Launch Failed", str(e), QMessageBox.Critical)
            return False

    def register_face(self):
        name, ok = QInputDialog.getText(self, "Register New Face", "Enter the name of the person:")
        if ok and name.strip():
            script = self._get_app_dir() / "train.py"
            self._run_python_script(script, [name.strip()])
        else:
            self.show_message("Cancelled", "Registration cancelled.")

    def recognize_face(self):
        script = self._get_app_dir() / "recognise.py"
        self._run_python_script(script)

    def manage_dataset(self):
        base = self._get_app_dir()
        folder = base / "data"
        folder.mkdir(exist_ok=True)
        files = [f.name for f in folder.glob("*.npy")]
        if not files:
            self.show_message("No Data", "No registered faces found in the 'data' folder.")
            return

        file, ok = QInputDialog.getItem(self, "Manage Dataset", "Choose face data file to manage:", files, 0, False)
        if ok and file:
            choice, ok2 = QInputDialog.getItem(self, "Action", f"Choose an action for {file}:", ["Rename", "Delete"], 0, False)
            if ok2:
                if choice == "Rename":
                    new_name, ok3 = QInputDialog.getText(self, "Rename", "Enter new name (no extension):")
                    if ok3 and new_name.strip():
                        os.rename(folder / file, folder / f"{new_name.strip()}.npy")
                        self.show_message("Renamed", f"{file} renamed to {new_name.strip()}.npy")
                elif choice == "Delete":
                    confirm = QMessageBox.question(self, "Confirm Deletion",
                                                   f"Are you sure you want to delete {file}?",
                                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if confirm == QMessageBox.Yes:
                        os.remove(folder / file)
                        self.show_message("Deleted", f"{file} deleted.")

    def open_data_folder(self):
        folder = self._get_app_dir() / "data"
        folder.mkdir(exist_ok=True)
        try:
            if sys.platform.startswith('win'):
                os.startfile(str(folder))
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(folder)])
            else:
                subprocess.Popen(['xdg-open', str(folder)])
        except Exception as e:
            self.show_message("Open Failed", f"Error: {e}", QMessageBox.Critical)



class DualQueryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(0, 10, 0, 10)

        instruction_label = QLabel("Ask AURA your question — by typing or speaking:")
        instruction_label.setObjectName("TextInputInstruction")
        self.main_layout.addWidget(instruction_label)

        # Text box
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type your question here...")
        self.text_input.setObjectName("TextInputArea")
        self.text_input.setFixedHeight(80)
        self.main_layout.addWidget(self.text_input)

        # Buttons layout
        button_layout = QHBoxLayout()
        self.send_button = QPushButton("Send")
        self.speak_button = QPushButton("Speak")
        for btn in [self.send_button, self.speak_button]:
            btn.setMinimumWidth(150)
            btn.setMinimumHeight(40)
            btn.setObjectName("SendQueryButton")
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.speak_button)
        self.main_layout.addLayout(button_layout)

        # Output display
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setObjectName("OutputBox")
        self.main_layout.addWidget(self.output_box)

        # Connect actions
        self.send_button.clicked.connect(self.handle_text_query)
        self.speak_button.clicked.connect(self.handle_voice_query)

    def handle_text_query(self):
        query = self.text_input.toPlainText().strip()
        if not query:
            self.text_input.setPlaceholderText("Please enter a question.")
            return
        self.output_box.append(f"🧑 You: {query}")
        self.text_input.clear()
        threading.Thread(target=self.process_query, args=(query,), daemon=True).start()

    def handle_voice_query(self):
        self.output_box.append("🎙 Listening... Speak now!")
        threading.Thread(target=self.process_voice_query, daemon=True).start()

    def process_voice_query(self):
        query = listen().strip()
        if not query:
            self.output_box.append("❌ No speech detected.")
            speak("I didn’t catch that. Please try again.")
            return
        self.output_box.append(f"🗣 You said: {query}")
        self.process_query(query)

    def process_query(self, query):
        try:
            answer = get_answer(query)
            self.output_box.append(f"🤖 AURA: {answer}\n")
            speak(answer)
        except Exception as e:
            self.output_box.append(f"⚠️ Error: {e}")


class BotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.BASE_DIR = Path(QCoreApplication.applicationDirPath()) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
        self.assets_dir = self.BASE_DIR / "assets"
        self.font_dir = self.BASE_DIR / "fonts"
        self.initUI()

    def initUI(self):
        self.load_custom_fonts()
        self.setWindowTitle("AURA - Humanoid Interface")
        self.setGeometry(100, 100, 1200, 700)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.central_widget = QWidget()
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.central_widget)
        window_layout = QVBoxLayout(self)
        window_layout.addWidget(self.scroll_area)
        self.setLayout(window_layout)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        bot_icon_path = self.assets_dir / "aura_icon.jpg"
        if bot_icon_path.exists():
            pixmap = QPixmap(str(bot_icon_path))
            scaled_pixmap = pixmap.scaled(QSize(400, 350), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            bot_label = QLabel()
            bot_label.setPixmap(scaled_pixmap)
            bot_label.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(bot_label)
        self.aura_label = QLabel("A U R A")
        self.aura_label.setObjectName("auraTitleLabel")
        self.aura_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.aura_label)
        main_layout.addLayout(header_layout)

        self.interactive_box = ClosableWidget(parent=self.central_widget)
        main_layout.addWidget(self.interactive_box, alignment=Qt.AlignCenter)

        # Main buttons
        button_layout = QHBoxLayout()
        self.ask_text_button = QPushButton("Ask (Text Input)")
        self.queries_btn = QPushButton("Queries")
        self.ask_text_button.clicked.connect(self.open_text_input)
        self.queries_btn.clicked.connect(self.open_dual_query)
        button_layout.addWidget(self.ask_text_button)
        button_layout.addWidget(self.queries_btn)
        main_layout.addLayout(button_layout)

        sec_layout = QHBoxLayout()
        self.train_btn = QPushButton("Record / Train Face")
        self.recognize_btn = QPushButton("Recognize Face")
        self.manage_btn = QPushButton("Manage Face Data")
        for b in [self.train_btn, self.recognize_btn, self.manage_btn]:
            sec_layout.addWidget(b)
        main_layout.addLayout(sec_layout)
        self.train_btn.clicked.connect(self.open_face_recognition)
        self.recognize_btn.clicked.connect(self.open_face_recognition)
        self.manage_btn.clicked.connect(self.open_face_recognition)
        self.setStyleSheet(self.get_stylesheet())
        self.show()

    def open_text_input(self):
        self.input_widget = TextInputWidget(self.interactive_box.content_widget)
        self.interactive_box.set_title("AURA Command Console")
        self.interactive_box.set_content_widget(self.input_widget)
        self.interactive_box.show_box(260)

    def open_dual_query(self):
        self.dual_query_widget = DualQueryWidget(self.interactive_box.content_widget)
        self.interactive_box.set_title("AURA Voice & Text Query Interface")
        self.interactive_box.set_content_widget(self.dual_query_widget)
        self.interactive_box.show_box(380)

    def open_face_recognition(self):
        self.face_widget = FaceRecognitionWidget(self.interactive_box.content_widget)
        self.interactive_box.set_title("Biometric Data Management")
        self.interactive_box.set_content_widget(self.face_widget)
        self.interactive_box.show_box(320)

    def load_custom_fonts(self):
        font_db = QFontDatabase()
        veltron = self.font_dir / "Veltorn Regular.ttf"
        centauri = self.font_dir / "Centauri.ttf"
        if veltron.exists(): font_db.addApplicationFont(str(veltron))
        if centauri.exists(): font_db.addApplicationFont(str(centauri))

    def get_stylesheet(self):
        return """
        QWidget#central_widget {
            background-color: #000;
            color: #e0e0e0;
            font-family: "Centauri", "Orbitron", monospace;
            font-size: 16pt;
        }
        #auraTitleLabel {
            font-family: "Veltron Regular", sans-serif;
            color: #8a2be2;
            font-size: 80pt;
            letter-spacing: 18px;
        }
        QPushButton {
            background-color: #3b3a61;
            color: #00ffff;
            padding: 20px 10px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 18pt;
            border: 1px solid #00ffff;
        }
        QPushButton:hover {
            background-color: #5d5c80;
            color: #e0e0e0;
        }
        #FaceActionButton {
            background-color: #1a1a2e;
            color: #bb86fc;
            border: 2px solid #bb86fc;
        }
        #FaceActionButton:hover {
            background-color: #3b3a61;
            color: #00ffff;
            border: 2px solid #00ffff;
        }
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = BotGUI()
    sys.exit(app.exec_())
