# import sounddevice as sd
# from scipy.io.wavfile import write
# import whisper
# import subprocess
# import numpy as np
# import tempfile
# import time
# import os
# import sys
# import re
# import warnings
# warnings.filterwarnings("ignore")

# # ====== CONFIGURATION ======
# MIC_DEVICE_ID   = None
# DURATION        = 8
# SAMPLE_RATE     = 16000
# EXIT_KEYWORDS   = ["stop", "exit", "quit", "goodbye", "bye", "end"]

# # ====== PIPER TTS PATHS (platform-specific) ======
# if sys.platform.startswith("win"):
#     PIPER_EXE   = r"C:\DataAnalysis\Batadal\piper\piper.exe"
#     PIPER_MODEL = r"C:\DataAnalysis\Batadal\piper\en_US-lessac-medium.onnx"
# else:
#     PIPER_EXE   = "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/piper"
#     PIPER_MODEL = "/home/pi/Documents/Humanoid_project/final_humanoid-main/piper/en_US-lessac-medium.onnx"

# # ====== WHISPER SETUP ======
# model = whisper.load_model("base")

# # ====== KNOWLEDGE BASE ======
# FACTS = {
#     # ── Original entries ──────────────────────────────────────────────────────
#     "who is the principal": "Ms. Petronella Eates is the Principal of Kothari International School, Pune.",
#     "who teaches science": "Science is taught by Mrs. Meena Iyer.",
#     "where is class 8a": "Class 8A is located on the second floor, left wing.",
#     "what is the school timing": "The school timing is from 8:00 AM to 2:30 PM.",
#     "where is the library": "The library is on the first floor near the staircase.",
#     "who teaches math": "Mathematics is taught by Mr. Rajesh Kumar.",
#     "how many classrooms are there": "There are 24 classrooms in total.",
#     "where is the principal office": "The principal's office is on the ground floor next to the reception.",

#     # ── General School Info ───────────────────────────────────────────────────
#     "what is the full name of the school": "The full name is Kothari International School, Pune — also known as KIS Pune.",
#     "what is the name of the school": "The school is Kothari International School, Pune (KIS Pune).",
#     "where is the school located": "The school is located at Fountain Road, Kharadi, Pune, Maharashtra – 411014, in the IT hub of Pune near World Trade Centre, City Vista Business Centre and EON IT Park.",
#     "what is the address of the school": "Kothari International School, Fountain Road, Kharadi, Pune, Maharashtra – 411014.",
#     "who founded the school": "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, also lovingly called Babuji.",
#     "when was the school founded": "The school was formally inaugurated on 16th October 2005, and the first academic session began on 1st April 2006.",
#     "when was the school inaugurated": "The school was formally inaugurated on 16th October 2005.",
#     "when did the school start": "The first academic session started on 1st April 2006.",
#     "what type of school is kis": "KIS Pune is a Day-Boarding School providing an excellent international educational experience in a safe and nurturing environment.",
#     "how big is the school campus": "The school campus is spread over a sprawling 8-acre area.",
#     "what is the campus size": "The school campus is spread over 8 acres.",
#     "what is the school affiliation number": "The CBSE affiliation number of the school is 1130849.",
#     "what board does the school follow": "The school follows the CBSE (Central Board of Secondary Education) curriculum.",
#     "what curriculum does the school follow": "Kothari International School follows the CBSE curriculum with innovative practices and methodologies.",
#     "what is the school website": "The school website is kispune.com.",
#     "what is the school email": "The school email address is admission@kispune.com.",
#     "what is the contact number of the school": "The school contact numbers are 8010-458-458, 84326 93342, and 8446031010.",
#     "what is the phone number of the school": "You can contact the school at 8010-458-458 or 84326 93342 or 8446031010.",

#     # ── Management ────────────────────────────────────────────────────────────
#     "who is the chairman of the school": "Mr. Deepak Kothari is the Chairman and Managing Director of Kothari International School.",
#     "who is the managing director": "Mr. Mitesh Kothari is the Managing Director of Kothari International School, Pune.",
#     "who is the chairperson": "Ms. Arti Kothari is the Chairperson of Kothari International School.",
#     "who is deepak kothari": "Mr. Deepak Kothari is the Chairman and Managing Director of Kothari International School.",
#     "who is mitesh kothari": "Mr. Mitesh Kothari is the Managing Director of Kothari International School, Pune.",
#     "who is arti kothari": "Ms. Arti Kothari is the Chairperson of Kothari International School.",
#     "who is the founder of kothari school": "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, known as Babuji, who started his career at a daily wage of Rs. 1.25 and built Kothari Products Ltd.",
#     "who is babuji": "Babuji refers to Late Shri Mansukhbhai Mahadevbhai Kothari, the founder of Kothari International School. He was a visionary who built one of India's largest business empires — Kothari Products Ltd.",

