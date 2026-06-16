import edge_tts

DEFAULT_VOICE = "en-US-AriaNeural"


async def synthesize_to_file(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> None:
    """Generates speech audio for the given text and writes it to output_path as mp3.

    edge-tts (https://github.com/rany2/edge-tts) uses Microsoft Edge's online neural
    voices for free, with no API key required.
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
