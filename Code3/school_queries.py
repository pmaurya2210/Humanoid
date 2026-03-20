"""
Kothari International School — Smart Voice Assistant
=====================================================
Upgrades over original:
  1. Sentence-BERT semantic matching  (replaces token overlap)
  2. RapidFuzz fuzzy fallback         (catches typos / short phrases)
  3. Conversation memory              (5-turn rolling context)
  4. Confidence-gated answers         (no more wrong guesses)
  5. Unknown query logging            (self-improvement over time)
  6. VAD-style silence detection      (stops recording when user stops)
  7. Graceful error handling          (never crashes mid-loop)
  8. Category-scoped matching         (GUI passes category via sys.argv[1])
"""

import sounddevice as sd
from scipy.io.wavfile import write as wav_write
import whisper
import subprocess
import numpy as np
import tempfile
import time
import os
import sys
import re
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Try importing smart-matching libs (graceful fallback if missing) ───────────
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    import torch
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False

try:
    from rapidfuzz import process as rf_process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


# ── CONFIGURATION ──────────────────────────────────────────────────────────────
MIC_DEVICE_ID     = None
RECORD_DURATION   = 6
SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 150
SILENCE_SECONDS   = 0.8
EXIT_KEYWORDS     = {"stop", "exit", "quit", "goodbye", "bye", "end", "thank you"}
SBERT_THRESHOLD   = 0.42
FUZZY_THRESHOLD   = 52
CONTEXT_WINDOW    = 5
LOG_DIR           = Path("logs")
UNKNOWN_LOG       = LOG_DIR / "unknown_queries.log"
CONVO_LOG         = LOG_DIR / "conversation.log"

# ── PIPER TTS PATHS ────────────────────────────────────────────────────────────
if sys.platform.startswith("win"):
    PIPER_EXE   = r"C:\DataAnalysis\Batadal\piper\piper.exe"
    PIPER_MODEL = r"C:\DataAnalysis\Batadal\piper\en_US-lessac-medium.onnx"
else:
    PIPER_EXE   = "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/piper"
    PIPER_MODEL = "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx"


