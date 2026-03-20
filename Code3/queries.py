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
    # ── Original entries ──────────────────────────────────────────────────────
    "who is the principal": "Ms. Petronella Eates is the Principal of Kothari International School, Pune.",
    "who teaches science": "Science is taught by Mrs. Meena Iyer.",
    "where is class 8a": "Class 8A is located on the second floor, left wing.",
    "what is the school timing": "The school timing is from 8:00 AM to 2:30 PM.",
    "where is the library": "The library is on the first floor near the staircase.",
    "who teaches math": "Mathematics is taught by Mr. Rajesh Kumar.",
    "how many classrooms are there": "There are 24 classrooms in total.",
    "where is the principal office": "The principal's office is on the ground floor next to the reception.",
 
    # ── General School Info ───────────────────────────────────────────────────
    "what is the full name of the school": "The full name is Kothari International School, Pune — also known as KIS Pune.",
    "what is the name of the school": "The school is Kothari International School, Pune (KIS Pune).",
    "where is the school located": "The school is located at Fountain Road, Kharadi, Pune, Maharashtra – 411014, in the IT hub of Pune near World Trade Centre, City Vista Business Centre and EON IT Park.",
    "what is the address of the school": "Kothari International School, Fountain Road, Kharadi, Pune, Maharashtra – 411014.",
    "who founded the school": "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, also lovingly called Babuji.",
    "when was the school founded": "The school was formally inaugurated on 16th October 2005, and the first academic session began on 1st April 2006.",
    "when was the school inaugurated": "The school was formally inaugurated on 16th October 2005.",
    "when did the school start": "The first academic session started on 1st April 2006.",
    "what type of school is kis": "KIS Pune is a Day-Boarding School providing an excellent international educational experience in a safe and nurturing environment.",
    "how big is the school campus": "The school campus is spread over a sprawling 8-acre area.",
    "what is the campus size": "The school campus is spread over 8 acres.",
    "what is the school affiliation number": "The CBSE affiliation number of the school is 1130849.",
    "what board does the school follow": "The school follows the CBSE (Central Board of Secondary Education) curriculum.",
    "what curriculum does the school follow": "Kothari International School follows the CBSE curriculum with innovative practices and methodologies.",
    "what is the school website": "The school website is kispune.com.",
    "what is the school email": "The school email address is admission@kispune.com.",
    "what is the contact number of the school": "The school contact numbers are 8010-458-458, 84326 93342, and 8446031010.",
    "what is the phone number of the school": "You can contact the school at 8010-458-458 or 84326 93342 or 8446031010.",
 
    # ── Management ────────────────────────────────────────────────────────────
    "who is the chairman of the school": "Mr. Deepak Kothari is the Chairman and Managing Director of Kothari International School.",
    "who is the managing director": "Mr. Mitesh Kothari is the Managing Director of Kothari International School, Pune.",
    "who is the chairperson": "Ms. Arti Kothari is the Chairperson of Kothari International School.",
    "who is deepak kothari": "Mr. Deepak Kothari is the Chairman and Managing Director of Kothari International School.",
    "who is mitesh kothari": "Mr. Mitesh Kothari is the Managing Director of Kothari International School, Pune.",
    "who is arti kothari": "Ms. Arti Kothari is the Chairperson of Kothari International School.",
    "who is the founder of kothari school": "The school was founded by Late Shri Mansukhbhai Mahadevbhai Kothari, known as Babuji, who started his career at a daily wage of Rs. 1.25 and built Kothari Products Ltd.",
    "who is babuji": "Babuji refers to Late Shri Mansukhbhai Mahadevbhai Kothari, the founder of Kothari International School. He was a visionary who built one of India's largest business empires — Kothari Products Ltd.",
 
    # ── Facilities ────────────────────────────────────────────────────────────
    "what facilities does the school have": "The school has air-conditioned classrooms, an Olympic size swimming pool, Physics, Chemistry, Biology, Math and Robotics Labs, computer rooms, multimedia projectors, a sports arena, Tinker Lab, Science Lab, ICT Lab, and more.",
    "does the school have a swimming pool": "Yes, Kothari International School has an Olympic size swimming pool on campus.",
    "does the school have a robotics lab": "Yes, the school has a well-equipped Robotics Lab along with Physics, Chemistry, Biology and Math labs.",
    "does the school have air conditioning": "Yes, all classrooms at KIS Pune are air-conditioned.",
    "what labs are available in the school": "The school has Physics, Chemistry, Biology, Mathematics, Robotics, Science, ICT (Computer) and Tinker Labs.",
    "does the school have sports facilities": "Yes, the school has a sports arena, an Olympic size swimming pool, a basketball court and various other sports facilities.",
 
    # ── Admission ────────────────────────────────────────────────────────────
    "how to apply for admission": "You can apply online at entab.online/kispun. Admissions for 2026-27 are open from Nursery to Grade 11.",
    "how to take admission in kothari school": "Visit entab.online/kispun to fill the online admission form. You can also contact the school at 8010-458-458 or email admission@kispune.com.",
    "is admission open": "Yes, admissions for the academic year 2026-27 are currently open from Nursery to Grade 11.",
    "what grades are admissions open for": "Admissions are open from Nursery to Grade 11 for the academic year 2026-27.",
 
    # ── Co-curricular ─────────────────────────────────────────────────────────
    "what co-curricular activities are offered": "The school offers Art and Craft, Music by Torrins, Sports, Clubs, Festival Celebrations, Swimming, Basketball, and Sustainable Development Goals integrated events.",
    "what sports are available": "The school offers swimming, basketball, and various other sports through a dedicated physical education program.",
    "does the school have music classes": "Yes, the school offers music classes through Torrins Music as part of its co-curricular activities.",
 
    # ── Vision, Values & Motto ───────────────────────────────────────────────
    "what is the school motto": "The school motto is United We Stand, reflecting unity against injustice, parochialism and discrimination.",
    "what is the school slogan": "The school slogan is United We Stand.",
    "what are the core values of the school": "The school has 4 core values: Preferred Future, Zero Conflict World, Oxygenated Sphere, and Excellence All Around.",
    "what is the vision of the school": "The vision is to empower students with knowledge and skills through engaged learning, ensure pursuit of higher education of their choice, and make them custodians of their own physical, mental, emotional and spiritual well-being.",
    "what is the mission of the school": "The mission of KIS is to develop responsible global citizens and leaders through academic excellence and holistic development.",
    "what values does the school teach": "The school is committed to moral, spiritual and ethical development and preaches the philosophy of ahimsa (non-violence) and compassion, along with integrity, respect and discipline.",
 
    # ── Curriculum: Grade 1–3 ────────────────────────────────────────────────
    "what is taught in grade 1 to 3": "In Grade 1 to 3, subjects include English, Hindi, Mathematics, Environmental Studies and Computer Literacy, with focus on the 4 R's — Reading, Writing, Arithmetic and Discovery.",
    "what is the kid fit program": "KID-FIT is a physical education program with 250+ fun activities using props and music, targeting kids from Kindergarten to Grade 3. It develops gross motor skills, coordination, teamwork and healthy habits.",
    "what subjects are taught in primary school": "In primary grades (1–3), subjects include English, Hindi, Mathematics, Environmental Studies and Computer Literacy.",
 
    # ── Curriculum: Grade 4–10 ───────────────────────────────────────────────
    "what subjects are taught in grade 4 to 10": "Subjects include Communicative English, a second language (Hindi, French, German, Spanish or Sanskrit), Mathematics, Science and Technology, Social Science, Work Experience, Art Education, and Physical and Health Education.",
    "what second language options are available": "Students can choose Hindi, French, German, Spanish or Sanskrit as their second language.",
    "what is the assessment system": "The school follows Comprehensive Continuous Formative and Summative Assessments as per the CBSE pattern. Science practicals carry 40% weightage and Social Science and Math practicals carry 20% weightage.",
 
    # ── Curriculum: Grade 11–12 ──────────────────────────────────────────────
    "what streams are available in grade 11 and 12": "Three streams are available — Science, Commerce and Humanities.",
    "what subjects can be chosen in grade 11": "Students choose English (compulsory) plus four electives from Mathematics, Physics, Chemistry, Biology, History, Political Science, Economics, Psychology, Business Studies, Accountancy, Commercial Art, Home Science, Fashion Studies, Legal Studies, Computer Science, Physical Education, Vocal Music, Instrumental Music and Entrepreneurship.",
    "what is asl": "ASL stands for Assessment of Speaking and Listening, introduced by CBSE in 2013-14 to enhance English communication skills for students in Grades 9 to 11.",
    "how many students needed to start a subject": "A minimum of 8 students must opt for a subject for the school to offer it as a course in Grade 11-12.",
 
    # ── Kothari Group ─────────────────────────────────────────────────────────
    "what other schools are in kothari group": "The Kothari group includes KIS Noida, KIS Mumbai, Mansukhbhai Kothari National School Pune, Kothari Starz (Pune, Noida, Mumbai, Malad), Indrayu Academy Noida and KED American Academy.",
    "how many schools does kothari group have": "The Kothari group has multiple schools across India including campuses in Pune, Noida, Mumbai and Malad.",
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
