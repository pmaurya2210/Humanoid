import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import subprocess
import numpy as np
import tempfile
import time
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# ====== CONFIGURATION ======
MIC_DEVICE_ID   = None
DURATION        = 8
SAMPLE_RATE     = 16000
EXIT_KEYWORDS   = ["stop", "exit", "quit", "goodbye", "bye", "end"]

# ====== PIPER TTS PATHS (platform-specific) ======
if sys.platform.startswith("win"):
    PIPER_EXE   = r"C:\DataAnalysis\Batadal\piper\piper.exe"
    PIPER_MODEL = r"C:\DataAnalysis\Batadal\piper\en_US-lessac-medium.onnx"
else:
    PIPER_EXE   = "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/piper"
    PIPER_MODEL = "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx"

# ====== WHISPER SETUP ======
model = whisper.load_model("base")

# ====== KNOWLEDGE BASE ======
FACTS = {
    "principal":   "Dr. Ananya Sharma",
    "school name": "Kothari International School",
    "location":    "Pune",
    "motto":       "Knowledge is Power",
    "established": "1995",
    "grades":      "kindergarten through grade 12",
}

# ====== CORE FUNCTIONS ======
def record_audio(duration=DURATION, samplerate=SAMPLE_RATE):
    print(f"\nRecording for {duration} seconds... Speak now!", flush=True)
    audio_data = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype='int16',
        device=MIC_DEVICE_ID
    )
    sd.wait()
    tmp = tempfile.mktemp(suffix=".wav")
    write(tmp, samplerate, audio_data)
    print("Recording saved.", flush=True)
    return tmp


def transcribe(audio_path):
    print("Transcribing...", flush=True)
    result = model.transcribe(audio_path, language="en")
    os.remove(audio_path)
    return result["text"].lower().strip()


def compare_to_facts(text):
    if not text:
        return "Sorry, I didn't catch that. Could you please repeat?"
    responses = []
    if any(w in text for w in ["principal", "head", "headmaster", "director"]):
        responses.append(f"The principal's name is {FACTS['principal']}.")
    if any(w in text for w in ["school", "institution", "academy"]) and "name" in text:
        responses.append(f"The school's name is {FACTS['school name']}.")
    if any(w in text for w in ["location", "where", "place", "city", "located"]):
        responses.append(f"The school is located in {FACTS['location']}.")
    if any(w in text for w in ["motto", "slogan", "tagline"]):
        responses.append(f"The school motto is '{FACTS['motto']}'.")
    if any(w in text for w in ["established", "founded", "started", "when"]):
        responses.append(f"The school was established in {FACTS['established']}.")
    if any(w in text for w in ["grade", "class", "level"]):
        responses.append(f"We offer {FACTS['grades']}.")
    if responses:
        return " ".join(responses)
    return "Sorry, I couldn't find an answer for that. You can ask about the principal, school name, location, motto, or grades offered."


def should_exit(text):
    if not text:
        return False
    return any(kw in text for kw in EXIT_KEYWORDS)


def speak(text):
    if not text:
        return
    print(f"Speaking: {text}", flush=True)
    try:
        proc = subprocess.run(
            [PIPER_EXE, "--model", PIPER_MODEL, "--output_raw"],
            input=text.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        audio = np.frombuffer(proc.stdout, dtype=np.int16)
        sd.play(audio, samplerate=22050)
        sd.wait()
    except Exception as e:
        print(f"TTS error: {e}", flush=True)


# ====== MAIN LOOP ======
welcome = f"Welcome to {FACTS['school name']}. How can I help you today?"
print(welcome, flush=True)
speak(welcome)

while True:
    print("\nListening...", flush=True)
    audio_path = record_audio()

    text = transcribe(audio_path)
    if not text:
        speak("Sorry, I couldn't understand that. Please try again.")
        continue

    print(f"You said: {text}", flush=True)

    if should_exit(text):
        goodbye = "Thank you for using Kothari International Voice Assistant. Goodbye!"
        print(f"Bot: {goodbye}", flush=True)
        speak(goodbye)
        break

    response = compare_to_facts(text)
    print(f"Bot: {response}", flush=True)
    speak(response)

    time.sleep(1)