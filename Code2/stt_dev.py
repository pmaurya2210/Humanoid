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

def get_best_input_device(test_duration=1, sr=16000):
    """Test all input devices and return the first one that captures actual audio."""
    devices = sd.query_devices()
    input_devices = [(i, dev) for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]
    
    if not input_devices:
        raise RuntimeError("No microphone found!")
    
    print(f"Found {len(input_devices)} input device(s). Auto-testing...")

    for i, dev in input_devices:
        try:
            print(f"  Testing [{i}] {dev['name']}...", end=" ")
            audio = sd.rec(int(test_duration * sr), samplerate=sr, channels=1, dtype='int16', device=i)
            sd.wait()
            level = np.max(np.abs(audio))
            print(f"level={level}")
            if level > 100:  # Not silence
                print(f"✓ Using device [{i}]: {dev['name']}")
                return i
        except Exception as e:
            print(f"failed ({e})")
            continue
    
    # Fallback: just return the first input device
    fallback = input_devices[0][0]
    print(f"Warning: All devices silent. Defaulting to [{fallback}]")
    return fallback


# Run ONCE at startup, reuse for all recordings
print("Detecting microphone...")
DEVICE_INDEX = get_best_input_device()

def record_audio(duration=5, sr=16000):
    print("Recording...")
    audio = sd.rec(int(duration * sr), samplerate=sr, channels=2, dtype='int16', device=DEVICE_INDEX)
    sd.wait()
    audio_mono = audio.mean(axis=1).astype(np.int16) # stereo -> mono
    tmp = tempfile.mktemp(suffix=".wav")
    wav.write(tmp, sr, audio_mono)
    return tmp

# 2. STT via Whisper - pass file path directly
model = whisper.load_model("base")

def transcribe(audio_path):
    result = model.transcribe(audio_path, language="en")
    os.remove(audio_path)
    return result["text"]

def ask_ollama(prompt, model="qwen2:1.5b"): #change model
    res = requests.post("http://localhost:11434/api/generate", json={"model": model, "prompt": prompt, "stream": False})
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
        [
            "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/piper",
            "--model", "/home/pradeep/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx",
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
