# Greenroom

Greenroom is a voice-based AI mock interview platform. Candidates pick a track
(behavioral, technical, or system design), talk through their answers out
loud, and get a structured feedback report afterwards. The entire stack runs
on free or generous free-tier services.

## Stack

| Piece | Service | Notes |
|---|---|---|
| Frontend | React + Vite + Tailwind | Deploys free on Vercel/Netlify |
| Speech-to-text | Web Speech API | Built into Chrome/Edge, no key needed |
| Text-to-speech | edge-tts (backend) | Free, uses Microsoft Edge neural voices |
| LLM (interviewer + scoring) | Groq API (Llama 3.3 70B) | Free tier, generous rate limits |
| Code execution | Piston public API | Open source, no key needed |
| Auth + database | Supabase | Free tier: Postgres + Auth |
| Backend | FastAPI | Deploys free on Render/Fly.io |

## 1. Set up Supabase

1. Create a free project at https://supabase.com.
2. Open the SQL editor and run `supabase/schema.sql`.
3. Go to Project Settings -> API and copy:
   - `Project URL`
   - `anon` public key (for the frontend)
   - `service_role` key (for the backend - keep secret)

## 2. Get a free Groq API key

1. Create an account at https://console.groq.com.
2. Generate an API key under "API Keys". This powers both the interviewer
   dialogue and the post-session evaluation.

## 3. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your Groq key and Supabase service role key
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000/api`.

## 4. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
# edit .env with your Supabase URL and anon key
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` requests to
the backend on port 8000.

## How a session works

1. The candidate picks a track from the dashboard and starts a session.
2. The backend creates a session, asks Groq for an opening question, and
   saves the session + first message to Supabase.
3. The candidate records their answer with the Web Speech API (or types it),
   and sends it. The backend appends it to the conversation, asks Groq for a
   follow-up question shaped by the candidate's actual answer, and saves
   both turns.
4. For the technical track, the candidate writes code in a Monaco editor and
   runs it via Piston; output is shown inline.
5. When the candidate ends the session, the backend sends the full transcript
   to Groq for scoring (clarity, structure, confidence, and technical depth
   where relevant), saves the scores and summary, and the frontend shows the
   report on the Results page.

## Deploying for free

- **Frontend**: push to GitHub, import the repo on Vercel or Netlify, set the
  build command to `npm run build` and the output directory to `dist`. Add
  the `VITE_*` environment variables in the project settings.
- **Backend**: deploy on Render's free web service tier (or Fly.io). Set the
  start command to `uvicorn main:app --host 0.0.0.0 --port $PORT` and add the
  environment variables from `.env.example`. Update `ALLOWED_ORIGINS` to your
  deployed frontend URL.
- **Database/auth**: Supabase's free tier covers this; no extra setup needed
  beyond what's in step 1.

## Notes and next steps

- The backend keeps active conversation state in memory (`SESSIONS` dict in
  `routers/interview.py`). This is fine for a single instance; for multi
  instance deployments, move this to Redis or rehydrate from the `messages`
  table in Supabase.
- The public Piston instance is rate-limited. For heavier usage, self-host
  Piston with Docker (see https://github.com/engineer-man/piston) and point
  `PISTON_URL` in `backend/services/piston.py` at your instance.
- A "Pro" tier is sketched on the landing page but not wired up. When you're
  ready to monetize, Stripe Checkout is the lowest-friction way to add a paid
  plan without any upfront cost.
- Speech recognition via the Web Speech API requires Chrome, Edge, or another
  Chromium-based browser, and a secure (HTTPS) context in production.
