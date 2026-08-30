import os, json, math, sqlite3
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "hercare.db")

FACILITIES = [
    ("Safdarjung Hospital", "Government Medical College / Tertiary Hospital", "New Delhi",
     "Women's health, emergency care, gynecology, obstetrics, general medicine, diagnostics",
     "24/7 Emergency; OPD Mon-Sat 8:30 AM-1:00 PM", "Wheelchair access, ramps, accessible toilets",
     "Hindi, English", 28.5685, 77.2074, "Available"),
    ("Lady Hardinge Medical College & Associated Hospitals", "Government Medical College",
     "New Delhi", "Women's health, gynecology, obstetrics, pediatrics, diagnostics",
     "24/7 Emergency; OPD Mon-Sat", "Wheelchair access, ramps, lift",
     "Hindi, English", 28.6355, 77.2249, "Available"),
    ("Dr. Baba Saheb Ambedkar Hospital", "Government Hospital", "Rohini",
     "Emergency care, gynecology, obstetrics, general medicine, diagnostics",
     "24/7 Emergency; OPD Mon-Sat", "Wheelchair access, ramps, lift",
     "Hindi, English", 28.7280, 77.1070, "Available"),
    ("Deen Dayal Upadhyay Hospital", "Government Hospital", "Hari Nagar",
     "Emergency care, gynecology, obstetrics, general medicine, diagnostics",
     "24/7 Emergency; OPD Mon-Sat", "Wheelchair access, ramps, accessible toilets",
     "Hindi, English", 28.6288, 77.1077, "Limited"),
    ("Guru Tegh Bahadur Hospital", "Government Teaching Hospital", "Dilshad Garden",
     "Emergency care, women's health, gynecology, obstetrics, diagnostics",
     "24/7 Emergency; OPD Mon-Sat", "Wheelchair access, ramps, lift",
     "Hindi, English", 28.6880, 77.3160, "Available"),
    ("Rao Tula Ram Memorial Hospital", "Government Hospital", "Jaffarpur",
     "Women's health, obstetrics, gynecology, general medicine",
     "24/7 Emergency; OPD Mon-Sat", "Wheelchair access, ramps",
     "Hindi, English", 28.6077, 76.9540, "Available"),
]

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, area TEXT,
        services TEXT, timings TEXT, accessibility TEXT, languages TEXT,
        lat REAL, lon REAL, status TEXT)""")
    cur.execute("SELECT COUNT(*) FROM facilities")
    if cur.fetchone()[0] == 0:
        cur.executemany("""INSERT INTO facilities
            (name,type,area,services,timings,accessibility,languages,lat,lon,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", FACILITIES)
    con.commit()
    con.close()

def get_facilities():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("SELECT * FROM facilities").fetchall()]
    con.close()
    return rows

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def analyze_demo(text):
    t = text.lower()
    emergency_words = ["severe", "unconscious", "fainting", "heavy bleeding", "chest pain",
                       "difficulty breathing", "breathing problem", "seizure", "accident",
                       "very heavy", "cannot breathe", "loss of consciousness"]
    gyn_words = ["period", "menstrual", "pregnan", "pregnancy", "bleeding", "pelvic",
                 "abdominal", "ovulation", "pcos", "gyne", "vaginal", "breast", "delivery"]
    if any(x in t for x in emergency_words):
        urgency = "Urgent"
        note = "Your description may require prompt medical assessment. If this is a life-threatening emergency, use emergency services immediately."
    elif any(x in t for x in gyn_words):
        urgency = "Soon"
        note = "A women's-health or general hospital service may be appropriate. HERCARE does not diagnose conditions."
    else:
        urgency = "Routine"
        note = "A primary-care or general medical consultation may be a suitable next step. HERCARE does not diagnose conditions."
    category = "Women's health / general care" if any(x in t for x in gyn_words) else "General medical care"
    return {"category": category, "urgency": urgency, "summary": "Care navigation guidance based on the concern provided.", "note": note}

def analyze_with_gemini(text):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return analyze_demo(text), "demo"
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        prompt = f"""You are HERCARE, a healthcare navigation assistant, not a doctor.
Analyze the user's concern ONLY for care navigation. Never diagnose, prescribe, or claim a disease.
Return JSON only with:
category (short string), urgency (one of Routine, Soon, Urgent), summary (one sentence),
note (short safety-aware guidance).
If there are signs of a possible emergency, say prompt/emergency assessment may be needed.
User concern: {text}"""
        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        data = json.loads(response.text)
        return data, "gemini"
    except Exception:
        return analyze_demo(text), "demo"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/facilities")
def facilities():
    return jsonify(get_facilities())

@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Please describe your concern."}), 400
    analysis, source = analyze_with_gemini(text)
    return jsonify({"analysis": analysis, "source": source})

@app.route("/api/match", methods=["POST"])
def match():
    payload = request.get_json(silent=True) or {}
    lat = payload.get("lat")
    lon = payload.get("lon")
    concern = (payload.get("concern") or "").lower()
    facilities = get_facilities()

    def score(f):
        s = 0
        if lat is not None and lon is not None:
            d = haversine(float(lat), float(lon), f["lat"], f["lon"])
            s += max(0, 50 - d * 8)
        else:
            d = None
            s += 20
        women_terms = ["women", "gyne", "obstetric", "pregnan", "menstrual", "breast", "pelvic"]
        if any(x in concern for x in women_terms):
            if any(x in f["services"].lower() for x in ["women", "gynecology", "obstetrics"]):
                s += 30
        if f["status"] == "Available":
            s += 10
        return s, d

    ranked = []
    for f in facilities:
        sc, dist = score(f)
        f["distance_km"] = round(dist, 1) if dist is not None else None
        ranked.append((sc, f))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return jsonify([f for _, f in ranked[:4]])

@app.route("/api/checklist", methods=["POST"])
def checklist():
    payload = request.get_json(silent=True) or {}
    category = (payload.get("category") or "").lower()
    common = ["Government ID / required identification", "Previous prescriptions or medical records", "Current medicines list", "Any relevant test reports"]
    questions = ["What should I do next?", "What follow-up is recommended?", "What warning signs should make me seek urgent care?"]
    if "women" in category:
        common += ["Relevant menstrual/pregnancy history if applicable"]
        questions += ["Which women's-health services are available here?"]
    return jsonify({"documents": common, "questions": questions})

init_db()

if __name__ == "__main__":
    app.run(debug=True)