#     # ── Facilities ────────────────────────────────────────────────────────────
#     "what facilities does the school have": "The school has air-conditioned classrooms, an Olympic size swimming pool, Physics, Chemistry, Biology, Math and Robotics Labs, computer rooms, multimedia projectors, a sports arena, Tinker Lab, Science Lab, ICT Lab, and more.",
#     "does the school have a swimming pool": "Yes, Kothari International School has an Olympic size swimming pool on campus.",
#     "does the school have a robotics lab": "Yes, the school has a well-equipped Robotics Lab along with Physics, Chemistry, Biology and Math labs.",
#     "does the school have air conditioning": "Yes, all classrooms at KIS Pune are air-conditioned.",
#     "what labs are available in the school": "The school has Physics, Chemistry, Biology, Mathematics, Robotics, Science, ICT (Computer) and Tinker Labs.",
#     "does the school have sports facilities": "Yes, the school has a sports arena, an Olympic size swimming pool, a basketball court and various other sports facilities.",

#     # ── Admission ────────────────────────────────────────────────────────────
#     "how to apply for admission": "You can apply online at entab.online/kispun. Admissions for 2026-27 are open from Nursery to Grade 11.",
#     "how to take admission in kothari school": "Visit entab.online/kispun to fill the online admission form. You can also contact the school at 8010-458-458 or email admission@kispune.com.",
#     "is admission open": "Yes, admissions for the academic year 2026-27 are currently open from Nursery to Grade 11.",
#     "what grades are admissions open for": "Admissions are open from Nursery to Grade 11 for the academic year 2026-27.",

#     # ── Co-curricular ─────────────────────────────────────────────────────────
#     "what co-curricular activities are offered": "The school offers Art and Craft, Music by Torrins, Sports, Clubs, Festival Celebrations, Swimming, Basketball, and Sustainable Development Goals integrated events.",
#     "what sports are available": "The school offers swimming, basketball, and various other sports through a dedicated physical education program.",
#     "does the school have music classes": "Yes, the school offers music classes through Torrins Music as part of its co-curricular activities.",

#     # ── Vision, Values & Motto ───────────────────────────────────────────────
#     "what is the school motto": "The school motto is United We Stand, reflecting unity against injustice, parochialism and discrimination.",
#     "what is the school slogan": "The school slogan is United We Stand.",
#     "what are the core values of the school": "The school has 4 core values: Preferred Future, Zero Conflict World, Oxygenated Sphere, and Excellence All Around.",
#     "what is the vision of the school": "The vision is to empower students with knowledge and skills through engaged learning, ensure pursuit of higher education of their choice, and make them custodians of their own physical, mental, emotional and spiritual well-being.",
#     "what is the mission of the school": "The mission of KIS is to develop responsible global citizens and leaders through academic excellence and holistic development.",
#     "what values does the school teach": "The school is committed to moral, spiritual and ethical development and preaches the philosophy of ahimsa (non-violence) and compassion, along with integrity, respect and discipline.",

#     # ── Curriculum: Grade 1–3 ────────────────────────────────────────────────
#     "what is taught in grade 1 to 3": "In Grade 1 to 3, subjects include English, Hindi, Mathematics, Environmental Studies and Computer Literacy, with focus on the 4 R's — Reading, Writing, Arithmetic and Discovery.",
#     "what is the kid fit program": "KID-FIT is a physical education program with 250+ fun activities using props and music, targeting kids from Kindergarten to Grade 3. It develops gross motor skills, coordination, teamwork and healthy habits.",
#     "what subjects are taught in primary school": "In primary grades (1–3), subjects include English, Hindi, Mathematics, Environmental Studies and Computer Literacy.",

#     # ── Curriculum: Grade 4–10 ───────────────────────────────────────────────
#     "what subjects are taught in grade 4 to 10": "Subjects include Communicative English, a second language (Hindi, French, German, Spanish or Sanskrit), Mathematics, Science and Technology, Social Science, Work Experience, Art Education, and Physical and Health Education.",
#     "what second language options are available": "Students can choose Hindi, French, German, Spanish or Sanskrit as their second language.",
#     "what is the assessment system": "The school follows Comprehensive Continuous Formative and Summative Assessments as per the CBSE pattern. Science practicals carry 40% weightage and Social Science and Math practicals carry 20% weightage.",

