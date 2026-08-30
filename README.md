# HERCARE — AI-Powered Public Healthcare Navigation

A ready-to-run prototype based on the HERCARE concept:
- AI-assisted healthcare navigation without diagnosis
- Care category and urgency guidance
- Public facility matching
- Distance-aware matching when location is allowed
- Facility services, timings, accessibility and language information
- Visit preparation checklist
- Browser voice input
- Gemini integration with a safe demo fallback when no API key is configured

## 1. Install

Open this folder in VS Code, then open Terminal:

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Install packages:
```bash
pip install -r requirements.txt
```

## 2. Optional: enable Gemini

Create a `.env` file by copying `.env.example`, then put your Gemini API key in it:

```text
GEMINI_API_KEY=YOUR_KEY_HERE
```

If no key is present, HERCARE still runs using its local navigation demo logic.

## 3. Run

```bash
python app.py
```

Open:
http://127.0.0.1:5000

## 4. Prototype notes

The included facility dataset is demo data for a working prototype. For a production deployment, replace it with a verified government/public-health facility dataset and verified real-time service availability.

The application deliberately does not diagnose medical conditions. It is a navigation and preparation prototype.

## Suggested demo flow

1. Enter: "I have severe abdominal pain and need help finding a hospital."
2. Click "Find my care path".
3. Show urgency + care category.
4. Show recommended facilities.
5. Click "Use my location" to demonstrate distance matching.
6. Show the visit preparation checklist.
7. Click "Speak" to demonstrate voice input.

## Deploy publicly with Render

1. Upload this project to a GitHub repository.
2. In Render, create a new Web Service from that repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Choose the Free plan for a prototype.
6. In Render > Environment, add `GEMINI_API_KEY` with your Gemini API key.
7. Deploy. Render will provide a public `onrender.com` URL.

The included SQLite database is demo storage. Render Free services have an ephemeral filesystem, so SQLite data can reset after restarts/redeploys. For production, use a managed database.
