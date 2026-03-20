# """
# recognise-vertical.py — KIS Face Recognition (Optimised)
# =========================================================
# Speed upgrades:
#   1. Frame skipping        — detect every 3rd frame, draw on all
#   2. Smaller detect input  — 160x120 for SSD (was 300x300 full frame)
#   3. ThreadPoolExecutor    — LBPH predict runs off main thread
#   4. Vote buffer           — 5-frame majority vote (smoother labels)
#   5. Non-blocking TTS      — speak() in daemon thread, never blocks camera

# Accuracy upgrades:
#   6. Confidence filter     — LBPH threshold tightened to 80
#   7. Min face size guard   — skip tiny false detections < 40px
#   8. ROI caching           — reuse last bbox on skipped frames
# """

# from pathlib import Path
# import numpy as np
# import cv2
# import sys
# import subprocess
# import threading
# from concurrent.futures import ThreadPoolExecutor
# from collections import deque, Counter

# # ── Paths ──────────────────────────────────────────────────────────────────────
# BASE_DIR     = Path(__file__).resolve().parent
# dataset_path = BASE_DIR / "data"
# assets_path  = BASE_DIR / "assets"

# modelFile  = str(assets_path / "res10_300x300_ssd_iter_140000.caffemodel")
# configFile = str(assets_path / "deploy.prototxt")

# # ── Config ─────────────────────────────────────────────────────────────────────
# DETECT_EVERY   = 3        # run SSD every N frames (1 = every frame, 3 = 3x faster)
# DETECT_W       = 160      # width fed to SSD (smaller = faster, was 300)
# DETECT_H       = 120      # height fed to SSD
# FACE_CONF      = 0.65     # SSD confidence threshold
# LBPH_THRESHOLD = 80.0     # lower = stricter (was 150 — way too loose)
# MIN_FACE_PX    = 40       # ignore faces smaller than this (pixels)
# VOTE_WINDOW    = 5        # majority vote over last N predictions
# FACE_SIZE      = 128      # normalised face size for LBPH


# # ── KNN (fallback, kept for compatibility) ─────────────────────────────────────
# def distance(v1, v2):
#     return np.sqrt(((v1 - v2) ** 2).sum())

# def knn(train, test, k=5):
#     dist = [[distance(test, train[i, :-1]), train[i, -1]] for i in range(train.shape[0])]
#     dk = sorted(dist, key=lambda x: x[0])[:k]
#     labels = np.array(dk)[:, -1]
#     output = np.unique(labels, return_counts=True)
#     return output[0][np.argmax(output[1])]


# # ── Load SSD model ─────────────────────────────────────────────────────────────
# print("Loading SSD face detector...", flush=True)
# net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
# net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
# net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# # ── Load training data ─────────────────────────────────────────────────────────
# face_data, labels, names = [], [], {}
# class_id = 0

# if not dataset_path.exists():
#     print("'data' folder not found. Please run train.py first.")
#     sys.exit()

# for file in sorted(dataset_path.glob("*.npy")):
#     names[class_id] = file.stem
#     print(f"  Loaded: {file.name}", flush=True)
#     data_item = np.load(file)
#     data_item = data_item.reshape(data_item.shape[0], -1)
#     face_data.append(data_item)
#     labels.append(class_id * np.ones((data_item.shape[0],)))
#     class_id += 1

# if not face_data:
#     print("No training data found. Run train.py first.")
#     sys.exit()

# face_dataset  = np.concatenate(face_data, axis=0)
# face_labels   = np.concatenate(labels, axis=0).reshape((-1, 1))
# trainset      = np.concatenate((face_dataset, face_labels), axis=1)

# print(f"\n  Dataset: {face_dataset.shape[0]} samples, {class_id} people", flush=True)


# # ── LBPH setup ─────────────────────────────────────────────────────────────────
# print("Training LBPH recogniser...", flush=True)
# lbph = cv2.face.LBPHFaceRecognizer_create(
#     radius=1, neighbors=8, grid_x=8, grid_y=8,
#     threshold=LBPH_THRESHOLD
# )