#     # ── Curriculum: Grade 11–12 ──────────────────────────────────────────────
#     "what streams are available in grade 11 and 12": "Three streams are available — Science, Commerce and Humanities.",
#     "what subjects can be chosen in grade 11": "Students choose English (compulsory) plus four electives from Mathematics, Physics, Chemistry, Biology, History, Political Science, Economics, Psychology, Business Studies, Accountancy, Commercial Art, Home Science, Fashion Studies, Legal Studies, Computer Science, Physical Education, Vocal Music, Instrumental Music and Entrepreneurship.",
#     "what is asl": "ASL stands for Assessment of Speaking and Listening, introduced by CBSE in 2013-14 to enhance English communication skills for students in Grades 9 to 11.",
#     "how many students needed to start a subject": "A minimum of 8 students must opt for a subject for the school to offer it as a course in Grade 11-12.",

#     # ── Kothari Group ─────────────────────────────────────────────────────────
#     "what other schools are in kothari group": "The Kothari group includes KIS Noida, KIS Mumbai, Mansukhbhai Kothari National School Pune, Kothari Starz (Pune, Noida, Mumbai, Malad), Indrayu Academy Noida and KED American Academy.",
#     "how many schools does kothari group have": "The Kothari group has multiple schools across India including campuses in Pune, Noida, Mumbai and Malad.",
# }


# # ====== CORE FUNCTIONS ======

# def clean(text):
#     """Lowercase and remove special characters for matching."""
#     text = text.lower()
#     text = re.sub(r'[^a-z0-9\s]', '', text)
#     return text.strip()


# def get_answer(text):
#     """
#     Match transcribed text against FACTS dictionary using:
#     1. Exact match after cleaning
#     2. Token-overlap scoring (no extra dependencies needed)
#     Falls back to a helpful default message if no match found.
#     """
#     if not text:
#         return "Sorry, I didn't catch that. Could you please repeat?"

#     cleaned_input = clean(text)
#     input_tokens = set(cleaned_input.split())

#     best_key   = None
#     best_score = 0

#     for key in FACTS:
#         key_tokens = set(clean(key).split())
#         if not key_tokens:
#             continue
#         # Jaccard-style overlap: shared tokens / union of tokens
#         overlap = len(input_tokens & key_tokens)
#         union   = len(input_tokens | key_tokens)
#         score   = overlap / union if union > 0 else 0

#         # Boost score if all key tokens are present in the input
#         if key_tokens.issubset(input_tokens):
#             score += 0.5

#         if score > best_score:
#             best_score = score
#             best_key   = key

#     # Only return an answer if confidence is high enough
#     if best_score >= 0.25 and best_key:
#         return FACTS[best_key]

#     return (
#         "Sorry, I couldn't find an answer for that. "
#         "You can ask me about the principal, school name, location, "
#         "facilities, admission, curriculum, or contact details."
#     )


# def record_audio(duration=DURATION, samplerate=SAMPLE_RATE):
#     print(f"\nRecording for {duration} seconds... Speak now!", flush=True)
#     audio_data = sd.rec(
#         int(duration * samplerate),
#         samplerate=samplerate,
#         channels=1,
#         dtype='int16',
#         device=MIC_DEVICE_ID
#     )
#     sd.wait()
#     tmp = tempfile.mktemp(suffix=".wav")
#     write(tmp, samplerate, audio_data)
#     print("Recording saved.", flush=True)
#     return tmp


# def transcribe(audio_path):
#     print("Transcribing...", flush=True)
#     result = model.transcribe(audio_path, language="en")
#     os.remove(audio_path)
#     return result["text"].lower().strip()


# def should_exit(text):
#     if not text:
#         return False
#     return any(kw in text for kw in EXIT_KEYWORDS)


# def speak(text):
#     if not text:
#         return
#     print(f"Speaking: {text}", flush=True)
#     try:
#         proc = subprocess.run(
#             [PIPER_EXE, "--model", PIPER_MODEL, "--output_raw"],
#             input=text.encode(),
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )
#         audio = np.frombuffer(proc.stdout, dtype=np.int16)
#         sd.play(audio, samplerate=22050)
#         sd.wait()
#     except Exception as e:
#         print(f"TTS error: {e}", flush=True)


# # ====== MAIN LOOP ======
# welcome = "Welcome to Kothari International School. How can I help you today?"
# print(welcome, flush=True)
# speak(welcome)

