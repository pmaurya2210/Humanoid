

# #!/usr/bin/env python3
# from pathlib import Path
# import numpy as np
# import cv2
# import subprocess
# import sys
# import time
# import threading
# import lgpio
# import serial
# # 
# # ─────────────────────────────────────────────
# #  PATHS & MODEL
# # ─────────────────────────────────────────────
# BASE_DIR     = Path(__file__).resolve().parent
# dataset_path = BASE_DIR / "data"
# assets_path  = BASE_DIR / "assets"
# # 
# modelFile  = str(assets_path / "res10_300x300_ssd_iter_140000.caffemodel")
# configFile = str(assets_path / "deploy.prototxt")
# # 
# # ─────────────────────────────────────────────
# #  ULTRASONIC SENSOR CONFIG  (GPIO BCM pins)
# # ─────────────────────────────────────────────
# TRIG            = 23
# ECHO            = 24
# THRESHOLD_CM    = 20
# SENSOR_COOLDOWN = 5
# SENSOR_TIMEOUT  = 0.05
# # 
# # ─────────────────────────────────────────────
# #  RECOGNITION CONFIG
# # ─────────────────────────────────────────────
# USE_LBPH         = True
# RECOGNITION_TIME = 4
# LBPH_THRESHOLD   = 150
# # 
# # ─────────────────────────────────────────────
# #  GPIO SETUP
# # ─────────────────────────────────────────────
# h = lgpio.gpiochip_open(0)
# lgpio.gpio_claim_output(h, TRIG)
# lgpio.gpio_claim_input(h, ECHO)
# # 
# # ─────────────────────────────────────────────
# #  SERIAL SETUP  (ESP32 via USB)
# # ─────────────────────────────────────────────
# ESP32_PORT     = "/dev/ttyUSB0"   # Change to /dev/ttyACM0 if ttyUSB0 doesn't work
# ESP32_BAUDRATE = 115200
# # 
# try:
#     esp = serial.Serial(ESP32_PORT, ESP32_BAUDRATE, timeout=1)
#     time.sleep(2)   # Wait for ESP32 to reset after serial connection
#     print(f"ESP32 connected on {ESP32_PORT}")
# except Exception as e:
#     esp = None
#     print(f"[WARNING] ESP32 not connected: {e}")
# # 
# # 
# def send_to_esp(message):
#     """Send a message string to ESP32 over serial."""
#     if esp and esp.is_open:
#         try:
#             esp.write((message + "\n").encode())
#             print(f"  → Sent to ESP32: {message}")
#         except Exception as e:
#             print(f"  [ESP32 ERROR] {e}")
#     else:
#         print("  [ESP32] Not connected, skipping.")
# # 
# # 
# def get_distance():
#     """Measure distance via HC-SR04 ultrasonic sensor."""
#     lgpio.gpio_write(h, TRIG, 1)
#     time.sleep(0.00001)
#     lgpio.gpio_write(h, TRIG, 0)
# # 
#     start = end = time.time()
# # 
#     deadline = time.time() + SENSOR_TIMEOUT
#     while lgpio.gpio_read(h, ECHO) == 0 and time.time() < deadline:
#         start = time.time()
#     if time.time() >= deadline:
#         return None
# # 
#     deadline = time.time() + SENSOR_TIMEOUT
#     while lgpio.gpio_read(h, ECHO) == 1 and time.time() < deadline:
#         end = time.time()
#     if time.time() >= deadline:
#         return None
# # 
#     return (end - start) * 17150
# # 
# # 
# # ─────────────────────────────────────────────
# #  KNN HELPER
# # ─────────────────────────────────────────────
# def distance(v1, v2):
#     return np.sqrt(((v1 - v2) ** 2).sum())
# # 
# # 
# def knn(train, test, k=5):
#     dist = [[distance(test, train[i, :-1]), train[i, -1]] for i in range(train.shape[0])]
#     dk     = sorted(dist, key=lambda x: x[0])[:k]
#     labels = np.array(dk)[:, -1]
#     output = np.unique(labels, return_counts=True)
#     return output[0][np.argmax(output[1])]
# # 
# # 
# # ─────────────────────────────────────────────
# #  LOAD TRAINING DATA
# # ─────────────────────────────────────────────
# if not dataset_path.exists():
#     print("'data' folder not found. Please run train.py first.")
#     sys.exit()
# # 
# face_data, labels, names = [], [], {}
# class_id = 0
# # 
# for file in dataset_path.glob("*.npy"):
#     names[class_id] = file.stem
#     print("Loaded:", file.name)
#     data_item = np.load(file)
#     data_item = data_item.reshape(data_item.shape[0], -1)
#     face_data.append(data_item)
#     labels.append(class_id * np.ones((data_item.shape[0],)))
#     class_id += 1
# # 
# if not face_data:
#     print("No training data found. Please collect faces first.")
#     sys.exit()
# # 
# face_dataset = np.concatenate(face_data,  axis=0)
# face_labels  = np.concatenate(labels,     axis=0).reshape(-1, 1)
# trainset     = np.concatenate((face_dataset, face_labels), axis=1)
# # 
# print(f"\nTraining data loaded — {face_dataset.shape[0]} samples, {class_id} person(s).")
# # 
# # ─────────────────────────────────────────────
# #  LOAD DNN FACE DETECTOR
# # ─────────────────────────────────────────────
# net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
# # 
# # ─────────────────────────────────────────────
# #  TRAIN LBPH
# # ─────────────────────────────────────────────
# lbph = None
# if USE_LBPH:
#     print("Training LBPH recognizer …")
#     lbph = cv2.face.LBPHFaceRecognizer_create(
#         radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=70.0
#     )
#     lbph_faces, lbph_ids = [], []
#     for file in dataset_path.glob("*.npy"):
#         cid  = [k for k, v in names.items() if v == file.stem][0]
#         data = np.load(file)
#         for img in data:
#             gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
#             gray = cv2.equalizeHist(gray)
#             lbph_faces.append(gray)
#             lbph_ids.append(cid)
#     if lbph_faces:
#         lbph.train(lbph_faces, np.array(lbph_ids))
#         print("LBPH training complete!\n")
# # 
# # 
# # ─────────────────────────────────────────────
# #  SPEAK HELPER
# # ─────────────────────────────────────────────
# def speak(text):
#     proc = subprocess.run([
#         "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/piper",
#         "--model", "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx",
#         "--output_raw"
#     ],
#         input=text.encode(),
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE
#     )
#     subprocess.run([
#         "aplay", "-r", "22050", "-f", "S16_LE", "-c", "1", "-t", "raw"
#     ], input=proc.stdout)
# # 
# # 
# # ─────────────────────────────────────────────
# #  FACE RECOGNITION SESSION
# # ─────────────────────────────────────────────
# def run_recognition_session():
#     print("\n[Camera ON] Starting recognition session …")
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("[ERROR] Cannot access webcam.")
#         return
# # 
#     spoken_names     = set()
#     greeted_unknown  = False
#     esp_signals_sent = False
#     session_end      = time.time() + RECOGNITION_TIME
# # 
#     while time.time() < session_end:
#         ret, frame = cap.read()
#         if not ret:
#             continue
# # 
#         frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
#         h_f, w_f = frame.shape[:2]
#         blob = cv2.dnn.blobFromImage(
#             cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
#         )
#         net.setInput(blob)
#         detections = net.forward()
# # 
#         for i in range(detections.shape[2]):
#             conf = detections[0, 0, i, 2]
#             if conf < 0.6:
#                 continue
# # 
#             box = detections[0, 0, i, 3:7] * np.array([w_f, h_f, w_f, h_f])
#             x1, y1, x2, y2 = box.astype("int")
#             x1, y1 = max(0, x1), max(0, y1)
#             x2, y2 = min(w_f - 1, x2), min(h_f - 1, y2)
# # 
#             face_section = frame[y1:y2, x1:x2]
#             if face_section.size == 0:
#                 continue
# # 
#             gray = cv2.cvtColor(face_section, cv2.COLOR_BGR2GRAY)
#             gray = cv2.equalizeHist(gray)
#             gray = cv2.resize(gray, (128, 128))
# # 
#             if USE_LBPH and lbph:
#                 label, conf_val = lbph.predict(gray)
#                 pred_name = names.get(label, "Unknown") if conf_val < LBPH_THRESHOLD else "Unknown"
#             else:
#                 out       = knn(trainset, gray.flatten())
#                 pred_name = names[int(out)]
# # 
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
#             cv2.putText(frame, f"{pred_name} ({conf * 100:.1f}%)",
#                         (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
# # 
#             # ── Send "13" and "12" once, only when a face is detected ──
#             if not esp_signals_sent:
#                 send_to_esp("13")
#                 send_to_esp("12")
#                 esp_signals_sent = True
# # 
#             # ── Greet + notify ESP32 (once per session) ──
#             if pred_name != "Unknown" and pred_name not in spoken_names:
#                 speak(f"Namaskar {pred_name}. How may I assist you")
#                 send_to_esp(f"RECOGNISED:{pred_name}")
#                 spoken_names.add(pred_name)
#                 print(f"  → Greeted: {pred_name}")
# # 
#             elif pred_name == "Unknown" and not greeted_unknown:
#                 speak("Namaskar. How may I assist you")
#                 send_to_esp("RECOGNISED:UNKNOWN")
#                 greeted_unknown = True
#                 print("  → Greeted unknown visitor")
# # 
#     cap.release()
#     print("[Camera OFF] Recognition session ended.\n")
# # 
# # 
# # ─────────────────────────────────────────────
# #  MAIN LOOP
# # ─────────────────────────────────────────────
# print("System ready. Waiting for someone to approach …")
# print("Press Ctrl+C to quit.\n")
# # 
# last_trigger_time  = 0
# recognition_thread = None
# # 
# try:
#     while True:
#         dist = get_distance()
# # 
#         if dist is not None:
#             print(f"Distance: {dist:.1f} cm", end="\r")
# # 
#             person_detected = dist < THRESHOLD_CM
#             cooldown_over   = (time.time() - last_trigger_time) > SENSOR_COOLDOWN
#             camera_idle     = (recognition_thread is None or not recognition_thread.is_alive())
# # 
#             if person_detected and cooldown_over and camera_idle:
#                 print(f"\n[SENSOR] Person detected at {dist:.1f} cm — launching recognition!")
#                 last_trigger_time  = time.time()
#                 recognition_thread = threading.Thread(target=run_recognition_session, daemon=True)
#                 recognition_thread.start()
#         else:
#             print("No echo detected   ", end="\r")
# # 
#         time.sleep(0.3)
# # 
# except KeyboardInterrupt:
#     print("\nShutting down …")
# # 
# finally:
#     if recognition_thread and recognition_thread.is_alive():
#         recognition_thread.join(timeout=2)
#     if esp and esp.is_open:
#         esp.close()
#     lgpio.gpiochip_close(h)
#     print("GPIO cleaned up. Bye!")