# ══════════════════════════════════════════════════════════════════════════════
#  CATEGORIZED KNOWLEDGE BASE
#  Each top-level key is a category slug that matches the GUI button's hint.
#  The GUI passes sys.argv[1] = one of these slugs.
#  "all" is the fallback when no category is given (merges everything).
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIZED_FACTS = {

    # ── 1. SCHOOL INFO ────────────────────────────────────────────────────────
    "school info": {
        # Basic identity
        "who is the principal":                "Miss. Petronella Eates is the Principal of Kothari International School, Pune.",
        "where is the principal office":       "The principal's office is on the ground floor next to the reception.",
        "what is the full name of the school": "The full name is Kothari International School, Pune, also known as KIS Pune.",
        "what is the name of the school":      "The school is Kothari International School, Pune.",
        "where is the school located":         "The school is at Fountain Road, Kharadi, Pune, Maharashtra 411014, near World Trade Centre, City Vista and EON IT Park.",
        "what is the address of the school":   "Kothari International School, Fountain Road, Kharadi, Pune, Maharashtra 411014.",
        "what type of school is kis":          "KIS Pune is a Day-Boarding School providing excellent international education in a safe and nurturing environment.",
        "how big is the school campus":        "The school campus is spread over a sprawling 8-acre area.",
        "what is the campus size":             "The school campus is spread over 8 acres.",
        "how many classrooms are there":       "There are 24 classrooms in total.",
        "what is the school timing":           "The school timing is from 8:00 AM to 2:30 PM.",
        "where is class 8a":                   "Class 8A is located on the second floor, left wing.",
        "where is the library":                "The library is on the first floor near the staircase.",
        # Affiliation & contact
        "what is the school affiliation number":    "The CBSE affiliation number of the school is 1130849.",
        "what board does the school follow":         "The school follows the CBSE curriculum.",
        "what curriculum does the school follow":    "Kothari International School follows the CBSE curriculum with innovative practices and methodologies.",
        "what is the school website":               "The school website is kispune.com.",
        "what is the school email":                 "The school email is admission@kispune.com.",
        "what is the contact number of the school": "The contact numbers are 8010-458-458, 84326 93342, and 8446031010.",
        "what is the phone number of the school":   "You can call the school at 8010-458-458 or 84326 93342 or 8446031010.",
        # Founding
        "who founded the school":          "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, lovingly called Babuji.",
        "when was the school founded":     "The school was formally inaugurated on 16th October 2005, and the first academic session began on 1st April 2006.",
        "when was the school inaugurated": "The school was formally inaugurated on 16th October 2005.",
        "when did the school start":       "The first academic session started on 1st April 2006.",
        # Kothari Group sister schools
        "what other schools are in kothari group":  "KIS Noida, KIS Mumbai, MKNS Pune, Kothari Starz (Pune Noida Mumbai Malad), Indrayu Academy Noida and KED American Academy.",
        "how many schools does kothari group have": "The Kothari group has schools across Pune, Noida, Mumbai and Malad.",
    },

    # ── 2. MANAGEMENT ────────────────────────────────────────────────────────
    "management": {
        "who is the principal":              "Miss. Petronella Eates is the Principal of Kothari International School, Pune.",
        "who is the chairman of the school": "Mr. Deepak Kothari is the Chairman and Managing Director.",
        "who is the managing director":      "Mr. Meetesh Kothari is the Managing Director of KIS Pune.",
        "who is the chairperson":            "Miss. Arti Kothari is the Chairperson of Kothari International School.",
        "who is deepak kothari":             "Mr. Deepak Kothari is the Chairman and Managing Director of Kothari International School.",
        "who is Meetesh kothari":             "Mr. Meetesh Kothari is the Managing Director of KIS Pune.",
        "who is arti kothari":               "Miss. Arti Kothari is the Chairperson of Kothari International School.",
        "who is the founder of kothari school": "Late Shri Mansukhbhai Kothari, known as Babuji, started his career at Rs. 1.25 per day and built Kothari Products Ltd.",
        "who is babuji":                     "Babuji is Late Shri Mansukhbhai Mahadevbhai Kothari, the visionary founder who built one of India's largest business empires.",
        "who teaches science":               "Science is taught by Mrs. Meena Iyer.",
        "who teaches math":                  "Mathematics is taught by Mr. Rajesh Kumar.",
        "who founded the school":            "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, lovingly called Babuji.",
    },

    # ── 3. FACILITIES ─────────────────────────────────────────────────────────
    "facilities": {
        "what facilities does the school have":  "The school has AC classrooms, Olympic swimming pool, Physics, Chemistry, Biology, Math and Robotics Labs, computer rooms, projectors, sports arena, Tinker Lab, ICT Lab and more.",
        "does the school have a swimming pool":  "Yes, KIS has an Olympic size swimming pool on campus.",
        "does the school have a robotics lab":   "Yes, the school has a well-equipped Robotics Lab along with Physics, Chemistry, Biology and Math labs.",
        "does the school have air conditioning": "Yes, all classrooms at KIS Pune are air-conditioned.",
        "what labs are available in the school": "The school has Physics, Chemistry, Biology, Mathematics, Robotics, Science, ICT and Tinker Labs.",
        "does the school have sports facilities":"Yes, the school has a sports arena, Olympic pool, basketball court and various sports facilities.",
        "where is the library":                  "The library is on the first floor near the staircase.",
        "how many classrooms are there":          "There are 24 classrooms in total.",
        "where is class 8a":                      "Class 8A is located on the second floor, left wing.",
        "what is the school timing":              "The school timing is from 8:00 AM to 2:30 PM.",
        "where is the principal office":          "The principal's office is on the ground floor next to the reception.",
    },

    # ── 4. ADMISSION ─────────────────────────────────────────────────────────
    "admission": {
        "how to apply for admission":              "Apply online at entab.online/kispun. Admissions for 2026-27 are open from Nursery to Grade 11.",
        "how to take admission in kothari school": "Visit entab.online/kispun, or call 8010-458-458, or email admission@kispune.com.",
        "is admission open":                       "Yes, admissions for 2026-27 are open from Nursery to Grade 11.",
        "what grades are admissions open for":     "Admissions are open from Nursery to Grade 11 for 2026-27.",
        "what is the school email":                "The school email is admission@kispune.com.",
        "what is the contact number of the school":"The contact number is  8 4 4 6 0 3 1 0 1 0.",
        "what is the phone number of the school":  "You can call the school at 8 4 4 6 0 3 1 0 1 0 .",
        "what is the school website":              "The school website is kispune.com.",
        "what type of school is kis":              "KIS Pune is a Day-Boarding School providing excellent international education in a safe and nurturing environment.",
        "how big is the school campus":            "The school campus is spread over a sprawling 8-acre area.",
        "what board does the school follow":       "The school follows the CBSE curriculum.",
    },

    # ── 5. CURRICULUM ─────────────────────────────────────────────────────────
    "curriculum": {
        # Board & affiliation
        "what board does the school follow":        "The school follows the CBSE curriculum.",
        "what curriculum does the school follow":   "Kothari International School follows the CBSE curriculum with innovative practices and methodologies.",
        "what is the school affiliation number":    "The CBSE affiliation number of the school is 1 1 3 0 8 4 9.",
        # Grade 1–3
        "what is taught in grade 1":            "Grade 1 covers English, Hindi, Mathematics, Environmental Studies and Computer Literacy, with focus on Reading, Writing, Arithmetic and Discovery.",
        "what is taught in grade 2":            "Grade 2 covers English, Hindi, Mathematics, Environmental Studies and Computer Literacy, with focus on Reading, Writing, Arithmetic and Discovery.",
        "what is taught in grade 3":            "Grade 3 covers English, Hindi, Mathematics, Environmental Studies and Computer Literacy, with focus on Reading, Writing, Arithmetic and Discovery.",
        "what is the kid fit program":               "KID-FIT has 250+ fun activities for Kindergarten to Grade 3 kids, developing motor skills, coordination, teamwork and healthy habits.",
        "what subjects are taught in primary school": "Primary grades cover English, Hindi, Mathematics, Environmental Studies and Computer Literacy.",
        # Grade 4–10
        "what subjects are taught in grade 4": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what subjects are taught in grade 5": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what subjects are taught in grade 6": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what subjects are taught in grade 7": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what subjects are taught in grade 8": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what subjects are taught in grade 9": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what subjects are taught in grade 10": "Subjects include English, a second language (Hindi,French, German, Spanish, Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
        "what second language options are available": "Students can choose Hindi, French, German, Spanish or Sanskrit.",
        "what is the assessment system":             "The school uses Continuous Formative and Summative Assessments. Science practicals are 40%, Social Science and Math practicals are 20%.",
        # Grade 11–12
        "what streams are available in grade 11 and 12": "Three streams: Science, Commerce and Humanities.",
        "what subjects can be chosen in grade 11":        "English plus four electives from Math, Physics, Chemistry, Biology, History, Political Science, Economics, Psychology, Business Studies, Accountancy, Computer Science, Physical Education, Music and more.",
        "what is asl":                               "ASL is Assessment of Speaking and Listening, introduced by CBSE in 2013-14 for Grades 9 to 11.",
        "how many students needed to start a subject":"Minimum 8 students must opt for a subject for it to be offered.",
        # Teachers
        "who teaches science": "Science is taught by Mrs. Meena Iyer.",
        "who teaches math":    "Mathematics is taught by Mr. Rajesh Kumar.",
    },

    # ── 6. CO-CURRICULAR ──────────────────────────────────────────────────────
    "co-curricular": {
        # Activities
        "what co-curricular activities are offered": "The school offers Art and Craft, Torrins Music, Sports, Clubs, Festival Celebrations, Swimming, Basketball and SDG events.",
        "what sports are available":                 "The school offers swimming, basketball, and many other sports through a dedicated physical education program.",
        "does the school have music classes":        "Yes, music classes are offered through Torrins Music.",
        "does the school have sports facilities":    "Yes, the school has a sports arena, Olympic pool, basketball court and various sports facilities.",
        "does the school have a swimming pool":      "Yes, KIS has an Olympic size swimming pool on campus.",
        # Vision, values, motto
        "what is the school motto":               "The school motto is United We Stand.",
        "what is the school slogan":              "The school slogan is United We Stand.",
        "what are the core values of the school": "The 4 core values are: Preferred Future, Zero Conflict World, Oxygenated Sphere, and Excellence All Around.",
        "what is the vision of the school":       "To empower students with knowledge and skills and make them custodians of their own physical, mental, emotional and spiritual well-being.",
        "what is the mission of the school":      "To develop responsible global citizens and leaders through academic excellence and holistic development.",
        "what values does the school teach":      "The school teaches ahimsa, compassion, integrity, respect, discipline and moral development.",
        # KID-FIT fits here too
        "what is the kid fit program": "KID-FIT has 250+ fun activities for Kindergarten to Grade 3 kids, developing motor skills, coordination, teamwork and healthy habits.",
    },
}