# while True:
#     print("\nListening...", flush=True)
#     audio_path = record_audio()

#     text = transcribe(audio_path)
#     if not text:
#         speak("Sorry, I couldn't understand that. Please try again.")
#         continue

#     print(f"You said: {text}", flush=True)

#     if should_exit(text):
#         goodbye = "Thank you for using Kothari International Voice Assistant. Goodbye!"
#         print(f"Bot: {goodbye}", flush=True)
#         speak(goodbye)
#         break

#     response = get_answer(text)
#     print(f"Bot: {response}", flush=True)
#     speak(response)

#     time.sleep(1)

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
    print("[WARN] sentence-transformers not installed. Falling back to fuzzy match.")

try:
    from rapidfuzz import process as rf_process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("[WARN] rapidfuzz not installed. Falling back to token overlap.")


# ── CONFIGURATION ──────────────────────────────────────────────────────────────
MIC_DEVICE_ID     = None
RECORD_DURATION   = 7          # max recording seconds
SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 200        # RMS below this = silence
SILENCE_SECONDS   = 1.5        # auto-stop after N seconds of silence
EXIT_KEYWORDS     = {"stop", "exit", "quit", "goodbye", "bye", "end", "thank you"}
SBERT_THRESHOLD   = 0.42       # min cosine similarity to return answer
FUZZY_THRESHOLD   = 52         # min fuzzy score (0-100)
CONTEXT_WINDOW    = 5          # how many past turns to remember
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


