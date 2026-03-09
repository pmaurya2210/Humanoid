import subprocess
import sounddevice as sd
import numpy as np
import whisper
import requests
import scipy.io.wavfile as wav
import tempfile
import os
import warnings
warnings.filterwarnings("ignore")

# 1. Record audio using arecord (more reliable on RPi)
def record_audio(duration=5, sr=16000):
    print("Recording...")
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run([
        "arecord",
        "-D", "default",    # PipeWire will route to webcam mic automatically
        "-d", str(duration),
        "-r", str(sr),
        "-f", "S16_LE",
        "-c", "2",          # stereo
        tmp
    ])
    if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
        print("Recording failed!")
        return None
    return tmp

# 2. STT via Whisper - pass file path directly
model = whisper.load_model("base")

def transcribe(audio_path):
    result = model.transcribe(audio_path, language="en")
    os.remove(audio_path)
    return result["text"]

# 3. Send to Ollama
def ask_ollama(prompt, model="qwen2:1.5b"):
    res = requests.post("http://localhost:11434/api/generate", json={
        "model": model, "prompt": prompt, "stream": False
    })
    data = res.json()
    print("Ollama raw response:", data)
    if "response" in data:
        return data["response"]
    elif "error" in data:
        print("Ollama error:", data["error"])
        return "Sorry, I couldn't get a response."
    else:
        return "Sorry, something went wrong."

# 4. TTS via Piper
def speak(text):
    proc = subprocess.run([
        "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/piper",
        "--model", "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx",
        "--output_raw"
    ],
        input=text.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    audio = np.frombuffer(proc.stdout, dtype=np.int16)
    sd.play(audio, samplerate=22050)
    sd.wait()

# Main loop
while True:
    print("Listening...")
    audio_path = record_audio()
    text = transcribe(audio_path)
    print(f"You said: {text}")
    response = ask_ollama(text)
    print(f"AI: {response}")
    speak(response)