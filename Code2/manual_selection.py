import serial
import time
import subprocess
from pathlib import Path

port = "/dev/ttyUSB0"   # change if needed


PIPER_MODEL = "voices/en_US-libritts-medium.onnx"   # change to your Piper model
OUTPUT_WAV = "piper_output.wav"

def speak(text):
    """
    Use Piper TTS to convert text to speech and play it.
    """

    # 1. Run Piper TTS → generate WAV
    cmd = [
        "piper",
        "--model", PIPER_MODEL,
        "--output_file", OUTPUT_WAV,
        "--sentence_silence", "0.4"
    ]

    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        p.communicate(text.encode())  # send text to piper
    except Exception as e:
        print("Piper Error:", e)
        return

    # 2. Play the generated audio file
    subprocess.run(["aplay", OUTPUT_WAV])



bb = (
    "Greetings, everyone! "
    "Before my friend here takes over, let me show you something special. "
    "These brilliant minds standing before you are the reason I exist. "
    "They gave me purpose, they gave me presence, "
    "and they shaped every part of who I am. "
    "Please enjoy this short video that captures my journey of creation."
)



ser = serial.Serial(port, 115200, timeout=1)
time.sleep(2)

print("Listening for ESP32...")

while True:
    data = ser.readline().decode().strip()

    if data == "1":
        print("Received 1 → Speaking: Hello")
        speak("Hello")

    elif data == "2":
        print("Received 2 → Speaking full message")
        speak(bb)

    elif data == "3":
        print("Received 3 → Speaking Three")
        speak("Three")
