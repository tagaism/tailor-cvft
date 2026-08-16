# Resum<span>eer</span>

<p align="center">
  <strong>A local resume studio.</strong><br>
  Save a job. Tailor a CV. Track the application.<br>
  The model never leaves your machine.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Jinja2-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img alt="LM Studio" src="https://img.shields.io/badge/LLM-LM%20Studio%20local-111111?style=for-the-badge">
  <img alt="Offline" src="https://img.shields.io/badge/data-stays%20on%20disk-8A4B08?style=for-the-badge">
</p>

---

Resumeer is a single-user web app for people who apply often and refuse to hand their CV to a cloud model.

You keep **one source-of-truth profile**. Under each **job description** you generate a tailored pack: Times-style CV, cover letter, and an honest match report. Companies and application status live next to the posting — Saved → Applied → Under consideration → Rejected / Declined.

The LLM is [LM Studio](https://lmstudio.ai) on `localhost`. Facts may be rephrased or reordered. They are not invented.

```
  Profile  +  Job posting  +  your notes
                 │
                 ▼
         LM Studio (local)
                 │
                 ▼
     ┌───────────┼───────────┐
     ▼           ▼           ▼
   CV PDF    Cover letter   Match
```

## Why this shape

| You want | Resumeer does |
| --- | --- |
| One profile, many applications | Upload a CV once, edit it, reuse it |
| A CV that reads like *that* job | Build a pack under the position, not a generic rewrite |
| A paper look, not a SaaS card | Google-Doc-style Times layout: intro, technical skills, experience, education |
| Tracking without a CRM | Company records + application statuses on each role |
| Privacy | API key stays in `.env`. Inference is local |

LinkedIn and some ATS pages block scraping. The job is still saved — paste the description and continue.

## Tour

```text
/jobs            Positions — add a posting, filter by status
/jobs/{id}       Source + status + Build tailored pack + results
/companies       Employers (created when you name a company)
/profile         Contact, experience, upload PDF / DOCX / TXT
```

**Add a position** with company name, URL (optional), job description, required skills, desired skills, and notes.

**Statuses**

`Saved` → `Applied` → `Under consideration` → `Rejected` (they said no) or `Declined` (you said no)

## Quick start

```bash
git clone <your-remote> resumeer
cd resumeer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start LM Studio, load a chat model, turn on the local server (**Developer** tab, port `1234`).

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

1. **Profile** — upload a CV or fill the form.
2. **Positions** — add the job.
3. Open the role → **Build tailored pack**.
4. Leave the tab open. Local models often take **3–10 minutes**.
5. Preview on the page, then download the CV / letter PDFs.

## LM Studio

| Setting | Default |
| --- | --- |
| `LLM_BASE_URL` | `http://127.0.0.1:1234/v1` |
| `LLM_API_KEY` | `lm-studio` (SDK needs a string; LM Studio ignores it unless you set a token) |
| `LLM_MODEL` | empty → first chat model from `GET /v1/models` |
| `LLM_TIMEOUT` | `600` seconds |

OpenAI-compatible calls:

- `GET /v1/models`
- `POST /v1/chat/completions`

Use the app at **:8000**. Opening **:1234** in a browser is the model server, not Resumeer.

## How tailoring is constrained

The system prompt is in [`app/services/llm.py`](app/services/llm.py).

- Only facts from your profile
- Skills grouped as **Languages / Databases / Frameworks / Technologies and Tools**
- Intro paragraph above Technical Skills
- Match report lists real gaps — it is not a pep talk

If JSON is cut off mid-stream (Gemma sometimes spends a minute reasoning first), the app tries to repair the object so a finished CV is not thrown away.

## Stack

```
FastAPI + Jinja2 + vanilla CSS
SQLite (jobs, companies, generations)
profile.json + uploads under ./data   ← gitignored
fpdf2  →  Times New Roman PDF
httpx + trafilatura  →  job URL fetch
openai SDK  →  LM Studio /v1
```

```
app/
  routers/     jobs · companies · profile
  services/    llm · scraper · pdf · parser · merge
  templates/   positions, companies, profile, CV preview
  cv_layout.py skill groups + contact line
  schemas.py   Profile, Position, Company, ApplicationStatus
```

## Data

Everything stays in `./data` on your disk.

| File | What |
| --- | --- |
| `resumeer.db` | companies, positions, generations |
| `profile.json` | your source CV |
| `uploads/` | files you imported |

That directory is gitignored. Do not commit a filled profile.

## License

Personal project. Use and fork as you like unless you add a license file later.