# ── CATEGORY WELCOME MESSAGES ──────────────────────────────────────────────────
CATEGORY_WELCOME = {
    "school info":    "Welcome! You can ask me anything about Kothari International School — its name, location, timings, contact details, and more.",
    "management":     "Welcome! You can ask me about our Principal, Chairman, Managing Director, Chairperson, teachers, and the school's founders.",
    "facilities":     "Welcome! You can ask me about the school's facilities — labs, swimming pool, sports arena, classrooms, library and more.",
    "admission":      "Welcome! You can ask me about admissions — how to apply, which grades are open, fees, contact details and the admission process.",
    "curriculum":     "Welcome! You can ask me about the curriculum — subjects for each grade, streams in Grade 11 and 12, assessment system and more.",
    "co-curricular":  "Welcome! You can ask me about co-curricular activities — sports, music, arts, clubs, the school motto, vision and values.",
    "all":            "Welcome to Kothari International School. I am your smart voice assistant. How can I help you today?",
}


# ── BUILD ACTIVE FACTS FROM CATEGORY ──────────────────────────────────────────
def build_active_facts(category: str) -> dict:
    """Return the FACTS dict for the chosen category, or merge all if 'all'."""
    cat = category.strip().lower()
    if cat in CATEGORIZED_FACTS:
        return dict(CATEGORIZED_FACTS[cat])
    # Unknown or missing category → merge everything
    merged = {}
    for sub in CATEGORIZED_FACTS.values():
        merged.update(sub)
    return merged


