import serial
import subprocess
import time

# --- CONFIG ---
BAUD_RATE = 115200
PORT = "/dev/ttyUSB0"
RECONNECT_DELAY = 3  # seconds to wait before reconnecting

# --- Signal labels (handles both BUTTON_ and REMOTE_ prefixes) ---
button_labels = {
    "BUTTON_1": "Button 1 (GPIO 13) pressed",
    "BUTTON_2": "Button 2 (GPIO 12) pressed",
    "BUTTON_3": "Button 3 (GPIO 14) pressed",
    "BUTTON_4": "Button 4 (GPIO 27) pressed",
    "REMOTE_1": "Remote Button 1 pressed",
    "REMOTE_2": "Remote Button 2 pressed",
    "REMOTE_3": "Remote Button 3 pressed",
    "REMOTE_4": "Remote Button 4 pressed",
}

NAMASTE_WAV = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/Namaste_hindi.wav"

# --- Boot/noise messages to ignore ---
IGNORE_PREFIXES = ("ets ", "rst:", "boot:", "waiting for", "configsip", "mode:", "ESP32")

def handle_signal(line):
    """Handle a clean signal line from ESP32."""
    label = button_labels.get(line, f"Unknown signal: {line}")
    print(f"[EVENT] {label}")

    if line in ("BUTTON_1", "REMOTE_1"):
        subprocess.run(["aplay", NAMASTE_WAV])
    elif line in ("BUTTON_2", "REMOTE_2"):
        print("[ACTION] Button 2 — add your action here")
    elif line in ("BUTTON_3", "REMOTE_3"):
        print("[ACTION] Button 3 — add your action here")
    elif line in ("BUTTON_4", "REMOTE_4"):
        print("[ACTION] Button 4 — add your action here")

def connect(port, baud):
    """Try to open serial port, return ser object or None."""
    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"[OK] Connected to {port} at {baud} baud\n")
        return ser
    except serial.SerialException as e:
        print(f"[WAIT] Cannot connect: {e} — retrying in {RECONNECT_DELAY}s...")
        return None

def main():
    print(f"Connecting to ESP32 on {PORT} at {BAUD_RATE} baud...")
    ser = None

    while True:
        # --- Connect / Reconnect loop ---
        if ser is None:
            ser = connect(PORT, BAUD_RATE)
            if ser is None:
                time.sleep(RECONNECT_DELAY)
                continue

        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                continue

            # Skip boot/bootloader noise
            if any(line.startswith(p) for p in IGNORE_PREFIXES):
                print(f"[BOOT] {line}")
                continue

            handle_signal(line)

        except serial.SerialException as e:
            print(f"\n[DISCONNECT] {e}")
            print(f"[RECONNECT] Retrying in {RECONNECT_DELAY}s...")
            try:
                ser.close()
            except:
                pass
            ser = None
            time.sleep(RECONNECT_DELAY)

        except KeyboardInterrupt:
            print("\n[STOP] Interrupted by user.")
            break

    # Cleanup
    if ser:
        try:
            ser.close()
            print("[OK] Serial port closed.")
        except:
            pass

if __name__ == "__main__":
    main()