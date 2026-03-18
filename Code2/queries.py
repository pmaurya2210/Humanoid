# from sentence_transformers import SentenceTransformer, util
# from rapidfuzz import process, fuzz
# from vosk import Model, KaldiRecognizer
# import torch, json, re, sounddevice as sd, pyttsx3

# faq = {
#     "who is the principal": "Dr. Anita Sharma is the principal of our school.",
#     "who teaches science": "Science is taught by Mrs. Meena Iyer.",
#     "where is class 8a": "Class 8A is located on the second floor, left wing.",
#     "what is the school timing": "The school timing is from 8:00 AM to 2:30 PM.",
#     "where is the library": "The library is on the first floor near the staircase.",
#     "who teaches math": "Mathematics is taught by Mr. Rajesh Kumar.",
#     "how many classrooms are there": "There are 24 classrooms in total.",
#     "where is the principal office": "The principal's office is on the ground floor next to the reception."
# }


# def clean(text):
#     text = text.lower()
#     text = re.sub(r'[^a-z0-9\s]', '', text)
#     return text.strip()

# print("Loading language model...")
# model = SentenceTransformer('all-MiniLM-L6-v2')
# faq_questions = list(faq.keys())
# faq_answers = list(faq.values())
# faq_embeddings = model.encode(faq_questions, convert_to_tensor=True)

# def speak(text):
#     engine = pyttsx3.init()
#     engine.setProperty('rate', 145)
#     engine.setProperty('volume', 1.0)
#     engine.say(text)
#     engine.runAndWait()
#     engine.stop()

# print("Loading Vosk speech recognition model...")
# vosk_model = Model("vosk_model_in")  
# def listen():
#     fs = 16000  # Sample rate
#     duration = 5  # seconds
#     print("Listening... Speak now!")
#     recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
#     sd.wait()

#     rec = KaldiRecognizer(vosk_model, fs)
#     rec.AcceptWaveform(recording.tobytes())
#     result = json.loads(rec.Result())
#     text = result.get("text", "")
#     return text


# def get_answer(query, semantic_threshold=0.55, fuzzy_threshold=30):
#     query_clean = clean(query)
#     if not query_clean:
#         return "I didn’t catch that. Please repeat your question."

#     fuzzy_match, fuzzy_score, _ = process.extractOne(query_clean, faq_questions, scorer=fuzz.token_sort_ratio)
#     query_emb = model.encode(query, convert_to_tensor=True)
#     scores = util.cos_sim(query_emb, faq_embeddings)[0]
#     best_idx = int(torch.argmax(scores))
#     semantic_score = float(scores[best_idx])

#     if fuzzy_score >= fuzzy_threshold and semantic_score < semantic_threshold:
#         return faq[fuzzy_match]
#     elif semantic_score >= semantic_threshold:
#         return faq_answers[best_idx]
#     else:
#         return "Sorry, I don't know that yet."


# if __name__ == "__main__":
#     print("\nOffline School Q&A Bot Ready (with Vosk Speech Recognition)")
#     while True:
#         print("\nSpeak your question (say 'exit' to quit)...")
#         query = listen().strip()
#         print(f"You said: {query}")
#         if query.lower() in ["exit", "quit"]:
#             speak("Goodbye!")
#             break
#         answer = get_answer(query)
#         print(f"Bot: {answer}\n")
#         speak(answer)
# queries_module.py

from sentence_transformers import SentenceTransformer, util
from rapidfuzz import process, fuzz
from vosk import Model, KaldiRecognizer
import torch, json, re, sounddevice as sd, pyttsx3

faq = {
    "who is the principal": "Dr. Anita Sharma is the principal of our school.",
    "who teaches science": "Science is taught by Mrs. Meena Iyer.",
    "where is class 8a": "Class 8A is located on the second floor, left wing.",
    "what is the school timing": "The school timing is from 8:00 AM to 2:30 PM.",
    "where is the library": "The library is on the first floor near the staircase.",
    "who teaches math": "Mathematics is taught by Mr. Rajesh Kumar.",
    "how many classrooms are there": "There are 24 classrooms in total.",
    "where is the principal office": "The principal's office is on the ground floor next to the reception."
}

def clean(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.strip()

# Load models once
print("Loading language model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
faq_questions = list(faq.keys())
faq_answers = list(faq.values())
faq_embeddings = model.encode(faq_questions, convert_to_tensor=True)

print("Loading Vosk model...")
vosk_model = Model("vosk_model_in")

def listen():
    fs = 16000
    duration = 5
    print("Listening... Speak now!")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    rec = KaldiRecognizer(vosk_model, fs)
    rec.AcceptWaveform(recording.tobytes())
    result = json.loads(rec.Result())
    return result.get("text", "")

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 145)
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()
    engine.stop()

def get_answer(query, semantic_threshold=0.55, fuzzy_threshold=30):
    query_clean = clean(query)
    if not query_clean:
        return "I didn’t catch that. Please repeat your question."
    fuzzy_match, fuzzy_score, _ = process.extractOne(query_clean, faq_questions, scorer=fuzz.token_sort_ratio)
    query_emb = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, faq_embeddings)[0]
    best_idx = int(torch.argmax(scores))
    semantic_score = float(scores[best_idx])
    if fuzzy_score >= fuzzy_threshold and semantic_score < semantic_threshold:
        return faq[fuzzy_match]
    elif semantic_score >= semantic_threshold:
        return faq_answers[best_idx]
    else:
        return "Sorry, I don't know that yet."