# Read category from command-line argument (set by the GUI)
# Example: python school_queries.py "facilities"
ACTIVE_CATEGORY = sys.argv[1].strip().lower() if len(sys.argv) > 1 else "all"
ACTIVE_FACTS    = build_active_facts(ACTIVE_CATEGORY)
FAQ_KEYS        = list(ACTIVE_FACTS.keys())
FAQ_VALUES      = list(ACTIVE_FACTS.values())


# ── SETUP LOGS ─────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)


# ── LOAD MODELS ────────────────────────────────────────────────────────────────
whisper_model = whisper.load_model("tiny")

sbert_model    = None
faq_embeddings = None

if SBERT_AVAILABLE:
    sbert_model    = SentenceTransformer("all-MiniLM-L6-v2")
    faq_embeddings = sbert_model.encode(FAQ_KEYS, convert_to_tensor=True)


# ── CONVERSATION MEMORY ────────────────────────────────────────────────────────
conversation_history = []


def remember(role, text):
    conversation_history.append({"role": role, "text": text})
    if len(conversation_history) > CONTEXT_WINDOW * 2:
        conversation_history.pop(0)


def build_query(current_text):
    follow_up_words = {"more", "it", "that", "this", "also", "and",
                       "what about", "tell me", "explain", "details"}
    words = set(current_text.lower().split())
    is_follow_up = bool(words & follow_up_words) and len(words) <= 6
    if is_follow_up:
        past = [t["text"] for t in conversation_history if t["role"] == "user"]
        if past:
            return past[-1] + " " + current_text
    return current_text