# lbph_faces, lbph_ids = [], []
# for file in sorted(dataset_path.glob("*.npy")):
#     cid = next(k for k, v in names.items() if v == file.stem)
#     for img in np.load(file):
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
#         lbph_faces.append(cv2.equalizeHist(gray))
#         lbph_ids.append(cid)

# lbph.train(lbph_faces, np.array(lbph_ids))
# print("LBPH ready!", flush=True)


# # ── Thread pool for async prediction ──────────────────────────────────────────
# executor    = ThreadPoolExecutor(max_workers=2)
# _pred_lock  = threading.Lock()

# def predict_face(face_gray):
#     """Run LBPH predict — called from thread pool."""
#     label, conf = lbph.predict(face_gray)
#     return label, conf


# # ── Non-blocking TTS ──────────────────────────────────────────────────────────
# _tts_lock    = threading.Lock()
# _tts_busy    = False

# def speak(text):
#     """Speak in a daemon thread — camera loop never blocks."""
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

#     t = threading.Thread(target=_run, daemon=True)
#     t.start()


# # ── Open camera ───────────────────────────────────────────────────────────────
# cap = cv2.VideoCapture(0)
# if not cap.isOpened():
#     print("Cannot open webcam.")
#     sys.exit()

# # Optionally set lower resolution for faster capture
# cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
# cap.set(cv2.CAP_PROP_FPS, 30)

# print("\nPress 'r' to reset spoken names, 'q' to quit.\n", flush=True)

# # ── State ──────────────────────────────────────────────────────────────────────
# spoken_names  = set()
# frame_count   = 0
# cached_boxes  = []          # reuse detections on skipped frames
# vote_buffers  = {}          # {face_index: deque of predicted names}
# pending_preds = {}          # {face_index: Future}

# # ── Main loop ──────────────────────────────────────────────────────────────────
# while True:
#     ret, frame = cap.read()
#     if not ret:
#         continue

#     frame       = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
#     h, w        = frame.shape[:2]
#     frame_count += 1

#     # ── Face detection (every Nth frame only) ──────────────────────────────────
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

#     # ── Per-face: normalise + async predict ───────────────────────────────────
#     for idx, (x1, y1, x2, y2) in enumerate(cached_boxes):
#         face_section = frame[y1:y2, x1:x2]
#         if face_section.size == 0:
#             continue

#         gray = cv2.cvtColor(face_section, cv2.COLOR_BGR2GRAY)
#         gray = cv2.equalizeHist(gray)
#         gray = cv2.resize(gray, (FACE_SIZE, FACE_SIZE))

#         # Submit prediction to thread pool (non-blocking)
#         if idx not in pending_preds or pending_preds[idx].done():
#             pending_preds[idx] = executor.submit(predict_face, gray)

#         # Collect result if ready
#         pred_name = "Unknown"
#         if idx in pending_preds and pending_preds[idx].done():
#             try:
#                 label, conf_val = pending_preds[idx].result(timeout=0)
#                 if label in names and conf_val < LBPH_THRESHOLD:
#                     raw_name = names[label]
#                 else:
#                     raw_name = "Unknown"

#                 # Vote buffer — smooth out flickering predictions
#                 if idx not in vote_buffers:
#                     vote_buffers[idx] = deque(maxlen=VOTE_WINDOW)
#                 vote_buffers[idx].append(raw_name)
#                 pred_name = Counter(vote_buffers[idx]).most_common(1)[0][0]

#             except Exception:
#                 pred_name = "Unknown"
#         elif idx in vote_buffers and vote_buffers[idx]:
#             pred_name = Counter(vote_buffers[idx]).most_common(1)[0][0]

#         # ── Draw box + label ──────────────────────────────────────────────────
#         color = (0, 255, 255) if pred_name != "Unknown" else (0, 80, 200)
#         cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#         cv2.putText(frame, pred_name,
#                     (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
#                     0.75, color, 2)

#         # ── Speak greeting (once per person, non-blocking) ───────────────────
#         if pred_name not in spoken_names and pred_name != "Unknown" and not _tts_busy:
#             speak(f"Namaskar {pred_name}. Welcome to Kothari International School!")
#             spoken_names.add(pred_name)

#     # ── Show FPS overlay ──────────────────────────────────────────────────────
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
