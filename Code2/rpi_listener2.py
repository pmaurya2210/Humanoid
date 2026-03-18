# import serial
# import serial.tools.list_ports
# import subprocess

# # --- CONFIG ---
# BAUD_RATE = 115200
# PORT = "/dev/ttyUSB0"

# # --- Button labels ---
# button_labels = {
#     "10": "Button 1 (GPIO 13) pressed",
#     "BUTTON_2": "Button 2 (GPIO 12) pressed",
#     "BUTTON_3": "Button 3 (GPIO 14) pressed",
#     "BUTTON_4": "Button 4 (GPIO 27) pressed",
# }

# NAMASTE_WAV = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/Namaste_hindi.wav"

# def main():
#     print(f"Connecting to ESP32 on {PORT} at {BAUD_RATE} baud...")
#     try:
#         ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
#         print("Connected! Listening for button presses...\n")
#         while True:
#             line = ser.readline().decode("utf-8").strip()
#             if line:
#                 label = button_labels.get(line, f"Unknown signal: {line}")
#                 print(f"[EVENT] {label}")
#                 if line == "10":
#                     subprocess.run(["aplay", NAMASTE_WAV])
#     except serial.SerialException as e:
#         print(f"Serial error: {e}")
#         print("Tip: Run ls /dev/ttyUSB* or ls /dev/ttyACM* to find your port.")  # ✅ Fixed

# if __name__ == "__main__":
#     main()



import serial
import subprocess

# --- CONFIG ---
BAUD_RATE = 115200
PORT = "/dev/ttyUSB0"

# --- Button labels ---
button_labels = {
    "10": "Button 1 (GPIO 13) pressed",
    "BUTTON_2": "Button 2 (GPIO 12) pressed",
    "BUTTON_3": "Button 3 (GPIO 14) pressed",
    "BUTTON_4": "Button 4 (GPIO 27) pressed",
}

NAMASTE_WAV = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/Namaste_hindi.wav"

# --- Boot messages to ignore ---
IGNORE_PREFIXES = ("ets ", "rst:", "boot:", "waiting for", "configsip", "mode:")

def main():
    print(f"Connecting to ESP32 on {PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print("Connected! Listening for button presses...\n")
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                continue

            # Skip ESP32 boot/bootloader messages
            if any(line.startswith(p) for p in IGNORE_PREFIXES):
                print(f"[BOOT] {line}")
                continue

            label = button_labels.get(line, f"Unknown signal: {line}")
            print(f"[EVENT] {label}")

            if line == "10":
                subprocess.run(["aplay", NAMASTE_WAV])
            elif line == "BUTTON_2":
                print("[ACTION] Button 2 action here")
            elif line == "BUTTON_3":
                print("[ACTION] Button 3 action here")
            elif line == "BUTTON_4":
                print("[ACTION] Button 4 action here")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        print("Tip: Run ls /dev/ttyUSB* or ls /dev/ttyACM* to find your port.")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        try:
            ser.close()
            print("Serial port closed.")
        except:
            pass

if __name__ == "__main__":
    main()