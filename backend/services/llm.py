import os
import json
from groq import Groq

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys"
            )
        _client = Groq(api_key=api_key)
    return _client


TRACK_PERSONAS = {
    "behavioral": (
        "You are a calm, experienced interviewer running a behavioral interview for a "
        "{role} role. Ask one question at a time. Use the STAR framework (Situation, "
        "Task, Action, Result) as your lens. When the candidate gives a vague or "
        "incomplete answer, ask a short, specific follow-up that targets the missing "
        "part (often the Result or the candidate's specific contribution). Keep your "
        "responses to one or two sentences. Never break character or mention you are an AI."
    ),
    "technical": (
        "You are a friendly but rigorous technical interviewer for a {role} role. The "
        "candidate is solving a coding problem in an editor. Ask about their approach, "
        "complexity, edge cases, and trade-offs. When they share code or an explanation, "
        "ask one focused follow-up question. Keep responses to one or two sentences. "
        "Never break character or mention you are an AI."
    ),
    "system-design": (
        "You are a senior engineer interviewing a candidate for a {role} role on system "
        "design. Probe their reasoning about scale, trade-offs, data models, and failure "
        "modes. Push back gently when they hand-wave a decision, asking 'why' or 'what "
        "happens if'. Keep responses to one or two sentences. Never break character or "
        "mention you are an AI."
    ),
}

OPENING_QUESTIONS = {
    "behavioral": "To get started, tell me about a time you disagreed with a decision made by your team and how you handled it.",
    "technical": "Let's start with a coding problem: given an array of integers, write a function that returns the two indices whose values sum to a target. Walk me through your approach before you start coding.",
    "system-design": "Let's design a URL shortener. Walk me through how you'd approach this, starting with the core requirements.",
}


def _system_prompt(track: str, role: str) -> str:
    persona = TRACK_PERSONAS.get(track, TRACK_PERSONAS["behavioral"])
    return persona.format(role=role)


def opening_question(track: str) -> str:
    return OPENING_QUESTIONS.get(track, OPENING_QUESTIONS["behavioral"])


def next_question(track: str, role: str, history: list[dict]) -> str:
    """history is a list of {role: 'interviewer'|'candidate', content: str}."""
    client = get_client()

    chat_messages = [{"role": "system", "content": _system_prompt(track, role)}]
    for turn in history:
        chat_role = "assistant" if turn["role"] == "interviewer" else "user"
        chat_messages.append({"role": chat_role, "content": turn["content"]})

    response = client.chat.completions.create(
        model=MODEL,
        messages=chat_messages,
        temperature=0.7,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


EVAL_SYSTEM_PROMPT = (
    "You are an interview coach reviewing a transcript of a mock {track} interview for a "
    "{role} role. Score the candidate from 1-10 on each of these categories: clarity, "
    "structure, and confidence. For technical or system-design tracks, also score "
    "'technical depth'. For each category, give a one-sentence reason. Then write a "
    "2-3 sentence overall summary with the single most useful thing to improve next time. "
    "Respond ONLY as JSON with this exact shape: "
    '{{"overall_score": <int 1-10>, "summary": "<string>", "evaluations": '
    '[{{"category": "<string>", "score": <int 1-10>, "feedback": "<string>"}}]}}'
)


def evaluate_session(track: str, role: str, history: list[dict]) -> dict:
    client = get_client()

    transcript = "\n".join(
        f"{'Interviewer' if t['role'] == 'interviewer' else 'Candidate'}: {t['content']}"
        for t in history
    )

    chat_messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT.format(track=track, role=role)},
        {"role": "user", "content": transcript or "The candidate did not answer any questions."},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=chat_messages,
        temperature=0.3,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "overall_score": 5,
            "summary": "We couldn't generate a detailed report this time, but your transcript has been saved.",
            "evaluations": [],
        }
