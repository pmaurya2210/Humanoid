# """
# recognise-vertical.py — KIS Face Recognition (dlib / face_recognition)
# =======================================================================
# Upgrades over LBPH version:
#   1. dlib ResNet face encodings  — far more accurate than LBPH
#   2. Frame skipping              — detect every 3rd frame
#   3. Smaller detect input        — 160x120 for SSD
#   4. ThreadPoolExecutor          — encoding runs off main thread
#   5. Vote buffer                 — 5-frame majority vote
#   6. Non-blocking TTS            — speak() in daemon thread
#   7. Tolerance tuning            — 0.5 strict, 0.6 normal
# """

# from pathlib import Path
# import numpy as np
# import cv2
# import sys
# import subprocess
# import threading
# from concurrent.futures import ThreadPoolExecutor
# from collections import deque, Counter
# import face_recognition

# # ── Paths ──────────────────────────────────────────────────────────────────────
# BASE_DIR     = Path(__file__).resolve().parent
# dataset_path = BASE_DIR / "data"
# assets_path  = BASE_DIR / "assets"

# modelFile  = str(assets_path / "res10_300x300_ssd_iter_140000.caffemodel")
# configFile = str(assets_path / "deploy.prototxt")

# # ── Config ─────────────────────────────────────────────────────────────────────
# DETECT_EVERY   = 3        # run SSD every N frames
# DETECT_W       = 160      # width fed to SSD
# DETECT_H       = 120      # height fed to SSD
# FACE_CONF      = 0.65     # SSD confidence threshold
# MIN_FACE_PX    = 40       # ignore faces smaller than this
# VOTE_WINDOW    = 5        # majority vote over last N predictions
# TOLERANCE      = 0.5      # dlib distance threshold (lower = stricter)

# # ── Load SSD face detector ─────────────────────────────────────────────────────
# print("Loading SSD face detector...", flush=True)
# net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
# net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
# net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# # ── Load training data from .npy and build face encodings ─────────────────────
# print("Loading training data and computing face encodings...", flush=True)

# known_encodings = []   # list of 128-d dlib encodings
# known_names     = []   # corresponding person names

# if not dataset_path.exists():
#     print("'data' folder not found. Please run train.py first.")
#     sys.exit()

# for file in sorted(dataset_path.glob("*.npy")):
#     name = file.stem
#     data = np.load(file)   # shape: (N, 128, 128) grayscale

#     print(f"  Processing {name} — {data.shape[0]} images...", flush=True)
#     count = 0

#     for img in data:
#         # Convert grayscale to RGB (dlib requires RGB)
#         rgb = img

#         # Get face encodings — use face_recognition directly
#         encs = face_recognition.face_encodings(rgb)
#         if encs:
#             known_encodings.append(encs[0])
#             known_names.append(name)
#             count += 1

#     print(f"    → {count} encodings extracted for {name}", flush=True)

# if not known_encodings:
#     print("\nNo face encodings could be extracted!")
#     print("Tip: ensure faces are clearly visible in training images.")
#     sys.exit()

# print(f"\nTotal encodings loaded: {len(known_encodings)} across {len(set(known_names))} people", flush=True)

# # ── Thread pool for async encoding ────────────────────────────────────────────
# executor   = ThreadPoolExecutor(max_workers=2)
# _pred_lock = threading.Lock()


# def predict_face(face_rgb):
#     """Compute dlib encoding and match against known faces."""
#     encs = face_recognition.face_encodings(face_rgb)
#     if not encs:
#         return "Unknown"

#     distances = face_recognition.face_distance(known_encodings, encs[0])
#     best_idx  = int(np.argmin(distances))

#     if distances[best_idx] <= TOLERANCE:
#         return known_names[best_idx]
#     return "Unknown"


# # ── Non-blocking TTS ──────────────────────────────────────────────────────────
# _tts_lock = threading.Lock()
# _tts_busy = False


# def speak(text):
#     global _tts_busy
#     def _run():
#         global _tts_busy
#         with _tts_lock:
#             _tts_busy = True
#             try:
#                 proc = subprocess.run([
#                     str(BASE_DIR / "piper" / "piper"),
#                     "--model", str(BASE_DIR / "piper" / "en_US-lessac-medium.onnx"),
#                     "--output_raw"
#                 ], input=text.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#                 subprocess.run(
#                     ["aplay", "-r", "22050", "-f", "S16_LE", "-c", "1", "-t", "raw"],
#                     input=proc.stdout
#                 )
#             except Exception as e:
#                 print(f"  [TTS error: {e}]", flush=True)
#             finally:
#                 _tts_busy = False
#     threading.Thread(target=_run, daemon=True).start()


