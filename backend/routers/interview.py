import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from auth import AuthenticatedUser, get_current_user
from models import (
    BoilerplateResponse,
    EndSessionRequest,
    EndSessionResponse,
    MessageRequest,
    MessageResponse,
    QuestionContext,
    ResumeSessionResponse,
    RunTestsRequest,
    RunTestsResponse,
    SaveDiagramRequest,
    SessionSummary,
    StartSessionRequest,
    StartSessionResponse,
)
from services import (
    adhoc_harness,
    guardrail,
    harness_generator,
    llm,
    metrics,
    piston,
    question_bank,
    question_generator,
    test_runner,
)
from services.persistence import (
    persist_assigned_question,
    persist_diagram,
    persist_evaluation,
    persist_message,
    persist_session_start,
)
from services.rate_limit import check_rate_limit
from services.retry import with_retry
from services.session_guard import (
    check_idle_timeout,
    check_ownership,
    check_session_duration,
    check_session_limit,
    session_expires_at,
)
from services.session_store import SESSIONS, evict, get_session, now, session_lock
from services.supabase_client import get_supabase

router = APIRouter(prefix="/interview", tags=["interview"])

# How many times a candidate can ask for a different problem before being
# locked to the one they're on: the original assignment plus this many
# switches (2) gives 3 total questions per session. The 3rd switch attempt
# (which would produce a 4th question) is refused with QUESTION_LIMIT_MESSAGE
# instead of assigning anything new.
MAX_QUESTION_SWITCHES = 2

QUESTION_LIMIT_MESSAGE = (
    "You've reached your question limit for this session. Let's dig deeper into this one instead. "
    "What part of your current answer would you like to walk through?"
)


def _question_context(assigned: dict) -> QuestionContext:
    is_stdio = bool(assigned.get("tests") and "stdin" in assigned["tests"][0])
    return QuestionContext(
        id=assigned["id"],
        title=assigned.get("title", ""),
        difficulty=assigned.get("difficulty", ""),
        prompt=assigned.get("prompt", ""),
        constraints=assigned.get("constraints") or [],
        examples=assigned.get("examples") or [],
        is_stdio=is_stdio,
        scale_metadata=assigned.get("scale_metadata") or [],
        functional_requirements=assigned.get("functional_requirements") or [],
        non_functional_requirements=assigned.get("non_functional_requirements") or [],
        scaling_constraints=assigned.get("scaling_constraints") or [],
        out_of_scope=assigned.get("out_of_scope") or [],
    )


