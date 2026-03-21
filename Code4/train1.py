# """
# train.py — KIS Face Data Collector (Optimised)
# ===============================================
# Speed upgrades:
#   1. Smaller detect input   — 160x120 for SSD (was 320x240)
#   2. Frame skipping         — process every 3rd frame (was every 5th)
#   3. Face quality filter    — blur check, skip low-quality frames
#   4. Progress bar           — visual count in terminal
#   5. Auto-quit at target    — no need to press q manually
#   6. Duplicate guard        — skip if face hasn't moved enough

# NOTE: Saves color RGB images (128x128x3) for face_recognition (dlib) compatibility.
# """

# from pathlib import Path
# import cv2
# import numpy as np
# import sys

# # ── Handle PyInstaller ────────────────────────────────────────────────────────
# if hasattr(sys, '_MEIPASS'):
#     BASE_DIR = Path(sys._MEIPASS)
# else:
#     BASE_DIR = Path(__file__).resolve().parent

# dataset_path = BASE_DIR / "data"
# assets_path  = BASE_DIR / "assets"
# dataset_path.mkdir(exist_ok=True)

# # ── Config ────────────────────────────────────────────────────────────────────
# TARGET_COUNT    = 200       # how many faces to collect
# DETECT_EVERY    = 3         # run SSD every N frames
# DETECT_W        = 160       # SSD input width  (smaller = faster)
# DETECT_H        = 120       # SSD input height
# FACE_CONF       = 0.65      # SSD confidence threshold
# MIN_FACE_PX     = 50        # ignore tiny detections
# FACE_SIZE       = 128       # saved face size
# BLUR_THRESHOLD  = 80.0      # skip blurry frames (Laplacian variance)
# MIN_MOVE_PX     = 8         # skip if face hasn't moved N pixels (avoid duplicates)

# # ── Name ──────────────────────────────────────────────────────────────────────
# if len(sys.argv) > 1:
#     person_name = sys.argv[1].strip()
#     print(f"\n  Collecting faces for: {person_name}", flush=True)
#     print(f"  Target: {TARGET_COUNT} samples", flush=True)
#     print(f"  Press 'q' to quit early.\n", flush=True)
# else:
#     print("  No name provided. Run from GUI or pass name as argument.")
#     sys.exit()

# # ── Load SSD ──────────────────────────────────────────────────────────────────
# modelFile  = str(assets_path / "res10_300x300_ssd_iter_140000.caffemodel")
# configFile = str(assets_path / "deploy.prototxt")
# net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
# net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
# net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# # ── Camera ────────────────────────────────────────────────────────────────────
# cap = cv2.VideoCapture(0)
# if not cap.isOpened():
#     print("Cannot open webcam.")
#     sys.exit()

# cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
# cap.set(cv2.CAP_PROP_FPS, 30)

# # ── State ─────────────────────────────────────────────────────────────────────
# face_data    = []
# count        = 0
# frame_count  = 0
# cached_boxes = []
# last_center  = None

# def progress_bar(current, total, width=40):
#     filled = int(width * current / total)
#     bar    = "█" * filled + "░" * (width - filled)
#     pct    = int(100 * current / total)
#     print(f"\r  [{bar}] {current}/{total}  {pct}%", end="", flush=True)

# # ── Main loop ─────────────────────────────────────────────────────────────────
# while True:
#     ret, frame = cap.read()
#     if not ret:
#         continue

#     frame       = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
#     h, w        = frame.shape[:2]
#     frame_count += 1

#     # ── Detect every Nth frame ────────────────────────────────────────────────
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

#     # ── Process detected faces ────────────────────────────────────────────────
#     for (x1, y1, x2, y2) in cached_boxes:
#         face_section = frame[y1:y2, x1:x2]
#         if face_section.size == 0:
#             continue

#         # ── Blur check ───────────────────────────────────────────────────────
#         gray_check = cv2.cvtColor(face_section, cv2.COLOR_BGR2GRAY)
#         blur_score = cv2.Laplacian(gray_check, cv2.CV_64F).var()
#         if blur_score < BLUR_THRESHOLD:
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 1)
#             cv2.putText(frame, "BLURRY", (x1, y1 - 8),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 1)
#             continue

#         # ── Duplicate guard ───────────────────────────────────────────────────
#         cx = (x1 + x2) // 2
#         cy = (y1 + y2) // 2
#         if last_center is not None:
#             move = np.sqrt((cx - last_center[0])**2 + (cy - last_center[1])**2)
#             if move < MIN_MOVE_PX and count > 10:
#                 cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 200), 1)
#                 continue
#         last_center = (cx, cy)

#         # ── Save color RGB image (required for face_recognition / dlib) ───────
#         color = cv2.resize(face_section, (FACE_SIZE, FACE_SIZE))
#         color = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
#         face_data.append(color)
#         count += 1

#         # Draw green box when saving
#         cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 100), 2)
#         cv2.putText(frame, f"{count}/{TARGET_COUNT}",
#                     (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
#                     0.7, (0, 255, 100), 2)

#         progress_bar(count, TARGET_COUNT)

#     cv2.imshow("Face Capture — KIS", frame)
#     key = cv2.waitKey(1) & 0xFF

#     if key == ord('q') or count >= TARGET_COUNT:
#         print()
#         break

# # ── Save ──────────────────────────────────────────────────────────────────────
# if face_data:
#     face_array = np.array(face_data)   # shape: (N, 128, 128, 3)
#     save_path  = dataset_path / f"{person_name}.npy"
#     np.save(save_path, face_array)
#     print(f"\n  Saved {face_array.shape[0]} faces for '{person_name}'", flush=True)
#     print(f"  Shape: {face_array.shape}", flush=True)
#     print(f"  Location: {save_path}", flush=True)
# else:
#     print("\n  No faces captured. Try again with better lighting.", flush=True)

# cap.release()
# cv2.destroyAllWindows()