# # ── Open camera ───────────────────────────────────────────────────────────────
# cap = cv2.VideoCapture(0)
# if not cap.isOpened():
#     print("Cannot open webcam.")
#     sys.exit()

# cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
# cap.set(cv2.CAP_PROP_FPS, 30)

# print("\nPress 'r' to reset spoken names, 'q' to quit.\n", flush=True)

# # ── State ──────────────────────────────────────────────────────────────────────
# spoken_names  = set()
# frame_count   = 0
# cached_boxes  = []
# vote_buffers  = {}
# pending_preds = {}

# # ── Main loop ──────────────────────────────────────────────────────────────────
# while True:
#     ret, frame = cap.read()
#     if not ret:
#         continue

#     frame       = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
#     h, w        = frame.shape[:2]
#     frame_count += 1

#     # ── Face detection (every Nth frame) ──────────────────────────────────────
#     if frame_count % DETECT_EVERY == 0:
#         small = cv2.resize(frame, (DETECT_W, DETECT_H))
#         blob  = cv2.dnn.blobFromImage(small, 1.0, (300, 300), (104.0, 177.0, 123.0))
#         net.setInput(blob)
#         dets  = net.forward()

#         sx = w / DETECT_W
#         sy = h / DETECT_H
#         new_boxes = []

#         for i in range(dets.shape[2]):
#             conf = dets[0, 0, i, 2]
#             if conf < FACE_CONF:
#                 continue
#             bx = dets[0, 0, i, 3:7] * np.array([DETECT_W, DETECT_H, DETECT_W, DETECT_H])
#             x1, y1, x2, y2 = bx.astype(int)
#             x1 = max(0, int(x1 * sx)); y1 = max(0, int(y1 * sy))
#             x2 = min(w-1, int(x2 * sx)); y2 = min(h-1, int(y2 * sy))
#             if (x2 - x1) < MIN_FACE_PX or (y2 - y1) < MIN_FACE_PX:
#                 continue
#             new_boxes.append((x1, y1, x2, y2))

#         cached_boxes = new_boxes

#     # ── Per-face: encode + async predict ──────────────────────────────────────
#     for idx, (x1, y1, x2, y2) in enumerate(cached_boxes):
#         face_section = frame[y1:y2, x1:x2]
#         if face_section.size == 0:
#             continue

#         # Convert to RGB for dlib
#         face_rgb = cv2.cvtColor(face_section, cv2.COLOR_BGR2RGB)

#         # Submit to thread pool
#         if idx not in pending_preds or pending_preds[idx].done():
#             pending_preds[idx] = executor.submit(predict_face, face_rgb)

#         # Collect result if ready
#         pred_name = "Unknown"
#         if idx in pending_preds and pending_preds[idx].done():
#             try:
#                 raw_name = pending_preds[idx].result(timeout=0)

#                 if idx not in vote_buffers:
#                     vote_buffers[idx] = deque(maxlen=VOTE_WINDOW)
#                 vote_buffers[idx].append(raw_name)
#                 pred_name = Counter(vote_buffers[idx]).most_common(1)[0][0]

#             except Exception:
#                 pred_name = "Unknown"
#         elif idx in vote_buffers and vote_buffers[idx]:
#             pred_name = Counter(vote_buffers[idx]).most_common(1)[0][0]

#         # ── Draw ──────────────────────────────────────────────────────────────
#         color = (0, 255, 255) if pred_name != "Unknown" else (0, 80, 200)
#         cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#         cv2.putText(frame, pred_name,
#                     (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
#                     0.75, color, 2)

#         # ── Speak greeting ────────────────────────────────────────────────────
#         if pred_name not in spoken_names and pred_name != "Unknown" and not _tts_busy:
#             speak(f"Namaskar {pred_name}. Welcome to Kothari International School!")
#             spoken_names.add(pred_name)
#             print(f"  → Greeted: {pred_name}", flush=True)

#     # ── Display ───────────────────────────────────────────────────────────────
#     cv2.imshow("KIS Face Recognition", frame)
#     key = cv2.waitKey(1) & 0xFF

#     if key == ord('r'):
#         spoken_names.clear()
#         vote_buffers.clear()
#         print("  Reset spoken names and vote buffers.", flush=True)
#     elif key == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()
# executor.shutdown(wait=False)