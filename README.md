# tailor-cvft

<p align="center">
  <strong>A local resume studio.</strong><br>
  Save a job. Tailor a CV. Track the application.<br>
  The model never leaves your machine.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-JSON%20API-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/UI-React%20%2B%20MUI-087EA4?style=for-the-badge&logo=react&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  <img alt="LLM" src="https://img.shields.io/badge/LLM-LM%20Studio%20or%20cloud-111111?style=for-the-badge">
  <img alt="Offline" src="https://img.shields.io/badge/data-stays%20on%20disk-8A4B08?style=for-the-badge">
</p>

---

**tailor-cvft** is a single-user web app for people who apply often and refuse to hand their CV to a cloud model.

You keep **one source-of-truth profile**. Under each **job description** you generate a tailored pack: Times-style CV, cover letter, and an honest match report. Companies and application status live next to the posting — Saved → Applied → Under consideration → Rejected / Declined.

The default LLM is [LM Studio](https://lmstudio.ai) on your machine. You can point the same OpenAI-compatible client at OpenAI, OpenRouter, Groq, xAI, or a custom `/v1` host via `.env`. Facts may be rephrased or reordered. They are not invented.

```
  Profile  +  Job posting  +  your notes
                 │
                 ▼
     LM Studio (host)  or  cloud /v1 API
                 │
                 ▼
     ┌───────────┼───────────┐
     ▼           ▼           ▼
   CV PDF    Cover letter   Match
```

## Why this shape

| You want | tailor-cvft does |
| --- | --- |
| One profile, many applications | Upload a CV once, edit it, reuse it |
| A CV that reads like *that* job | Build a pack under the position, not a generic rewrite |
| A paper look, not a SaaS card | Google-Doc-style Times layout: intro, technical skills, experience, education |
| Tracking without a CRM | Company records + application statuses on each role |
| Privacy | API key stays in `.env`. Local inference by default; a cloud provider sees profile + job text |

LinkedIn and some ATS pages block scraping. The job is still saved — paste the description and continue.

There are two UIs on the same API:

| URL | What |
| --- | --- |
| [http://127.0.0.1:5173](http://127.0.0.1:5173) | **React + Material UI** (use this) |
| [http://127.0.0.1:8000](http://127.0.0.1:8000) | Original Jinja pages (still work) |

The Times CV / cover letter preview is the same HTML on both. React embeds it; click-to-edit still saves on blur.

## Tour

```text
/jobs            Positions — add a posting, filter by status
/jobs/{id}       Source + status + Build tailored pack + results
/companies       Employers (created when you name a company)
/profile         Contact, experience, upload PDF / DOCX / TXT
/api/...         JSON for the React app (health, jobs, profile, companies)
/health          Liveness probe (used by Docker)
```

**Add a position** with company name, URL (optional), job description, required skills, desired skills, and notes.

**Statuses**

`Saved` → `Applied` → `Under consideration` → `Rejected` (they said no) or `Declined` (you said no)

## Run with Docker

Preferred if you already have [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Engine + Compose).

1. Start **Docker Desktop** so the daemon is up.
2. For the default local setup, in LM Studio: load a chat model, start the local server on port **1234**, and allow network / `0.0.0.0` (not only `127.0.0.1`). For a cloud API, set `LLM_PROVIDER`, `LLM_API_KEY`, and `LLM_MODEL` in `.env` instead.
3. From the repo:

```bash
cp .env.example .env
mkdir -p data
docker compose up --build
```

4. Open the React UI at [http://127.0.0.1:5173](http://127.0.0.1:5173). The API / Jinja pages stay at [http://127.0.0.1:8000](http://127.0.0.1:8000).

Compose starts both containers. Nginx on **5173** serves the built React app and proxies `/api`, `/static`, health, previews, and PDFs to `web`. Build-pack requests can take up to 10 minutes.

| Piece | Role |
| --- | --- |
| `Dockerfile` | Python 3.12 slim, installs `requirements.txt`, serves with uvicorn |
| `frontend/Dockerfile` | Node build of the Vite app, then nginx |
| `docker-compose.yml` | `web` on `8000`, `ui` on `5173`; mounts `./data` and `./app` on `web` |
| `.dockerignore` | Keeps `.venv`, `.git`, `data/`, `.env` out of the API image |

Compose **overrides** two values so the container works:

| Variable | In the container |
| --- | --- |
| `DATA_DIR` | `/data` (your `./data` folder) |
| `LLM_IN_DOCKER` | `1` — rewrites `127.0.0.1` to `host.docker.internal` for local providers only |

`localhost` inside the container is not your Mac. `host.docker.internal` is. Linux already has `extra_hosts: host.docker.internal:host-gateway` in the Compose file.

```bash
docker compose logs -f        # follow API + UI logs
docker compose down           # stop
docker compose up -d --build  # rebuild and run in the background
```

**Port 8000 or 5173 already in use?** Stop a local `uvicorn` or `npm run dev` first.

**Banner cannot reach LM Studio?** Confirm the model server is on `0.0.0.0:1234`, then:

```bash
docker compose exec web python -c "import httpx; print(httpx.get('http://host.docker.internal:1234/v1/models', timeout=3).status_code)"
```

You should see `200`.

## Run without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start LM Studio on `http://127.0.0.1:1234`, then:

```bash
uvicorn app.main:app --reload
```

The API is [http://127.0.0.1:8000](http://127.0.0.1:8000). LM Studio stays at `http://127.0.0.1:1234/v1` unless you set another provider in `.env`.

Then start the React UI (Vite, with hot reload):

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). With Docker you can skip this and use the `ui` container instead.

## First session

1. **Profile** — upload a CV or fill the form.
2. **Positions** — add the job.
3. Open the role → **Build tailored pack**.
4. Leave the tab open. Local models often take **3–10 minutes**.
5. Preview on the page. Click the intro, a CV bullet, or the cover letter to edit; **B** / **I** for bold and italic; click outside to save.
6. Download the CV / letter PDFs.

## LLM providers

All providers use the OpenAI-compatible SDK (`GET /v1/models`, `POST /v1/chat/completions`). Set them in `.env` and restart the API. There is no Settings UI yet.

| `LLM_PROVIDER` | Base URL | Key | Model |
| --- | --- | --- | --- |
| `lmstudio` (default) | `http://127.0.0.1:1234/v1` | optional (`lm-studio`) | empty → first loaded chat model |
| `openai` | `https://api.openai.com/v1` | required | required |
| `openrouter` | `https://openrouter.ai/api/v1` | required | required |
| `groq` | `https://api.groq.com/openai/v1` | required | required |
| `xai` | `https://api.x.ai/v1` | required | required |
| `custom` | `LLM_BASE_URL` (required) | optional | required unless the host is local |

`LLM_TIMEOUT` defaults to 600s for LM Studio and 120s for cloud. In Docker, a local `127.0.0.1` / `localhost` URL is rewritten to `host.docker.internal` so the container can reach LM Studio on the host. Cloud URLs are left alone.

A cloud provider **does** receive your profile and the job text. Keep keys in `.env` (gitignored).

Use the React app at **:5173** (API + Jinja at **:8000**). Opening **:1234** in a browser is LM Studio, not tailor-cvft.

On the tailored CV or cover letter, click to edit. **B** / **I** (or Ctrl/Cmd+B and Ctrl/Cmd+I) apply bold and italic. Click outside to save. Downloads pick up those edits.

## How tailoring is constrained

The system prompt is in [`app/services/llm.py`](app/services/llm.py).

- Only facts from your profile
- Skills grouped as **Languages / Databases / Frameworks / Technologies and Tools**
- Intro paragraph above Technical Skills
- Match report lists real gaps — it is not a pep talk

If JSON is cut off mid-stream (Gemma sometimes spends a minute reasoning first), the app tries to repair the object so a finished CV is not thrown away.

## Stack

```
FastAPI  →  JSON /api + Jinja pages + PDF
React + MUI (Vite)  →  product UI on :5173
SQLite (jobs, companies, generations)
profile.json + uploads under ./data   ← gitignored
fpdf2  →  Times New Roman PDF
httpx + trafilatura  →  job URL fetch
openai SDK  →  LM Studio or cloud /v1
Docker Compose  →  API (`web`) + React nginx (`ui`)
```

```
app/
  routers/     api · jobs · companies · profile
  services/    llm · scraper · pdf · parser · merge
  templates/   Jinja pages + Times CV / letter preview
  schemas.py   Profile, Position, Company, ApplicationStatus
frontend/      Vite + React + Material UI + nginx image
Dockerfile
docker-compose.yml
```

## Data

Everything stays in `./data` on your disk (bind-mounted when you use Compose).

| File | What |
| --- | --- |
| `resumeer.db` | companies, positions, generations (existing filename) |
| `profile.json` | your source CV |
| `uploads/` | files you imported |

That directory is gitignored. Do not commit a filled profile.

## License

Personal project. Use and fork as you like unless you add a license file later.
