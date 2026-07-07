"""
Architecture fitness functions — these tests enforce structural rules that
must never be violated regardless of feature changes.

Run with: pytest tests/architecture/ -v
"""
import ast
from pathlib import Path

FRONTEND_SRC = Path(__file__).parents[4] / "frontend" / "src"
BACKEND_SRC = Path(__file__).parents[2]


# ── Rule 1: service-role key must never appear in frontend source ─────────────

def _all_frontend_files():
    return list(FRONTEND_SRC.rglob("*.js")) + list(FRONTEND_SRC.rglob("*.jsx")) + \
           list(FRONTEND_SRC.rglob("*.ts")) + list(FRONTEND_SRC.rglob("*.tsx"))


def test_service_role_key_not_in_frontend():
    """SUPABASE_SERVICE_ROLE_KEY must never be referenced in frontend code."""
    violations = []
    for f in _all_frontend_files():
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "SERVICE_ROLE" in content or "service_role" in content.lower():
            violations.append(str(f.relative_to(FRONTEND_SRC)))
    assert not violations, (
        f"Service-role key referenced in frontend files: {violations}\n"
        "The service-role key bypasses RLS — it must only live on the backend."
    )


def test_supabase_url_uses_vite_env_prefix():
    """Frontend Supabase URL must come from VITE_ env vars, never hardcoded."""
    for f in _all_frontend_files():
        content = f.read_text(encoding="utf-8", errors="ignore")
        # supabase.co URLs hardcoded directly (not via env var) are a leak risk
        if "supabase.co" in content and "VITE_SUPABASE_URL" not in content:
            assert False, (
                f"{f.name}: Supabase URL appears hardcoded. Use VITE_SUPABASE_URL."
            )


# ── Rule 2: every session endpoint must call check_ownership ────────────────

def test_session_endpointscheck_ownership():
    """
    Every router function that accepts a session_id must call check_ownership.
    This is the app-layer ownership guard that sits in front of Postgres RLS.
    """
    router_file = BACKEND_SRC / "routers" / "interview.py"
    source = router_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        # Collect all argument names for this function
        arg_names = [a.arg for a in node.args.args]
        # Collect parameter names from type-annotated args that look like requests
        # (any arg that holds session_id — either directly or via a Pydantic model
        # where we know the field is req.session_id)
        uses_session = "session_id" in arg_names or any(
            isinstance(stmt, ast.Assign) and
            any("session_id" in ast.dump(t) for t in ast.walk(stmt))
            for stmt in ast.walk(node)
        )
        calls_ownership = any(
            isinstance(n, ast.Call) and
            getattr(getattr(n, "func", None), "id", None) == "check_ownership"
            for n in ast.walk(node)
        )
        if uses_session and not calls_ownership:
            violations.append(node.name)

    # start_session doesn't check ownership because the session is being created
    # (there's nothing to own yet). delete_session checks it conditionally.
    allowed_exceptions = {"start_session"}
    real_violations = [v for v in violations if v not in allowed_exceptions]
    assert not real_violations, (
        f"Session endpoints missing check_ownership: {real_violations}"
    )


# ── Rule 3: backend never imports from frontend ───────────────────────────────

def test_backend_does_not_import_frontend():
    """Backend Python files must never import anything from the frontend tree."""
    backend_py = list(BACKEND_SRC.rglob("*.py"))
    for f in backend_py:
        if ".venv" in str(f):
            continue
        source = f.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in getattr(node, "names", [])]
                module = getattr(node, "module", "") or ""
                assert not module.startswith("frontend") and not any(
                    n.startswith("frontend") for n in names
                ), (f"{f.name} imports from the frontend tree — cross-boundary dependency.")


# ── Rule 4: no hardcoded secrets pattern ─────────────────────────────────────

_SECRET_PATTERNS = ["sk-", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "xoxb-", "ghp_"]


def test_no_hardcoded_secrets_in_backend():
    backend_py = list(BACKEND_SRC.rglob("*.py"))
    for f in backend_py:
        if ".venv" in str(f) or "test" in str(f):
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in _SECRET_PATTERNS:
            assert pattern not in content, (
                f"Possible hardcoded secret ({pattern!r}) found in {f.name}"
            )
