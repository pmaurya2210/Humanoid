"""
Run this in the same terminal / venv you use to launch the GUI.
It tells you exactly why the SENSOR MODE button might be dead.
"""
import sys

print("=" * 55)
print("  AURA SENSOR BUTTON DIAGNOSTIC")
print("=" * 55)

# ── 1. Check imports ──────────────────────────────────
print("\n[1] Checking required imports …")

ok = True
for lib in ("lgpio", "numpy", "cv2"):
    try:
        __import__(lib)
        print(f"    ✓  {lib}")
    except ImportError as e:
        print(f"    ✗  {lib}  ← MISSING: {e}")
        ok = False

if not ok:
    print("\n  ► SENSOR_AVAILABLE will be False → button is DISABLED.")
    print("  ► Fix: pip install lgpio opencv-python numpy")
    sys.exit(1)

print("\n    All imports OK → SENSOR_AVAILABLE = True")

# ── 2. Check GPIO chip ────────────────────────────────
print("\n[2] Checking GPIO chip …")
try:
    import lgpio
    h = lgpio.gpiochip_open(0)
    lgpio.gpiochip_close(h)
    print("    ✓  gpiochip0 opened and closed OK")
except Exception as e:
    print(f"    ✗  GPIO ERROR: {e}")
    print("       Fix: run with sudo, or add user to 'gpio' group")
    sys.exit(1)

# ── 3. Check data folder ──────────────────────────────
print("\n[3] Checking training data …")
from pathlib import Path
import os

# Try to locate the project dir the same way the GUI does
project_dir = Path(os.path.dirname(os.path.abspath(__file__)))
data_dir    = project_dir / "data"
assets_dir  = project_dir / "assets"

print(f"    Project dir : {project_dir}")
print(f"    Data dir    : {data_dir}  {'✓ exists' if data_dir.exists() else '✗ MISSING'}")
print(f"    Assets dir  : {assets_dir}  {'✓ exists' if assets_dir.exists() else '✗ MISSING'}")

npy_files = list(data_dir.glob("*.npy")) if data_dir.exists() else []
print(f"    .npy files  : {len(npy_files)}  {[f.name for f in npy_files]}")

caffe = assets_dir / "res10_300x300_ssd_iter_140000.caffemodel"
proto = assets_dir / "deploy.prototxt"
print(f"    caffemodel  : {'✓' if caffe.exists() else '✗ MISSING'}")
print(f"    prototxt    : {'✓' if proto.exists() else '✗ MISSING'}")

# ── 4. Check PyQt5 signal wiring (dry-run) ────────────
print("\n[4] Checking PyQt5 / PySide6 …")
try:
    from PyQt5 import QtCore
    print(f"    ✓  PyQt5 found")
except ImportError:
    try:
        from PySide6 import QtCore
        print(f"    ✓  PySide6 found")
    except ImportError:
        print("    ✗  Neither PyQt5 nor PySide6 found!")
        sys.exit(1)

# ── 5. Summary ────────────────────────────────────────
print("\n" + "=" * 55)
if not npy_files:
    print("  ⚠  No .npy training data found.")
    print("     The sensor will start but models won't load.")
    print("     Run train.py first to register at least one person.")
elif not caffe.exists() or not proto.exists():
    print("  ⚠  DNN model files missing in assets/")
    print("     Copy res10_300x300_ssd_iter_140000.caffemodel")
    print("     and deploy.prototxt into the assets/ folder.")
else:
    print("  ✓  Everything looks good!")
    print("     If the button still does nothing, the issue is")
    print("     that the GUI file has SENSOR_AVAILABLE=False baked in.")
    print("     → Copy the fresh aura_gui_integrated.py and re-run.")

print("=" * 55)