# ── KNOWLEDGE BASE ─────────────────────────────────────────────────────────────
FACTS = {
    # Original entries
    "who is the principal":              "Ms. Petronella Eates is the Principal of Kothari International School, Pune.",
    "who teaches science":               "Science is taught by Mrs. Meena Iyer.",
    "where is class 8a":                 "Class 8A is located on the second floor, left wing.",
    "what is the school timing":         "The school timing is from 8:00 AM to 2:30 PM.",
    "where is the library":              "The library is on the first floor near the staircase.",
    "who teaches math":                  "Mathematics is taught by Mr. Rajesh Kumar.",
    "how many classrooms are there":     "There are 24 classrooms in total.",
    "where is the principal office":     "The principal's office is on the ground floor next to the reception.",

    # General School Info
    "what is the full name of the school":      "The full name is Kothari International School, Pune, also known as KIS Pune.",
    "what is the name of the school":           "The school is Kothari International School, Pune.",
    "where is the school located":              "The school is at Fountain Road, Kharadi, Pune, Maharashtra 411014, near World Trade Centre, City Vista and EON IT Park.",
    "what is the address of the school":        "Kothari International School, Fountain Road, Kharadi, Pune, Maharashtra 411014.",
    "who founded the school":                   "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, lovingly called Babuji.",
    "when was the school founded":              "The school was formally inaugurated on 16th October 2005, and the first academic session began on 1st April 2006.",
    "when was the school inaugurated":          "The school was formally inaugurated on 16th October 2005.",
    "when did the school start":                "The first academic session started on 1st April 2006.",
    "what type of school is kis":               "KIS Pune is a Day-Boarding School providing excellent international education in a safe and nurturing environment.",
    "how big is the school campus":             "The school campus is spread over a sprawling 8-acre area.",
    "what is the campus size":                  "The school campus is spread over 8 acres.",
    "what is the school affiliation number":    "The CBSE affiliation number of the school is 1130849.",
    "what board does the school follow":        "The school follows the CBSE curriculum.",
    "what curriculum does the school follow":   "Kothari International School follows the CBSE curriculum with innovative practices and methodologies.",
    "what is the school website":               "The school website is kispune.com.",
    "what is the school email":                 "The school email is admission@kispune.com.",
    "what is the contact number of the school": "The contact numbers are 8010-458-458, 84326 93342, and 8446031010.",
    "what is the phone number of the school":   "You can call the school at 8010-458-458 or 84326 93342 or 8446031010.",

    # Management
    "who is the chairman of the school":    "Mr. Deepak Kothari is the Chairman and Managing Director.",
    "who is the managing director":         "Mr. Mitesh Kothari is the Managing Director of KIS Pune.",
    "who is the chairperson":               "Ms. Arti Kothari is the Chairperson of Kothari International School.",
    "who is deepak kothari":                "Mr. Deepak Kothari is the Chairman and Managing Director of Kothari International School.",
    "who is mitesh kothari":                "Mr. Mitesh Kothari is the Managing Director of KIS Pune.",
    "who is arti kothari":                  "Ms. Arti Kothari is the Chairperson of Kothari International School.",
    "who is the founder of kothari school": "Late Shri Mansukhbhai Kothari, known as Babuji, started his career at Rs. 1.25 per day and built Kothari Products Ltd.",
    "who is babuji":                        "Babuji is Late Shri Mansukhbhai Mahadevbhai Kothari, the visionary founder who built one of India's largest business empires.",

    # Facilities
    "what facilities does the school have": "The school has AC classrooms, Olympic swimming pool, Physics, Chemistry, Biology, Math and Robotics Labs, computer rooms, projectors, sports arena, Tinker Lab, ICT Lab and more.",
    "does the school have a swimming pool": "Yes, KIS has an Olympic size swimming pool on campus.",
    "does the school have a robotics lab":  "Yes, the school has a well-equipped Robotics Lab along with Physics, Chemistry, Biology and Math labs.",
    "does the school have air conditioning":"Yes, all classrooms at KIS Pune are air-conditioned.",
    "what labs are available in the school":"The school has Physics, Chemistry, Biology, Mathematics, Robotics, Science, ICT and Tinker Labs.",
    "does the school have sports facilities":"Yes, the school has a sports arena, Olympic pool, basketball court and various sports facilities.",

    # Admission
    "how to apply for admission":              "Apply online at entab.online/kispun. Admissions for 2026-27 are open from Nursery to Grade 11.",
    "how to take admission in kothari school": "Visit entab.online/kispun, or call 8010-458-458, or email admission@kispune.com.",
    "is admission open":                       "Yes, admissions for 2026-27 are open from Nursery to Grade 11.",
    "what grades are admissions open for":     "Admissions are open from Nursery to Grade 11 for 2026-27.",

    # Co-curricular
    "what co-curricular activities are offered": "The school offers Art and Craft, Torrins Music, Sports, Clubs, Festival Celebrations, Swimming, Basketball and SDG events.",
    "what sports are available":                 "The school offers swimming, basketball, and many other sports through a dedicated physical education program.",
    "does the school have music classes":        "Yes, music classes are offered through Torrins Music.",

    # Vision, Values and Motto
    "what is the school motto":               "The school motto is United We Stand.",
    "what is the school slogan":              "The school slogan is United We Stand.",
    "what are the core values of the school": "The 4 core values are: Preferred Future, Zero Conflict World, Oxygenated Sphere, and Excellence All Around.",
    "what is the vision of the school":       "To empower students with knowledge and skills and make them custodians of their own physical, mental, emotional and spiritual well-being.",
    "what is the mission of the school":      "To develop responsible global citizens and leaders through academic excellence and holistic development.",
    "what values does the school teach":      "The school teaches ahimsa, compassion, integrity, respect, discipline and moral development.",

    # Curriculum Grade 1-3
    "what is taught in grade 1 to 3":           "Grade 1 to 3 covers English, Hindi, Mathematics, Environmental Studies and Computer Literacy, with focus on Reading, Writing, Arithmetic and Discovery.",
    "what is the kid fit program":              "KID-FIT has 250+ fun activities for Kindergarten to Grade 3 kids, developing motor skills, coordination, teamwork and healthy habits.",
    "what subjects are taught in primary school":"Primary grades cover English, Hindi, Mathematics, Environmental Studies and Computer Literacy.",

    # Curriculum Grade 4-10
    "what subjects are taught in grade 4 to 10": "Subjects include English, a second language (Hindi/French/German/Spanish/Sanskrit), Math, Science, Social Science, Work Experience, Art and Physical Education.",
    "what second language options are available": "Students can choose Hindi, French, German, Spanish or Sanskrit.",
    "what is the assessment system":             "The school uses Continuous Formative and Summative Assessments. Science practicals are 40%, Social Science and Math practicals are 20%.",

    # Curriculum Grade 11-12
    "what streams are available in grade 11 and 12": "Three streams: Science, Commerce and Humanities.",
    "what subjects can be chosen in grade 11":   "English plus four electives from Math, Physics, Chemistry, Biology, History, Political Science, Economics, Psychology, Business Studies, Accountancy, Computer Science, Physical Education, Music and more.",
    "what is asl":                              "ASL is Assessment of Speaking and Listening, introduced by CBSE in 2013-14 for Grades 9 to 11.",
    "how many students needed to start a subject":"Minimum 8 students must opt for a subject for it to be offered.",

    # Kothari Group
    "what other schools are in kothari group":  "KIS Noida, KIS Mumbai, MKNS Pune, Kothari Starz (Pune/Noida/Mumbai/Malad), Indrayu Academy Noida and KED American Academy.",
    "how many schools does kothari group have": "The Kothari group has schools across Pune, Noida, Mumbai and Malad.",
}