@router.post("/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest, user: AuthenticatedUser = Depends(get_current_user)):
    await run_in_threadpool(check_rate_limit, user.id)
    await run_in_threadpool(check_session_limit, user.id)

    session_id = str(uuid.uuid4())
    if req.job_description:
        # Run concurrently — both are independent LLM calls, so analyzing the
        # JD adds no extra latency to session start beyond whichever of the
        # two is slower.
        greeting, jd_analysis = await asyncio.gather(
            run_in_threadpool(llm.opening_message, req.track, req.role),
            run_in_threadpool(question_generator.analyze_job_description, req.job_description),
        )
    else:
        greeting = await run_in_threadpool(llm.opening_message, req.track, req.role)
        jd_analysis = None

    if req.seniority:
        # Candidate's explicit choice overrides both the JD's AI-inferred
        # seniority and role-string keyword matching — merged in once here so
        # every downstream consumer of session["jd_analysis"] (post_message,
        # question_bank, question_generator) picks it up for free via the
        # existing "jd_seniority takes precedence" pattern, with no signature
        # changes needed anywhere else.
        jd_analysis = {**(jd_analysis or {}), "seniority": req.seniority}

    started_at = now()
    SESSIONS[session_id] = {
        "track": req.track,
        "role": req.role,
        "history": [{"role": "interviewer", "content": greeting}],
        "user_id": user.id,
        "assigned_question": None,
        "next_sequence_no": 1,
        "last_activity_at": started_at,
        "created_at": started_at,
        "job_description": req.job_description or None,
        "jd_analysis": jd_analysis,
        "status": "active",
        "diagram_elements": [],
        "asked_question_ids": set(),
        "candidate_intro": "",
        "question_switch_count": 0,
        "last_sent_code": None,
    }
    metrics.SESSIONS_STARTED.labels(track=req.track).inc()

    await run_in_threadpool(
        persist_session_start, session_id, user.id, req.track, req.role, greeting,
        assigned_question_id=None,
    )

    expires_at = session_expires_at(SESSIONS[session_id])
    return StartSessionResponse(
        session_id=session_id, track=req.track, question=greeting,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
):
    sb = get_supabase()
    if not sb:
        return []
    resp = (
        sb.table("sessions")
        .select("id, track, role, overall_score, status, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []


@router.post("/message", response_model=MessageResponse)
async def post_message(req: MessageRequest, user: AuthenticatedUser = Depends(get_current_user)):
    await run_in_threadpool(check_rate_limit, user.id)

    async with session_lock(req.session_id):
        session = get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_ownership(session, user)
        check_idle_timeout(session)
        check_session_duration(session)

        candidate_content = req.message
        # Only embed the candidate's code in the transcript when it's real,
        # non-boilerplate work AND has actually changed since the last time it
        # was attached — the frontend already sends `code` on every single
        # turn (so a "Run" click's code shows up even without a fresh chat
        # message), which previously re-embedded an identical, unchanged code
        # block on every follow-up turn, bloating the transcript sent to the
        # LLM on every call for no new information (the model already has the
        # earlier turn with the same code in its conversation history).
        if req.code and req.code.strip() and req.code != session.get("last_sent_code"):
            lang_label = f" ({req.language})" if req.language else ""
            candidate_content += f"\n\n[Candidate's submitted code{lang_label}]\n```\n{req.code}\n```"
            session["last_sent_code"] = req.code

        is_first_reply = (
            session["track"] in ("technical", "system-design", "behavioral")
            and session.get("assigned_question") is None
        )
        # Technical and system-design only: the candidate can explicitly ask
        # for a different problem (e.g. "next question please", "can I get a
        # new problem"). The interviewer is otherwise hard-guardrailed against
        # ever introducing a second problem on its own (see
        # guardrail.sanitize_no_new_problem, which covers exactly these two
        # tracks) — the code editor/diagram grading are tied to exactly one
        # assigned question, so an uninvited switch would desync the
        # transcript from what's actually gradable. This is the one
        # deliberate, detectable exception: the candidate asking is a real
        # signal the guardrail itself can't distinguish from the LLM going
        # off script on its own. Behavioral is excluded — there's no
        # editor/diagram state tied to the assigned prompt to desync.
        switch_requested = (
            not is_first_reply
            and session["track"] in ("technical", "system-design")
            and session.get("assigned_question")
            and guardrail.candidate_requests_new_problem(req.message)
        )
        switch_limit_reached = bool(switch_requested) and session.get("question_switch_count", 0) >= MAX_QUESTION_SWITCHES
        wants_new_question = bool(switch_requested) and not switch_limit_reached

        session["history"].append({"role": "candidate", "content": candidate_content})
        # Persist the code-inclusive content (not just req.message) — the
        # transcript otherwise silently drops whatever the candidate had in
        # the editor when they sent this turn.
        await run_in_threadpool(persist_message, req.session_id, "candidate", candidate_content, session["next_sequence_no"])
        session["next_sequence_no"] += 1

        if is_first_reply:
            session["candidate_intro"] = req.message
            jd_analysis = session.get("jd_analysis")
            jd_seniority = (jd_analysis or {}).get("seniority")
            jd_topics = (jd_analysis or {}).get("topics")
            if session["track"] == "technical":
                session["assigned_question"] = await question_generator.select_or_generate_question(
                    session["role"], candidate_intro=req.message, jd_analysis=jd_analysis,
                )
            elif session["track"] == "system-design":
                session["assigned_question"] = await run_in_threadpool(
                    question_bank.pick_system_design_question, None, session["role"],
                    jd_seniority=jd_seniority, jd_topics=jd_topics,
                )
            else:
                session["assigned_question"] = await run_in_threadpool(
                    question_bank.pick_behavioral_question, None, None, session["role"],
                    jd_seniority=jd_seniority, jd_topics=jd_topics,
                )
            if session["assigned_question"]:
                session.setdefault("asked_question_ids", set()).add(session["assigned_question"]["id"])
                await run_in_threadpool(persist_assigned_question, req.session_id, session["assigned_question"]["id"])
        elif wants_new_question:
            exclude_ids = session.get("asked_question_ids") or set()
            if session["track"] == "technical":
                new_question = await question_generator.select_or_generate_question(
                    session["role"], candidate_intro=session.get("candidate_intro", ""), exclude_ids=exclude_ids,
                    jd_analysis=session.get("jd_analysis"),
                )
            else:
                jd_analysis = session.get("jd_analysis")
                new_question = await run_in_threadpool(
                    question_bank.pick_system_design_question, None, session["role"],
                    (jd_analysis or {}).get("seniority"), (jd_analysis or {}).get("topics"), exclude_ids,
                )
            if new_question:
                session["assigned_question"] = new_question
                session.setdefault("asked_question_ids", set()).add(new_question["id"])
                session["question_switch_count"] = session.get("question_switch_count", 0) + 1
                await run_in_threadpool(persist_assigned_question, req.session_id, new_question["id"])
            else:
                wants_new_question = False  # bank exhausted — fall back to a normal follow-up turn

        if switch_limit_reached:
            # Deterministic, no LLM call: this is a hard session rule, not a
            # conversational judgment call, so it must never drift or vary
            # with model phrasing — same reasoning as the guardrail's
            # pre-written safe-fallback question (see services/guardrail.py).
            question = QUESTION_LIMIT_MESSAGE
        else:
            question = await run_in_threadpool(
                llm.next_question, session["track"], session["role"], session["history"],
                session.get("assigned_question"), session.get("job_description"), is_first_reply or wants_new_question,
                is_question_swap=wants_new_question,
            )

        session["history"].append({"role": "interviewer", "content": question})
        await run_in_threadpool(persist_message, req.session_id, "interviewer", question, session["next_sequence_no"])
        session["next_sequence_no"] += 1
        session["last_activity_at"] = now()

    ctx = (
        _question_context(session["assigned_question"])
        if (is_first_reply or wants_new_question) and session.get("assigned_question")
        else None
    )
    return MessageResponse(question=question, question_context=ctx)


@router.get("/{session_id}/boilerplate", response_model=BoilerplateResponse)
async def get_boilerplate(session_id: str, language: str, user: AuthenticatedUser = Depends(get_current_user)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    check_ownership(session, user)

    assigned = session.get("assigned_question")
    if not assigned:
        bank_lang = "cpp" if language == "gcc" else language
        if bank_lang in ("java", "cpp"):
            problem = test_runner._extract_problem(session["history"])
            cases = test_runner.get_or_generate_cases(problem) if problem else None
            if cases:
                signature = await adhoc_harness.get_or_generate_signature(bank_lang, problem, cases)
                return BoilerplateResponse(boilerplate=signature, supported=bool(signature))
        return BoilerplateResponse(boilerplate=None, supported=True)

    is_stdio = bool(assigned.get("tests") and "stdin" in assigned["tests"][0])
    bank_lang = "cpp" if language == "gcc" else language
    allowed = set(assigned.get("languages") or [])
    if "cpp" in allowed:
        allowed.add("gcc")

    if is_stdio:
        return BoilerplateResponse(boilerplate=None, supported=True)

    if bank_lang in (assigned.get("languages") or []):
        signature = await harness_generator.get_or_generate_signature(assigned, bank_lang)
        return BoilerplateResponse(boilerplate=signature, supported=True)

    if bank_lang == "node":
        # JS doesn't need a full test-runner harness like Java/C++ — the same
        # signature-only generator works regardless of whether the bank entry
        # already lists node, unlike the harness path below. Previously this
        # fell through to "unsupported" unconditionally for every question
        # that didn't already list node natively (nearly all of them, since
        # most imports are Python-only) — Node was never actually attempted.
        signature = await harness_generator.get_or_generate_signature(assigned, bank_lang)
        return BoilerplateResponse(boilerplate=signature, supported=bool(signature))

    if bank_lang not in ("java", "cpp"):
        return BoilerplateResponse(boilerplate=None, supported=False)

    harness_data = await harness_generator.get_or_generate(assigned, bank_lang)
    if not harness_data:
        return BoilerplateResponse(boilerplate=None, supported=False)
    return BoilerplateResponse(boilerplate=harness_data["boilerplate"], supported=True)


@router.get("/{session_id}/resume", response_model=ResumeSessionResponse)
async def resume_session(session_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    check_ownership(session, user)
    if session.get("status") != "active":
        raise HTTPException(status_code=409, detail="Session is no longer active")

    # Resuming is itself activity — without this, a session that sat idle
    # past SESSION_IDLE_TIMEOUT_MINUTES before being resumed would trip the
    # idle-timeout check on the very next message, immediately after the
    # candidate just resumed it.
    session["last_activity_at"] = now()

    ctx = _question_context(session["assigned_question"]) if session.get("assigned_question") else None
    expires_at = session_expires_at(session)
    return ResumeSessionResponse(
        session_id=session_id,
        track=session["track"],
        history=[{"role": m["role"], "content": m["content"]} for m in session["history"]],
        question_context=ctx,
        diagram_elements=session.get("diagram_elements") or [],
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.post("/diagram")
async def save_diagram(req: SaveDiagramRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Autosave endpoint for the system-design board — called debounced from
    the frontend while the candidate draws, so a refresh/resume restores the
    diagram along with the conversation instead of only the conversation."""
    await run_in_threadpool(check_rate_limit, user.id, max_per_minute=30)

    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    check_ownership(session, user)

    session["diagram_elements"] = req.elements
    await run_in_threadpool(persist_diagram, req.session_id, req.elements)
    return {"saved": True}


@router.post("/code/test", response_model=RunTestsResponse)
async def run_tests(req: RunTestsRequest, user: AuthenticatedUser = Depends(get_current_user)):
    await run_in_threadpool(check_rate_limit, user.id, max_per_minute=20)

    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    check_ownership(session, user)

    assigned = session.get("assigned_question")
    bank_lang = "cpp" if req.language == "gcc" else req.language
    is_stdio = bool(assigned and assigned.get("tests") and "stdin" in assigned["tests"][0])

    if is_stdio:
        return RunTestsResponse(**await _run_stdio(req, assigned))
    if assigned and bank_lang in ("java", "cpp"):
        # Always prefer the curated bank's own harness path for java/cpp when a
        # bank question is assigned — get_or_generate checks its Supabase cache
        # first, so an already-verified harness (whether the question lists
        # java/cpp natively in "languages" or only has it via generated
        # "harnesses") is served instantly instead of falling through to the
        # ad-hoc (re-generate-from-scratch) path below, which doesn't know
        # about this question's own pre-verified test data at all.
        return RunTestsResponse(**await _run_generated_harness(req, assigned, bank_lang))
    return RunTestsResponse(**await _run_call_expected(req, session, assigned))


async def _run_stdio(req: RunTestsRequest, assigned: dict) -> dict:
    return await test_runner.run_stdio_tests(
        req.language, req.version, req.source,
        assigned["tests"], assigned.get("visible_count", 3),
    )


async def _run_generated_harness(req: RunTestsRequest, assigned: dict, bank_lang: str) -> dict:
    harness_data = await harness_generator.get_or_generate(assigned, bank_lang)
    if not harness_data:
        return _error_response(
            f"Couldn't auto-generate a verified {req.language} harness for this problem. "
            "Switch to Python or JavaScript, or try again — harness generation uses the LLM "
            "and occasionally fails on first attempt.",
            "transient",
        )
    full_source = harness_generator.merge_sources(bank_lang, [req.source, harness_data["harness"]])
    result = await piston.run_code(req.language, req.version, full_source, stdin="")
    raw = result.get("run", {})
    return test_runner.parse_results(raw.get("stdout", ""), raw.get("stderr", ""))


async def _run_call_expected(req: RunTestsRequest, session: dict, assigned: dict | None) -> dict:
    bank_lang = "cpp" if req.language == "gcc" else req.language
    if bank_lang in ("java", "cpp"):
        return await _run_adhoc_compiled(req, session, bank_lang)

    harness = test_runner.generate_harness(
        req.language, req.source, session["history"],
        assigned_question=session.get("assigned_question"),
    )
    if harness is None:
        # bank_lang in ("java", "cpp") already returned above via
        # _run_adhoc_compiled, so req.language here is always python/node —
        # generate_harness() itself now raises ValueError for anything else,
        # so a None here can only mean "no problem assigned".
        return _error_response(
            "No coding problem has been assigned yet — wait for the interviewer to give you a problem first.",
            "permanent",
        )
    result = await piston.run_code(req.language, req.version, harness)
    raw = result.get("run", {})
    return test_runner.parse_results(raw.get("stdout", ""), raw.get("stderr", ""))


async def _run_adhoc_compiled(req: RunTestsRequest, session: dict, bank_lang: str) -> dict:
    """Java/C++ test running for problems the interviewer invented ad hoc
    (not from the curated bank) — mirrors _run_generated_harness, but keyed
    by problem text via services.adhoc_harness instead of a bank question id."""
    problem = test_runner._extract_problem(session["history"])
    if not problem:
        return _error_response(
            "No coding problem has been assigned yet — wait for the interviewer to give you a problem first.",
            "permanent",
        )
    cases = test_runner.get_or_generate_cases(problem)
    if not cases:
        return _error_response(
            "Couldn't generate test cases for this problem. Try again in a moment.", "transient",
        )
    harness_data = await adhoc_harness.get_or_generate(bank_lang, problem, cases)
    if not harness_data:
        return _error_response(
            f"Couldn't auto-generate a verified {req.language} harness for this problem. "
            "Switch to Python or JavaScript, or try again — harness generation uses the LLM "
            "and occasionally fails on first attempt.",
            "transient",
        )
    full_source = harness_generator.merge_sources(bank_lang, [req.source, harness_data["harness"]])
    result = await piston.run_code(req.language, req.version, full_source, stdin="")
    raw = result.get("run", {})
    return test_runner.parse_results(raw.get("stdout", ""), raw.get("stderr", ""))


def _error_response(message: str, error_type: str) -> dict:
    return {
        "status": "compile_error",
        "compile_error": message,
        "error_type": error_type,
        "visible_tests": [], "hidden_tests": [], "passed": 0, "total": 0,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    session = get_session(session_id)
    if session:
        check_ownership(session, user)

    evict(session_id)

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Storage unavailable, session was not deleted")

    async def _delete(table: str, column: str) -> None:
        # Retried — a bulk "delete all" fires many of these concurrently, and
        # a single transient network hiccup shouldn't surface as a 500 for a
        # request that would have succeeded on retry.
        await with_retry(
            lambda: run_in_threadpool(lambda: sb.table(table).delete().eq(column, session_id).execute()),
            attempts=3, base_delay=0.5, label=f"delete_session.{table}",
        )

    await _delete("evaluations", "session_id")
    await _delete("messages", "session_id")
    await _delete("analytics_events", "session_id")
    await _delete("sessions", "id")
    return {"deleted": session_id}


@router.post("/end", response_model=EndSessionResponse)
async def end_session(req: EndSessionRequest, user: AuthenticatedUser = Depends(get_current_user)):
    async with session_lock(req.session_id):
        session = get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        check_ownership(session, user)

        has_candidate_answer = any(t["role"] == "candidate" for t in session["history"])
        if not has_candidate_answer:
            empty_result = {
                "overall_score": 0,
                "summary": "No answers were recorded in this session. Start a new session and answer at least one question to receive a score.",
                "evaluations": [],
            }
            await run_in_threadpool(persist_evaluation, req.session_id, empty_result)
            session["status"] = "completed"
            metrics.SESSIONS_COMPLETED.labels(track=session["track"]).inc()
            metrics.EVALUATION_SCORE.labels(track=session["track"]).observe(0)
            return EndSessionResponse(overall_score=0, summary=empty_result["summary"], evaluations=[])

        result = await run_in_threadpool(llm.evaluate_session, session["track"], session["role"], session["history"])

        # For system-design sessions: score the candidate's diagram separately
        diagram_eval = None
        assigned = session.get("assigned_question")
        if session["track"] == "system-design" and assigned and assigned.get("expected_components"):
            diagram_eval = await run_in_threadpool(
                llm.evaluate_diagram, session["history"], assigned, session.get("diagram_elements"),
            )
            result["diagram_evaluation"] = diagram_eval

        await run_in_threadpool(persist_evaluation, req.session_id, result)
        session["status"] = "completed"
        metrics.SESSIONS_COMPLETED.labels(track=session["track"]).inc()
        metrics.EVALUATION_SCORE.labels(track=session["track"]).observe(result.get("overall_score", 5))

    return EndSessionResponse(
        overall_score=result.get("overall_score", 5),
        summary=result.get("summary", ""),
        star_analysis=result.get("star_analysis"),
        evaluations=result.get("evaluations", []),
        diagram_evaluation=diagram_eval,
    )
