import asyncio
import os
import re
import sys
import tempfile

import httpx

from services.logger import log
from services.retry import with_retry

# emkc.org — free public Piston API, no key needed, identical request/response format
_EMKC_URL = "https://emkc.org/api/v2/piston/execute"

# Wandbox — free public compiler service, no auth
_WANDBOX_URL = "https://wandbox.org/api/compile.json"
_WANDBOX_COMPILER = {
    "python": "cpython-3.12.7",
    "node":   "nodejs-20.17.0",
    "java":   "openjdk-jdk-21+35",
    "gcc":    "gcc-head",
}
_WANDBOX_EXTRA: dict[str, dict] = {
    "gcc": {"compiler-option-raw": "-std=c++17"},
}

_UNAVAILABLE = {
    "run": {
        "stdout": "",
        "stderr": "Code execution is temporarily unavailable. Please try again in a moment.",
        "code": -1,
    }
}

_OCI_MARKERS = ("OCI runtime", "crun: clone", "Resource temporarily unavailable")


def _is_oci_error(text: str) -> bool:
    return any(m in text for m in _OCI_MARKERS)


async def _emkc(language: str, version: str, source: str, stdin: str) -> dict | None:
    """Public Piston API hosted by emkc.org — no key, free, same format as self-hosted."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                _EMKC_URL,
                json={"language": language, "version": version,
                      "files": [{"content": source}], "stdin": stdin},
            )
            resp.raise_for_status()
            data = resp.json()
            if "run" not in data:
                return None
            if _is_oci_error(data["run"].get("stderr", "")):
                return None
            return data
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        return None


def _wandbox_source(language: str, source: str) -> str:
    if language == "java":
        return re.sub(r"^public\s+class\b", "class", source, count=1, flags=re.MULTILINE)
    return source


async def _wandbox(language: str, source: str, stdin: str) -> dict | None:
    compiler = _WANDBOX_COMPILER.get(language)
    if not compiler:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {"code": _wandbox_source(language, source), "compiler": compiler, "stdin": stdin}
            payload.update(_WANDBOX_EXTRA.get(language, {}))
            resp = await client.post(_WANDBOX_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            stderr = data.get("program_error") or data.get("compiler_error") or ""
            if _is_oci_error(stderr):
                return None
            return {
                "run": {
                    "stdout": data.get("program_output") or "",
                    "stderr": stderr,
                    "code": int(data.get("status", 0)),
                }
            }
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        return None


async def _local_subprocess(language: str, source: str, stdin: str) -> dict | None:
    """Last-resort: run code directly in the backend container.
    Python 3.12 and gcc/g++ are always present. nodejs is installed too."""
    src_file = bin_file = None
    try:
        if language == "python":
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source)
                src_file = f.name
            run_argv = [sys.executable, src_file]

        elif language == "node":
            with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
                f.write(source)
                src_file = f.name
            run_argv = ["node", src_file]

        elif language == "gcc":
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
                f.write(source)
                src_file = f.name
            bin_fd, bin_file = tempfile.mkstemp()
            os.close(bin_fd)
            compile_proc = await asyncio.create_subprocess_exec(
                "g++", "-std=c++17", "-O2", "-o", bin_file, src_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, compile_err = await asyncio.wait_for(compile_proc.communicate(), timeout=15)
            if compile_proc.returncode != 0:
                return {"run": {"stdout": "", "stderr": compile_err.decode(errors="replace"), "code": compile_proc.returncode}}
            run_argv = [bin_file]

        else:
            return None

        proc = await asyncio.create_subprocess_exec(
            *run_argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin.encode() if stdin else b""),
                timeout=15,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"run": {"stdout": "", "stderr": "Time limit exceeded (15s).", "code": 1}}
    except FileNotFoundError:
        return None
    except Exception:
        return None
    finally:
        for path in (src_file, bin_file):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    return {
        "run": {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "code": proc.returncode,
        }
    }


async def run_code(language: str, version: str, source: str, stdin: str = "") -> dict:
    import time

    # 1. emkc.org — free external Piston API, no key, covers all languages
    start = time.monotonic()
    try:
        result = await with_retry(
            lambda: _emkc(language, version, source, stdin),
            attempts=2,
            base_delay=0.5,
            label="emkc",
        )
    except Exception:
        result = None

    if result:
        log.info("piston.run", language=language, latency_ms=round((time.monotonic() - start) * 1000), backend="emkc")
        return result

    log.warning("piston.emkc_unavailable", language=language)

    # 2. Wandbox — different external service, good Python/JS/Java/C++ coverage
    wb_start = time.monotonic()
    try:
        result = await with_retry(
            lambda: _wandbox(language, source, stdin),
            attempts=2,
            base_delay=1.0,
            label="wandbox",
        )
    except Exception:
        result = None

    if result:
        log.info("piston.run", language=language, latency_ms=round((time.monotonic() - wb_start) * 1000), backend="wandbox")
        return result

    log.warning("piston.wandbox_unavailable", language=language)

    # 3. Local subprocess — Python + Node run directly in the backend container
    sub_start = time.monotonic()
    try:
        result = await _local_subprocess(language, source, stdin)
    except Exception:
        result = None

    if result:
        log.info("piston.run", language=language, latency_ms=round((time.monotonic() - sub_start) * 1000), backend="subprocess")
        return result

    log.error("piston.all_unavailable", language=language)
    return _UNAVAILABLE
