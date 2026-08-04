import hashlib
import os
import tempfile
import threading

import edge_tts

DEFAULT_VOICE = "en-US-AriaNeural"

# Repeat requests for the same (text, voice) pair — e.g. the candidate
# replaying the interviewer's question, or navigating back to one already
# asked — are served from disk instead of round-tripping to edge-tts every
# time. Bounded by _MAX_CACHE_ENTRIES with LRU eviction so the cache
# directory never grows without bound.
_CACHE_DIR = os.environ.get("TTS_CACHE_DIR") or os.path.join(tempfile.gettempdir(), "greenroom-tts-cache")
_MAX_CACHE_ENTRIES = int(os.environ.get("TTS_CACHE_MAX_ENTRIES", "500"))
_prune_lock = threading.Lock()


async def synthesize_to_file(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> None:
    """Generates speech audio for the given text and writes it to output_path as mp3.

    edge-tts (https://github.com/rany2/edge-tts) uses Microsoft Edge's online neural
    voices for free, with no API key required.
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _cache_path(text: str, voice: str) -> str:
    key = hashlib.sha256(f"{voice}:{text}".encode("utf-8")).hexdigest()
    return os.path.join(_CACHE_DIR, f"{key}.mp3")


def _prune_cache() -> None:
    """Evicts the least-recently-used entries once the cache exceeds
    _MAX_CACHE_ENTRIES entries."""
    with _prune_lock:
        try:
            entries = [os.path.join(_CACHE_DIR, f) for f in os.listdir(_CACHE_DIR)]
        except OSError:
            return
        overflow = len(entries) - _MAX_CACHE_ENTRIES
        if overflow <= 0:
            return
        entries.sort(key=lambda p: os.path.getmtime(p))
        for path in entries[:overflow]:
            try:
                os.unlink(path)
            except OSError:
                pass


async def get_or_synthesize(text: str, voice: str = DEFAULT_VOICE) -> str:
    """Returns a path to a cached mp3 for (text, voice), generating and
    caching it first on a miss."""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    path = _cache_path(text, voice)

    if os.path.exists(path):
        os.utime(path, None)  # mark as recently used for LRU pruning
        return path

    fd, tmp_path = tempfile.mkstemp(suffix=".mp3", dir=_CACHE_DIR)
    os.close(fd)
    try:
        await synthesize_to_file(text, tmp_path, voice)
        os.replace(tmp_path, path)  # atomic — no reader ever sees a partial file
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    _prune_cache()
    return path
