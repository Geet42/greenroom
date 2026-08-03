"""Unit tests for the code-execution fallback chain (Judge0 -> Judge0 RapidAPI -> local subprocess)."""
import pytest

from services import piston


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json


class _FakeAsyncClient:
    def __init__(self, response=None, raises=None):
        self._response = response
        self._raises = raises

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        if self._raises:
            raise self._raises
        return self._response


def _patch_client(monkeypatch, response=None, raises=None):
    monkeypatch.setattr(piston.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient(response, raises))


@pytest.mark.asyncio
async def test_judge0_success_returns_run_shape(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse({
        "status": {"id": 3, "description": "Accepted"},
        "stdout": "2\n",
        "stderr": None,
    }))
    result = await piston._judge0_public("python", "print(1+1)", "")
    assert result == {"run": {"stdout": "2\n", "stderr": "", "code": 0}}


@pytest.mark.asyncio
async def test_judge0_internal_error_status_treated_as_unavailable(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse({"status": {"id": 13, "description": "Internal Error"}}))
    result = await piston._judge0_public("python", "print(1)", "")
    assert result is None


@pytest.mark.asyncio
async def test_judge0_compile_error_is_a_legitimate_result(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse({
        "status": {"id": 6, "description": "Compilation Error"},
        "stdout": None,
        "compile_output": "SyntaxError: invalid syntax",
    }))
    result = await piston._judge0_public("python", "def bad(", "")
    assert result == {"run": {"stdout": "", "stderr": "SyntaxError: invalid syntax", "code": 1}}


@pytest.mark.asyncio
async def test_judge0_oci_error_in_stderr_treated_as_unavailable(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse({
        "status": {"id": 11, "description": "Runtime Error"},
        "stderr": "OCI runtime error: crun: clone: Resource temporarily unavailable",
    }))
    result = await piston._judge0_public("python", "print(1)", "")
    assert result is None


@pytest.mark.asyncio
async def test_judge0_connect_error_returns_none(monkeypatch):
    import httpx
    _patch_client(monkeypatch, raises=httpx.ConnectError("boom"))
    result = await piston._judge0_public("python", "print(1)", "")
    assert result is None


@pytest.mark.asyncio
async def test_judge0_rapidapi_skipped_without_key(monkeypatch):
    monkeypatch.setattr(piston, "_JUDGE0_RAPIDAPI_KEY", None)
    result = await piston._judge0_rapidapi("python", "print(1)", "")
    assert result is None


@pytest.mark.asyncio
async def test_unsupported_language_returns_none_from_judge0(monkeypatch):
    result = await piston._judge0_public("ruby", "puts 1", "")
    assert result is None


@pytest.mark.asyncio
async def test_run_code_falls_through_to_subprocess_for_python(monkeypatch):
    async def _unavailable(*args, **kwargs):
        return None

    monkeypatch.setattr(piston, "_judge0_public", _unavailable)
    monkeypatch.setattr(piston, "_judge0_rapidapi", _unavailable)

    result = await piston.run_code("python", "3.10.0", "print(1 + 1)", "")
    assert result["run"]["stdout"].strip() == "2"
    assert result["run"]["code"] == 0


@pytest.mark.asyncio
async def test_run_code_subprocess_cpp_compiles_and_runs(monkeypatch):
    async def _unavailable(*args, **kwargs):
        return None

    monkeypatch.setattr(piston, "_judge0_public", _unavailable)
    monkeypatch.setattr(piston, "_judge0_rapidapi", _unavailable)

    source = '#include <iostream>\nint main(){ std::cout << 1+1; return 0; }'
    result = await piston.run_code("gcc", "10.2.0", source, "")
    # If g++ isn't installed in this environment, subprocess returns None and
    # run_code degrades to _UNAVAILABLE rather than raising.
    if result is not piston._UNAVAILABLE:
        assert result["run"]["stdout"].strip() == "2"


@pytest.mark.asyncio
async def test_run_code_returns_unavailable_when_everything_fails(monkeypatch):
    async def _unavailable(*args, **kwargs):
        return None

    monkeypatch.setattr(piston, "_judge0_public", _unavailable)
    monkeypatch.setattr(piston, "_judge0_rapidapi", _unavailable)
    monkeypatch.setattr(piston, "_local_subprocess", _unavailable)

    result = await piston.run_code("java", "15.0.2", "class Main {}", "")
    assert result == piston._UNAVAILABLE
