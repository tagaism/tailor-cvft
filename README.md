# Resumeer

A local, single-user resume builder. You save **job descriptions**, then build a tailored CV, cover letter, and match analysis under each one. The LLM runs in [LM Studio](https://lmstudio.ai) on your machine.

## What it does

1. Keep one personal profile (or seed it by uploading a PDF/DOCX/TXT CV).
2. Add a job from a company careers URL or a pasted LinkedIn posting.
3. Build a tailored pack: ATS-friendly CV preview + PDF, cover letter, and an honest match report.

Facts stay grounded in your profile. The model may rephrase, reorder, and drop irrelevant bullets — it is instructed not to invent jobs, dates, degrees, or metrics.

LinkedIn and some ATS pages block scraping. If the fetch is thin, the job is still saved; paste the posting text and continue.

## Setup

```bash
cd resumeer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

PDF export uses `fpdf2` (no extra system libraries). The on-screen preview is HTML/CSS.

## Run LM Studio

1. Open LM Studio and load a model.
2. Developer tab → start the local server (default `http://127.0.0.1:1234`).
3. Optional: set `LLM_MODEL` in `.env` to a specific model id. Leave it empty to use the first model LM Studio reports.

The OpenAI-compatible base URL is `http://127.0.0.1:1234/v1`. `LLM_API_KEY` defaults to `lm-studio` (the SDK needs a string; LM Studio ignores it unless you set a token).

## Start the app

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Layout

- `/jobs` — job descriptions (home)
- `/jobs/new` — URL + notes + optional pasted JD
- `/jobs/{id}` — source, **Build tailored pack**, then analysis / CV / letter
- `/profile` — editable profile + CV upload

Data stays in `./data` (SQLite, `profile.json`, uploads). That folder is gitignored.