#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import cv2
import subprocess
import sys
import time
import threading
import lgpio
import serial

# ─────────────────────────────────────────────
#  PATHS & MODEL
# ─────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
dataset_path = BASE_DIR / "data"
assets_path  = BASE_DIR / "assets"

modelFile  = str(assets_path / "res10_300x300_ssd_iter_140000.caffemodel")
configFile = str(assets_path / "deploy.prototxt")

# ─────────────────────────────────────────────
#  ULTRASONIC SENSOR CONFIG  (GPIO BCM pins)
# ─────────────────────────────────────────────
TRIG            = 23
ECHO            = 24
THRESHOLD_CM    = 20
SENSOR_COOLDOWN = 5
SENSOR_TIMEOUT  = 0.05

# ─────────────────────────────────────────────
#  RECOGNITION CONFIG
# ─────────────────────────────────────────────
USE_LBPH         = True
RECOGNITION_TIME = 4
LBPH_THRESHOLD   = 150

# ─────────────────────────────────────────────
#  SERIAL CONFIG  (shared port for ESP32)
# ─────────────────────────────────────────────
ESP32_PORT     = "/dev/ttyUSB0"
ESP32_BAUDRATE = 115200

NAMASTE_WAV = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/Namaste_hindi.wav"

# Boot messages from ESP32 to ignore
IGNORE_PREFIXES = ("ets ", "rst:", "boot:", "waiting for", "configsip", "mode:")

