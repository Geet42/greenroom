import os
import tempfile
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from services import tts

router = APIRouter(prefix="/tts", tags=["tts"])


@router.get("/speak")
async def speak(text: str = Query(..., min_length=1, max_length=2000)):
    out_path = os.path.join(tempfile.gettempdir(), f"greenroom-tts-{uuid.uuid4().hex}.mp3")
    await tts.synthesize_to_file(text, out_path)
    return FileResponse(out_path, media_type="audio/mpeg", filename="speech.mp3")
