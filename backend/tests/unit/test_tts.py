"""Unit tests for the on-disk TTS response cache in services/tts.py.

edge_tts.Communicate is never invoked for real here — synthesize_to_file is
patched with a fake that just writes bytes to output_path, so these tests
never make a network call.
"""
import os
from unittest.mock import patch

import pytest

from services import tts


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Each test gets its own empty cache directory and a small cap, so
    pruning behavior can be exercised without generating hundreds of files."""
    monkeypatch.setattr(tts, "_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(tts, "_MAX_CACHE_ENTRIES", 3)
    yield


async def _fake_synthesize(text: str, output_path: str, voice: str = tts.DEFAULT_VOICE) -> None:
    with open(output_path, "wb") as f:
        f.write(b"fake-mp3-bytes")


async def test_cache_miss_generates_and_writes_file():
    with patch.object(tts, "synthesize_to_file", side_effect=_fake_synthesize) as mock_synth:
        path = await tts.get_or_synthesize("Tell me about a challenge you faced.")
    assert os.path.exists(path)
    assert open(path, "rb").read() == b"fake-mp3-bytes"
    mock_synth.assert_called_once()


async def test_cache_hit_skips_regeneration():
    with patch.object(tts, "synthesize_to_file", side_effect=_fake_synthesize) as mock_synth:
        path1 = await tts.get_or_synthesize("Same question")
        path2 = await tts.get_or_synthesize("Same question")
    assert path1 == path2
    mock_synth.assert_called_once()


async def test_different_text_produces_different_cache_entries():
    with patch.object(tts, "synthesize_to_file", side_effect=_fake_synthesize):
        path1 = await tts.get_or_synthesize("Question A")
        path2 = await tts.get_or_synthesize("Question B")
    assert path1 != path2


async def test_different_voice_produces_different_cache_entry_for_same_text():
    with patch.object(tts, "synthesize_to_file", side_effect=_fake_synthesize):
        path1 = await tts.get_or_synthesize("Same text", voice="en-US-AriaNeural")
        path2 = await tts.get_or_synthesize("Same text", voice="en-GB-SoniaNeural")
    assert path1 != path2


async def test_cache_prunes_oldest_entries_beyond_cap():
    with patch.object(tts, "synthesize_to_file", side_effect=_fake_synthesize):
        for i in range(5):
            await tts.get_or_synthesize(f"Question {i}")
    remaining = os.listdir(tts._CACHE_DIR)
    assert len(remaining) == tts._MAX_CACHE_ENTRIES


async def test_synthesize_failure_cleans_up_temp_file_and_propagates():
    async def _boom(text, output_path, voice=tts.DEFAULT_VOICE):
        raise RuntimeError("edge-tts unreachable")

    with patch.object(tts, "synthesize_to_file", side_effect=_boom):
        with pytest.raises(RuntimeError):
            await tts.get_or_synthesize("Will fail")

    # No leftover temp file, and no cached entry for the failed request.
    assert os.listdir(tts._CACHE_DIR) == []