# Button signal labels (for logging)
BUTTON_LABELS = {
    "12":       "Button 1 (GPIO 13) pressed",
    "BUTTON_2": "Button 2 (GPIO 12) pressed",
    "BUTTON_3": "Button 3 (GPIO 14) pressed",
    "BUTTON_4": "Button 4 (GPIO 27) pressed",
}

# ─────────────────────────────────────────────
#  GPIO SETUP
# ─────────────────────────────────────────────
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, TRIG)
lgpio.gpio_claim_input(h, ECHO)

# ─────────────────────────────────────────────
#  SERIAL SETUP  (single shared connection)
# ─────────────────────────────────────────────
try:
    esp = serial.Serial(ESP32_PORT, ESP32_BAUDRATE, timeout=1)
    time.sleep(2)
    print(f"ESP32 connected on {ESP32_PORT}")
except Exception as e:
    esp = None
    print(f"[WARNING] ESP32 not connected: {e}")

# Lock to prevent read/write collisions from different threads
serial_lock = threading.Lock()


def send_to_esp(message):
    """Send a message string to ESP32 over serial."""
    if esp and esp.is_open:
        try:
            with serial_lock:
                esp.write((message + "\n").encode())
            print(f"  → Sent to ESP32: {message}")
        except Exception as e:
            print(f"  [ESP32 ERROR] {e}")
    else:
        print("  [ESP32] Not connected, skipping.")


