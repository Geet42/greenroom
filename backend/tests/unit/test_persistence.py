"""Unit tests for the Supabase write path in services/persistence.py.

persist_analytics_event is already covered in test_analytics.py; this file
covers the rest of the persist_* functions: persist_session_start,
persist_assigned_question, persist_diagram, persist_message, and
persist_evaluation.
"""
from unittest.mock import MagicMock, patch

from services import persistence


def _mock_supabase():
    """A MagicMock whose .table(...).insert(...).execute() / .update(...).eq(...).execute()
    chains all just return further mocks, so assertions can inspect call args."""
    return MagicMock()


# --- persist_session_start ------------------------------------------------

def test_persist_session_start_noop_when_supabase_unconfigured():
    with patch.object(persistence, "get_supabase", return_value=None):
        persistence.persist_session_start(
            "sess-1", "user-1", "behavioral", "Backend Engineer", "Tell me about yourself", None,
        )  # should not raise


def test_persist_session_start_inserts_session_and_opening_message():
    sb = _mock_supabase()
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_session_start(
            "sess-1", "user-1", "behavioral", "Backend Engineer", "Tell me about yourself",
            assigned_question_id="q-42",
        )

    session_call = sb.table.call_args_list[0]
    assert session_call.args == ("sessions",)
    session_payload = sb.table.return_value.insert.call_args_list[0].args[0]
    assert session_payload["id"] == "sess-1"
    assert session_payload["user_id"] == "user-1"
    assert session_payload["track"] == "behavioral"
    assert session_payload["role"] == "Backend Engineer"
    assert session_payload["status"] == "active"
    assert session_payload["assigned_question_id"] == "q-42"

    message_call = sb.table.call_args_list[1]
    assert message_call.args == ("messages",)
    message_payload = sb.table.return_value.insert.call_args_list[1].args[0]
    assert message_payload["session_id"] == "sess-1"
    assert message_payload["role"] == "interviewer"
    assert message_payload["content"] == "Tell me about yourself"
    assert message_payload["sequence_no"] == 0


# --- persist_assigned_question ------------------------------------------------

def test_persist_assigned_question_noop_when_supabase_unconfigured():
    with patch.object(persistence, "get_supabase", return_value=None):
        persistence.persist_assigned_question("sess-1", "q-1")  # should not raise


def test_persist_assigned_question_updates_expected_row():
    sb = _mock_supabase()
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_assigned_question("sess-1", "q-1")
    sb.table.assert_called_once_with("sessions")
    sb.table.return_value.update.assert_called_once_with({"assigned_question_id": "q-1"})
    sb.table.return_value.update.return_value.eq.assert_called_once_with("id", "sess-1")


# --- persist_diagram ------------------------------------------------

def test_persist_diagram_noop_when_supabase_unconfigured():
    with patch.object(persistence, "get_supabase", return_value=None):
        persistence.persist_diagram("sess-1", [{"type": "box"}])  # should not raise


def test_persist_diagram_updates_expected_row():
    sb = _mock_supabase()
    elements = [{"type": "box", "x": 1}]
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_diagram("sess-1", elements)
    sb.table.assert_called_once_with("sessions")
    sb.table.return_value.update.assert_called_once_with({"diagram_elements": elements})
    sb.table.return_value.update.return_value.eq.assert_called_once_with("id", "sess-1")


# --- persist_message ------------------------------------------------

def test_persist_message_noop_when_supabase_unconfigured():
    with patch.object(persistence, "get_supabase", return_value=None):
        persistence.persist_message("sess-1", "candidate", "hi", 3)  # should not raise


def test_persist_message_inserts_expected_row():
    sb = _mock_supabase()
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_message("sess-1", "candidate", "hi", 3)
    sb.table.assert_called_once_with("messages")
    payload = sb.table.return_value.insert.call_args[0][0]
    assert payload["session_id"] == "sess-1"
    assert payload["role"] == "candidate"
    assert payload["content"] == "hi"
    assert payload["sequence_no"] == 3


# --- persist_evaluation ------------------------------------------------

def test_persist_evaluation_noop_when_supabase_unconfigured():
    with patch.object(persistence, "get_supabase", return_value=None):
        persistence.persist_evaluation("sess-1", {"overall_score": 8})  # should not raise


def test_persist_evaluation_updates_session_with_star_and_diagram():
    sb = _mock_supabase()
    result = {
        "overall_score": 8,
        "summary": "Solid answer",
        "star_analysis": {"situation": "ok"},
        "diagram_evaluation": {"score": 7},
        "evaluations": [],
    }
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_evaluation("sess-1", result)

    update_calls = [c for c in sb.table.call_args_list if c.args == ("sessions",)]
    assert len(update_calls) == 1
    payload = sb.table.return_value.update.call_args[0][0]
    assert payload["status"] == "completed"
    assert payload["overall_score"] == 8
    assert payload["summary"] == "Solid answer"
    assert payload["star_analysis"] == {"situation": "ok"}
    assert payload["diagram_evaluation"] == {"score": 7}
    assert "ended_at" in payload


def test_persist_evaluation_omits_diagram_evaluation_key_when_none():
    sb = _mock_supabase()
    result = {"overall_score": 5, "summary": "meh", "evaluations": []}
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_evaluation("sess-1", result)
    payload = sb.table.return_value.update.call_args[0][0]
    assert "diagram_evaluation" not in payload
    assert payload["star_analysis"] is None


def test_persist_evaluation_inserts_one_row_per_category():
    sb = _mock_supabase()
    result = {
        "overall_score": 6,
        "summary": "ok",
        "evaluations": [
            {"category": "communication", "score": 6, "feedback": "clear"},
            {"category": "problem_solving", "score": 7, "feedback": "good approach"},
        ],
    }
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_evaluation("sess-1", result)

    eval_insert_calls = [
        c for c in sb.table.return_value.insert.call_args_list
    ]
    # First insert.call_args corresponds to "sessions".update, not insert, so
    # every insert() call recorded here belongs to the "evaluations" table.
    assert len(eval_insert_calls) == 2
    assert eval_insert_calls[0].args[0]["category"] == "communication"
    assert eval_insert_calls[0].args[0]["score"] == 6
    assert eval_insert_calls[1].args[0]["category"] == "problem_solving"
    assert eval_insert_calls[1].args[0]["score"] == 7