FAQ_KEYS   = list(FACTS.keys())
FAQ_VALUES = list(FACTS.values())


# ── SETUP LOGS ─────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)


# ── LOAD MODELS ────────────────────────────────────────────────────────────────
print("Loading Whisper STT model...", flush=True)
whisper_model = whisper.load_model("base")

sbert_model    = None
faq_embeddings = None

if SBERT_AVAILABLE:
    print("Loading Sentence-BERT model...", flush=True)
    sbert_model    = SentenceTransformer("all-MiniLM-L6-v2")
    faq_embeddings = sbert_model.encode(FAQ_KEYS, convert_to_tensor=True)
    print(f"SBERT ready — {len(FAQ_KEYS)} FAQ entries embedded.", flush=True)


# ── CONVERSATION MEMORY ────────────────────────────────────────────────────────
conversation_history = []   # list of {"role": "user"|"bot", "text": str}


def remember(role, text):
    """Add a turn to memory, keep last CONTEXT_WINDOW turns."""
    conversation_history.append({"role": role, "text": text})
    if len(conversation_history) > CONTEXT_WINDOW * 2:
        conversation_history.pop(0)


def build_query(current_text):
    """
    If the current utterance looks like a follow-up (short + vague),
    prepend the last user question for better context matching.
    """
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


# ── ANSWER MATCHING ────────────────────────────────────────────────────────────
def sbert_match(query):
    if not SBERT_AVAILABLE or sbert_model is None:
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
        return FACTS[result[0]], result[1] / 100.0
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
        return FACTS[best_key], best_score
    return None, best_score


def get_answer(raw_text):
    """
    3-strategy pipeline:
      1. Sentence-BERT  (semantic similarity)
      2. RapidFuzz      (fuzzy string match)
      3. Token overlap  (pure Python fallback)
    Logs unanswered queries automatically.
    """
    if not raw_text:
        return "Sorry, I didn't catch that. Could you please repeat?"

    enriched = build_query(raw_text)
    query    = clean(enriched)

    answer, score = sbert_match(query)
    if answer:
        print(f"  [SBERT  score={score:.2f}]", flush=True)
        return answer

    answer, score = fuzzy_match(query)
    if answer:
        print(f"  [Fuzzy  score={score:.2f}]", flush=True)
        return answer

    answer, score = token_overlap_match(query)
    if answer:
        print(f"  [Token  score={score:.2f}]", flush=True)
        return answer

    log_unknown(raw_text)
    return (
        "I'm sorry, I don't have an answer for that yet. "
        "You can ask me about the principal, facilities, "
        "admission, curriculum, or contact details."
    )


# ── LOGGING ────────────────────────────────────────────────────────────────────
def log_unknown(query):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(UNKNOWN_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {query}\n")
    print(f"  [Unknown query logged → {UNKNOWN_LOG}]", flush=True)


def log_conversation(user, bot):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] USER: {user}\n")
        f.write(f"[{ts}]  BOT: {bot}\n\n")


# ── SMART RECORDING WITH SILENCE DETECTION ────────────────────────────────────
def record_audio():
    """
    Record in 300ms chunks. Automatically stop when silence is detected
    for SILENCE_SECONDS after speech has started.
    """
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
    result = whisper_model.transcribe(audio_path, language="en")
    os.remove(audio_path)
    text = result["text"].strip().lower()
    # Strip filler words Whisper sometimes adds
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
            sd.wait()
    except FileNotFoundError:
        print(f"  [TTS unavailable — Piper not found]", flush=True)
    except Exception as e:
        print(f"  [TTS error: {e}]", flush=True)


# ── MAIN LOOP ──────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60, flush=True)
    print("  KIS Pune — Smart Voice Assistant", flush=True)
    print("  Say 'exit' or 'bye' to quit.", flush=True)
    print("=" * 60 + "\n", flush=True)

    welcome = "Welcome to Kothari International School. I am your smart voice assistant. How can I help you today?"
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
            print("\n[Interrupted]", flush=True)
            speak("Goodbye!")
            break
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            speak("Sorry, something went wrong. Please try again.")
            time.sleep(1)


if __name__ == "__main__":
    main()