# ─────────────────────────────────────────────
#  BUTTON LISTENER THREAD
#  Reads incoming serial lines from ESP32 and
#  reacts to button press signals.
# ─────────────────────────────────────────────
def button_listener():
    print("[Button Listener] Started, waiting for ESP32 signals…")
    while True:
        if not esp or not esp.is_open:
            time.sleep(1)
            continue
        try:
            with serial_lock:
                line = esp.readline().decode("utf-8", errors="ignore").strip()
        except Exception as e:
            print(f"[Button Listener] Read error: {e}")
            time.sleep(0.5)
            continue

        if not line:
            continue

        # Skip ESP32 boot/bootloader messages
        if any(line.startswith(p) for p in IGNORE_PREFIXES):
            print(f"[BOOT] {line}")
            continue

        # Ignore messages we sent (outbound signals echo back on some setups)
        if line.startswith("RECOGNISED:") or line in ("13",):
            continue

        label = BUTTON_LABELS.get(line, f"Unknown signal: {line}")
        print(f"[EVENT] {label}")

        if line == "12":
            subprocess.run(["aplay", NAMASTE_WAV])
        elif line == "BUTTON_2":
            print("[ACTION] Button 2 action here")
        elif line == "BUTTON_3":
            print("[ACTION] Button 3 action here")
        elif line == "BUTTON_4":
            print("[ACTION] Button 4 action here")


# ─────────────────────────────────────────────
#  ULTRASONIC DISTANCE
# ─────────────────────────────────────────────
def get_distance():
    lgpio.gpio_write(h, TRIG, 1)
    time.sleep(0.00001)
    lgpio.gpio_write(h, TRIG, 0)

    start = end = time.time()

    deadline = time.time() + SENSOR_TIMEOUT
    while lgpio.gpio_read(h, ECHO) == 0 and time.time() < deadline:
        start = time.time()
    if time.time() >= deadline:
        return None

    deadline = time.time() + SENSOR_TIMEOUT
    while lgpio.gpio_read(h, ECHO) == 1 and time.time() < deadline:
        end = time.time()
    if time.time() >= deadline:
        return None

    return (end - start) * 17150


# ─────────────────────────────────────────────
#  KNN HELPER
# ─────────────────────────────────────────────
def dist_vec(v1, v2):
    return np.sqrt(((v1 - v2) ** 2).sum())


def knn(train, test, k=5):
    dist = [[dist_vec(test, train[i, :-1]), train[i, -1]] for i in range(train.shape[0])]
    dk     = sorted(dist, key=lambda x: x[0])[:k]
    labels = np.array(dk)[:, -1]
    output = np.unique(labels, return_counts=True)
    return output[0][np.argmax(output[1])]


# ─────────────────────────────────────────────
#  LOAD TRAINING DATA
# ─────────────────────────────────────────────
if not dataset_path.exists():
    print("'data' folder not found. Please run train.py first.")
    sys.exit()

face_data, labels, names = [], [], {}
class_id = 0

for file in dataset_path.glob("*.npy"):
    names[class_id] = file.stem
    print("Loaded:", file.name)
    data_item = np.load(file)
    data_item = data_item.reshape(data_item.shape[0], -1)
    face_data.append(data_item)
    labels.append(class_id * np.ones((data_item.shape[0],)))
    class_id += 1

if not face_data:
    print("No training data found. Please collect faces first.")
    sys.exit()

face_dataset = np.concatenate(face_data,  axis=0)
face_labels  = np.concatenate(labels,     axis=0).reshape(-1, 1)
trainset     = np.concatenate((face_dataset, face_labels), axis=1)

print(f"\nTraining data loaded — {face_dataset.shape[0]} samples, {class_id} person(s).")

# ─────────────────────────────────────────────
#  LOAD DNN FACE DETECTOR
# ─────────────────────────────────────────────
net = cv2.dnn.readNetFromCaffe(configFile, modelFile)

