import subprocess
import sounddevice as sd
import numpy as np
import whisper
import requests
import scipy.io.wavfile as wav
import tempfile
import os
import warnings
import threading
import sys
import time
warnings.filterwarnings("ignore")

def record_audio(duration=5, sr=16000):
    print("Recording...")
    audio = sd.rec(int(duration * sr), samplerate=sr, channels=2, dtype='int16', device=1)
    sd.wait()
    audio_mono = audio.mean(axis=1).astype(np.int16)
    tmp = tempfile.mktemp(suffix=".wav")
    wav.write(tmp, sr, audio_mono)
    return tmp

model = whisper.load_model("base")

def transcribe(audio_path):
    result = model.transcribe(audio_path, language="en")
    os.remove(audio_path)
    return result["text"]


def thinking_spinner(stop_event):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r🤖 Thinking {spinner[i % len(spinner)]} ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + " " * 30 + "\r")  # Clear the spinner line
    sys.stdout.flush()


def ask_ollama(prompt, model="qwen2:1.5b"):
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=thinking_spinner, args=(stop_event,))
    spinner_thread.start()

    try:
        res = requests.post("http://localhost:11434/api/generate", json={
            "model": model, "prompt": prompt, "stream": False
        })
        data = res.json()
    finally:
        stop_event.set()
        spinner_thread.join()

    if "response" in data:
        return data["response"]
    elif "error" in data:
        print("Ollama error:", data["error"])
        return "Sorry, I couldn't get a response."
    else:
        return "Sorry, something went wrong."


def speak(text):
    proc = subprocess.run(
        ["/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/piper",
         "--model", "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx",
         "--output_raw"],
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