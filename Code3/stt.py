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

# def record_audio(duration=5, sr=16000):
#     print("Recording...")
#     audio = sd.rec(int(duration * sr), samplerate=sr, channels=2, dtype='int16', device=2)
#     sd.wait()
#     tmp = tempfile.mktemp(suffix=".wav")
#     subprocess.run(["arecord", "-d", str(duration), "-r", str(sr), "-f", "S16_LE", "-c", "1", tmp])
#     return tmp  

def record_audio(duration=5, sr=16000):
    print("Recording...")
    audio = sd.rec(int(duration * sr), samplerate=sr, channels=2, dtype='int16', device=4)
    sd.wait()
    audio_mono = audio.mean(axis=1).astype(np.int16)  # stereo -> mono
    tmp = tempfile.mktemp(suffix=".wav")
    wav.write(tmp, sr, audio_mono)
    return tmp
# 2. STT via Whisper - pass file path directly
model = whisper.load_model("base")
def transcribe(audio_path):
    result = model.transcribe(audio_path, language="en")
    os.remove(audio_path) 
    return result["text"]


def ask_ollama(prompt, model="llama3.2:1b"): #change model
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


def speak(text):
    proc = subprocess.run(
        ["/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/piper",
         "--model", "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx",
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