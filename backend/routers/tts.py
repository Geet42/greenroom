from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from auth import AuthenticatedUser, get_current_user
from services import tts
from services.rate_limit import check_rate_limit

router = APIRouter(prefix="/tts", tags=["tts"])


@router.get("/speak")
async def speak(
    text: str = Query(..., min_length=1, max_length=2000),
    user: AuthenticatedUser = Depends(get_current_user),
):
    check_rate_limit(user.id)
    path = await tts.get_or_synthesize(text)
    return FileResponse(path, media_type="audio/mpeg", filename="speech.mp3")
