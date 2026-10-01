# RoleSync AI — Hackathon Edition

**AI Resume Matching · ATS Intelligence · Multi-Template Builder · Role-Specific Mock Interview**

## What makes this version demo-ready
- PDF/DOCX/TXT resume parsing
- Real semantic similarity with Sentence Transformers when available, with a deterministic fallback
- Job-specific skill gaps, keyword coverage and ATS breakdown
- Selectable AI recommendations: the user chooses what to apply before optimization
- AI optimization with Gemini when `GEMINI_API_KEY` is configured; safe deterministic fallback otherwise
- Before/after match + ATS scores
- Four DOCX resume templates: Minimal ATS, Modern Blue, Executive, Tech Slate
- Separate structured resume builder with template switching
- Mock interview based on the actual resume + target JD
- Four interview stages: Introduction, Resume Deep Dive, Technical, Behavioral/System Design
- Technical questions can target skills such as SQL, MongoDB, Python, FastAPI, AWS, Docker and Kubernetes when relevant
- Per-answer evaluation + final score out of 100
- LAN-ready frontend/backend configuration for teammates

## Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python run.py
```
Backend: `http://localhost:8000/docs`

For LAN sharing, `run.py` binds to `0.0.0.0:8000`.

## Frontend
```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```
Set `frontend/.env`:
```env
VITE_API_URL=http://YOUR_LAPTOP_IP:8000
```
Then teammates open `http://YOUR_LAPTOP_IP:5173` on the same Wi-Fi.

## Optional Gemini
Create `backend/.env` from `.env.example` and set `GEMINI_API_KEY`. Never commit or share the key. The product still works without Gemini using deterministic interview generation/evaluation and safe optimization fallbacks.

## Demo flow
1. Load Demo
2. Analyze Match
3. Show Role Match / ATS / Semantic Match / Keywords
4. Show matched skills + skill gaps
5. Select 2–4 recommendations
6. Optimize Resume
7. Show before/after scores
8. Download multiple templates
9. Open Mock Interview
10. Complete 8–10 questions across four rounds
11. Show final interview score and per-round breakdown

## Important product rule
The optimizer is instructed not to invent skills, employers, dates, metrics, certifications or achievements. Missing skills should be added only when the candidate genuinely has them.
