import serial
import serial.tools.list_ports
import subprocess

# --- CONFIG ---
BAUD_RATE = 115200
PORT = "/dev/ttyUSB0"

# --- Button labels ---
button_labels = {
    "BUTTON_1": "Button 1 (GPIO 13) pressed",
    "BUTTON_2": "Button 2 (GPIO 12) pressed",
    "BUTTON_3": "Button 3 (GPIO 14) pressed",
    "BUTTON_4": "Button 4 (GPIO 27) pressed",
}

NAMASTE_WAV = "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/Namaste_hindi.wav"

def main():
    print(f"Connecting to ESP32 on {PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print("Connected! Listening for button presses...\n")

        while True:
            line = ser.readline().decode("utf-8").strip()
            if line:
                label = button_labels.get(line, f"Unknown signal: {line}")
                print(f"[EVENT] {label}")

                if line == "BUTTON_1":
                    subprocess.run(["aplay", NAMASTE_WAV])

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        print("Tip: Run ls /dev/ttyUSB* or ls /dev/ttyACM* t// ESP32 Button to Raspberry Pi via Serial USB")
// Buttons on GPIO 13, 12, 14, 27

#define BTN1 13
#define BTN2 12
#define BTN3 14
#define BTN4 27

// Debounce time in ms
#define DEBOUNCE_MS 200

unsigned long lastPressTime[4] = {0, 0, 0, 0};
bool lastState[4] = {HIGH, HIGH, HIGH, HIGH};
int pins[4] = {BTN1, BTN2, BTN3, BTN4};

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < 4; i++) {
  }

  Serial.println("ESP32 Ready. Waiting for button presses...");
}

void loop() {
  unsigned long now = millis();

  for (int i = 0; i < 4; i++) {
    bool currentState = digitalRead(pins[i]);

    // Detect falling edge (HIGH → LOW = button pressed)
    if (currentState == LOW && lastState[i] == HIGH) {
      if (now - lastPressTime[i] > DEBOUNCE_MS) {
        lastPressTime[i] = now;
        Serial.println("BUTTON_" + String(i + 1));
      }
    }

    lastState[i] = currentState;
  }
}o find your port.")

if __name__ == "__main__":
    main()