# ─────────────────────────────────────────────
#  TRAIN LBPH
# ─────────────────────────────────────────────
lbph = None
if USE_LBPH:
    print("Training LBPH recognizer …")
    lbph = cv2.face.LBPHFaceRecognizer_create(
        radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=70.0
    )
    lbph_faces, lbph_ids = [], []
    for file in dataset_path.glob("*.npy"):
        cid  = [k for k, v in names.items() if v == file.stem][0]
        data = np.load(file)
        for img in data:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            gray = cv2.equalizeHist(gray)
            lbph_faces.append(gray)
            lbph_ids.append(cid)
    if lbph_faces:
        lbph.train(lbph_faces, np.array(lbph_ids))
        print("LBPH training complete!\n")


# ─────────────────────────────────────────────
#  SPEAK HELPER
# ─────────────────────────────────────────────
def speak(text):
    proc = subprocess.run([
        "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/piper",
        "--model", "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx",
        "--output_raw"
    ],
        input=text.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    subprocess.run([
        "aplay", "-r", "22050", "-f", "S16_LE", "-c", "1", "-t", "raw"
    ], input=proc.stdout)


# ─────────────────────────────────────────────
#  FACE RECOGNITION SESSION
# ─────────────────────────────────────────────
def run_recognition_session():
    print("\n[Camera ON] Starting recognition session …")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot access webcam.")
        return

    spoken_names     = set()
    greeted_unknown  = False
    esp_signals_sent = False
    session_end      = time.time() + RECOGNITION_TIME

    while time.time() < session_end:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        h_f, w_f = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
        )
        net.setInput(blob)
        detections = net.forward()

        for i in range(detections.shape[2]):
            conf = detections[0, 0, i, 2]
            if conf < 0.6:
                continue

            box = detections[0, 0, i, 3:7] * np.array([w_f, h_f, w_f, h_f])
            x1, y1, x2, y2 = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_f - 1, x2), min(h_f - 1, y2)

            face_section = frame[y1:y2, x1:x2]
            if face_section.size == 0:
                continue

            gray = cv2.cvtColor(face_section, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            gray = cv2.resize(gray, (128, 128))

            if USE_LBPH and lbph:
                label, conf_val = lbph.predict(gray)
                pred_name = names.get(label, "Unknown") if conf_val < LBPH_THRESHOLD else "Unknown"
            else:
                out       = knn(trainset, gray.flatten())
                pred_name = names[int(out)]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, f"{pred_name} ({conf * 100:.1f}%)",
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            # Send "13" and "12" once when first face detected
            if not esp_signals_sent:
                send_to_esp("13")
                send_to_esp("12")
                esp_signals_sent = True

            # Greet + notify ESP32 (once per person per session)
            if pred_name != "Unknown" and pred_name not in spoken_names:
                speak(f"Namaskar {pred_name}. How may I assist you")
                send_to_esp(f"RECOGNISED:{pred_name}")
                spoken_names.add(pred_name)
                print(f"  → Greeted: {pred_name}")

            elif pred_name == "Unknown" and not greeted_unknown:
                speak("Namaskar. How may I assist you")
                send_to_esp("RECOGNISED:UNKNOWN")
                greeted_unknown = True
                print("  → Greeted unknown visitor")

    cap.release()
    print("[Camera OFF] Recognition session ended.\n")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
print("System ready. Waiting for someone to approach …")
print("Press Ctrl+C to quit.\n")

# Start button listener in background
listener_thread = threading.Thread(target=button_listener, daemon=True)
listener_thread.start()

last_trigger_time  = 0
recognition_thread = None

try:
    while True:
        dist = get_distance()

        if dist is not None:
            print(f"Distance: {dist:.1f} cm", end="\r")

            person_detected = dist < THRESHOLD_CM
            cooldown_over   = (time.time() - last_trigger_time) > SENSOR_COOLDOWN
            camera_idle     = (recognition_thread is None or not recognition_thread.is_alive())

            if person_detected and cooldown_over and camera_idle:
                print(f"\n[SENSOR] Person detected at {dist:.1f} cm — launching recognition!")
                last_trigger_time  = time.time()
                recognition_thread = threading.Thread(target=run_recognition_session, daemon=True)
                recognition_thread.start()
        else:
            print("No echo detected   ", end="\r")

        time.sleep(0.3)

except KeyboardInterrupt:
    print("\nShutting down …")

finally:
    if recognition_thread and recognition_thread.is_alive():
        recognition_thread.join(timeout=2)
    if esp and esp.is_open:
        esp.close()
    lgpio.gpiochip_close(h)
    print("GPIO cleaned up. Bye!")