# ── TEXT CLEANING ──────────────────────────────────────────────────────────────
def clean(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.strip()


# ── ANSWER MATCHING  (searches only ACTIVE_FACTS) ─────────────────────────────
def sbert_match(query):
    if not SBERT_AVAILABLE or sbert_model is None or faq_embeddings is None:
        return None, 0.0
    q_emb  = sbert_model.encode(query, convert_to_tensor=True)
    scores = st_util.cos_sim(q_emb, faq_embeddings)[0]
    idx    = int(torch.argmax(scores))
    score  = float(scores[idx])
    if score >= SBERT_THRESHOLD:
        return FAQ_VALUES[idx], score
    return None, score


def fuzzy_match(query):
    if not FUZZY_AVAILABLE:
        return None, 0.0
    result = rf_process.extractOne(query, FAQ_KEYS, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= FUZZY_THRESHOLD:
        return ACTIVE_FACTS[result[0]], result[1] / 100.0
    return None, 0.0


def token_overlap_match(query):
    tokens = set(clean(query).split())
    best_key, best_score = None, 0.0
    for key in FAQ_KEYS:
        key_tokens = set(clean(key).split())
        if not key_tokens:
            continue
        overlap = len(tokens & key_tokens)
        union   = len(tokens | key_tokens)
        score   = overlap / union if union else 0.0
        if key_tokens.issubset(tokens):
            score += 0.4
        if score > best_score:
            best_score, best_key = score, key
    if best_score >= 0.30 and best_key:
        return ACTIVE_FACTS[best_key], best_score
    return None, best_score


def get_answer(raw_text):
    """
    3-strategy pipeline scoped to ACTIVE_FACTS (the selected category).
    Falls back to a friendly message if no match is found.
    """
    if not raw_text:
        return "Sorry, I didn't catch that. Could you please repeat?"

    enriched = build_query(raw_text)
    query    = clean(enriched)

    answer, score = sbert_match(query)
    if answer:
        print(f"  [SBERT  score={score:.2f}  category={ACTIVE_CATEGORY}]", flush=True)
        return answer

    answer, score = fuzzy_match(query)
    if answer:
        print(f"  [Fuzzy  score={score:.2f}  category={ACTIVE_CATEGORY}]", flush=True)
        return answer

    answer, score = token_overlap_match(query)
    if answer:
        print(f"  [Token  score={score:.2f}  category={ACTIVE_CATEGORY}]", flush=True)
        return answer

    log_unknown(raw_text)

    # Give a category-specific hint in the fallback message
    hints = {
        "school info":   "the school's name, location, timings, contact details or affiliation",
        "management":    "the principal, chairman, managing director, chairperson or teachers",
        "facilities":    "labs, swimming pool, sports facilities, classrooms or the library",
        "admission":     "how to apply, which grades are open, or the school contact details",
        "curriculum":    "subjects by grade, streams in Grade 11 and 12, or the assessment system",
        "co-curricular": "sports, music, arts, clubs, the school motto, vision or values",
        "all":           "the principal, facilities, admission, curriculum or contact details",
    }
    hint = hints.get(ACTIVE_CATEGORY, hints["all"])
    return f"I'm sorry, I don't have an answer for that yet. You can ask me about {hint}."


# ── LOGGING ────────────────────────────────────────────────────────────────────
def log_unknown(query):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(UNKNOWN_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{ACTIVE_CATEGORY.upper()}] {query}\n")


def log_conversation(user, bot):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{ACTIVE_CATEGORY.upper()}] USER: {user}\n")
        f.write(f"[{ts}] [{ACTIVE_CATEGORY.upper()}]  BOT: {bot}\n\n")


# ── SMART RECORDING WITH SILENCE DETECTION ────────────────────────────────────
def record_audio():
    chunk_size    = int(SAMPLE_RATE * 0.3)
    max_chunks    = int(RECORD_DURATION / 0.3)
    silence_limit = int(SILENCE_SECONDS / 0.3)

    print("\nListening... (speak now, silence auto-stops)", flush=True)
    frames         = []
    silent_chunks  = 0
    speech_started = False

    for _ in range(max_chunks):
        chunk = sd.rec(chunk_size, samplerate=SAMPLE_RATE, channels=1,
                       dtype="int16", device=MIC_DEVICE_ID)
        sd.wait()
        rms = int(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

        if rms > SILENCE_THRESHOLD:
            speech_started = True
            silent_chunks  = 0
        else:
            silent_chunks += 1

        frames.append(chunk)

        if speech_started and silent_chunks >= silence_limit:
            print("  (silence — stopping)", flush=True)
            break

    audio = np.concatenate(frames, axis=0)
    tmp   = tempfile.mktemp(suffix=".wav")
    wav_write(tmp, SAMPLE_RATE, audio)
    return tmp


# ── TRANSCRIPTION ──────────────────────────────────────────────────────────────
def transcribe(audio_path):
    print("Transcribing...", flush=True)
    result = whisper_model.transcribe(
        audio_path,
        language="en",
        beam_size=1,
        best_of=1,
        temperature=0.0,
        fp16=False,
        condition_on_previous_text=False,
    )
    os.remove(audio_path)
    text = result["text"].strip().lower()
    text = re.sub(r"^(um+|uh+|hmm+|like|so|okay|ok)\s+", "", text)
    return text


# ── EXIT DETECTION ─────────────────────────────────────────────────────────────
def should_exit(text):
    if not text:
        return False
    return bool(set(clean(text).split()) & EXIT_KEYWORDS)


# ── TTS SPEAK ──────────────────────────────────────────────────────────────────
def speak(text):
    if not text:
        return
    print(f"Bot: {text}", flush=True)
    try:
        proc = subprocess.run(
            [PIPER_EXE, "--model", PIPER_MODEL, "--output_raw"],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        audio = np.frombuffer(proc.stdout, dtype=np.int16)
        if audio.size > 0:
            sd.play(audio, samplerate=22050)
            try:
                sd.wait()
            except KeyboardInterrupt:
                sd.stop()
                raise
    except FileNotFoundError:
        print(f"  [TTS unavailable — Piper not found at {PIPER_EXE}]", flush=True)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"  [TTS error: {e}]", flush=True)


# ── MAIN LOOP ──────────────────────────────────────────────────────────────────
def main():
    cat_display = ACTIVE_CATEGORY.upper() if ACTIVE_CATEGORY != "all" else "ALL CATEGORIES"
    print("\n" + "=" * 60, flush=True)
    print(f"  KIS Pune — Smart Voice Assistant", flush=True)
    print(f"  Category : {cat_display}", flush=True)
    print(f"  Questions: {len(FAQ_KEYS)} loaded", flush=True)
    print("  Say 'exit' or 'bye' to quit.", flush=True)
    print("=" * 60 + "\n", flush=True)

    if not SBERT_AVAILABLE or not FUZZY_AVAILABLE:
        print("[TIP] For smarter matching, run:", flush=True)
        print("  pip install sentence-transformers rapidfuzz", flush=True)
        print("", flush=True)

    welcome = CATEGORY_WELCOME.get(ACTIVE_CATEGORY, CATEGORY_WELCOME["all"])
    speak(welcome)

    while True:
        try:
            audio_path = record_audio()
            text       = transcribe(audio_path)

            if not text:
                speak("I couldn't catch that. Please try again.")
                continue

            print(f"\nYou: {text}", flush=True)

            if should_exit(text):
                farewell = "Thank you for using the KIS Voice Assistant. Have a wonderful day. Goodbye!"
                speak(farewell)
                log_conversation(text, farewell)
                break

            remember("user", text)
            response = get_answer(text)
            remember("bot", response)

            speak(response)
            log_conversation(text, response)
            time.sleep(0.5)

        except KeyboardInterrupt:
            sd.stop()
            print("\n[Stopped by user]", flush=True)
            break
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            speak("Sorry, something went wrong. Please try again.")
            time.sleep(1)


if __name__ == "__main__":
    main()
