import os
import wave

from dotenv import load_dotenv

load_dotenv() 

import requests
import whisper
from pydub import AudioSegment

SARVAM_PIECE_SECONDS = 25  

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")

_model = None


def load_model():
    global _model

    if _model is None:
        print(f"Loading Whisper model: {WHISPER_MODEL} ...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("Whisper model loaded.")
    return _model


def transcribe_chunk_whisper(chunk_path: str) -> list:
    """Return [{start, end, text}, ...] with times relative to this chunk."""
    model = load_model()
    result = model.transcribe(chunk_path, task="transcribe")
    return [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result["segments"]
    ]


def _send_to_sarvam(piece_path: str) -> str:
    """Send one <=30s WAV file to Sarvam and return the English transcript."""
    headers = {"api-subscription-key": SARVAM_API_KEY}

    with open(piece_path, "rb") as f:
        files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
        data = {"model": SARVAM_MODEL, "with_diarization": "false"}
        response = requests.post(
            SARVAM_STT_TRANSLATE_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        print(f"\n Sarvam returned {response.status_code}")
        print(f"Response body: {response.text}\n")
        response.raise_for_status()

    return response.json().get("transcript", "")


def transcribe_chunk_sarvam(chunk_path: str) -> list:
    """
    Sarvam sync API only accepts <=30s audio. Split this chunk into
    25-second pieces, send each separately, and return one segment per piece.
    Times are relative to this chunk.
    """
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000
    total_pieces = (len(audio) + piece_ms - 1) // piece_ms
    segments = []

    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")

        try:
            print(f"  → Sarvam piece {i + 1}/{total_pieces} ...")
            text = _send_to_sarvam(piece_path).strip()
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

        if text:
            segments.append({
                "start": start / 1000,
                "end": (start + len(piece)) / 1000,
                "text": text,
            })

    return segments


def transcribe_chunk(chunk_path: str, language: str = "english") -> list:
    """
    Route one chunk to Whisper or Sarvam depending on language choice.
    - english  → Whisper (local model)
    - hinglish → Sarvam (translates to English while transcribing)
    Returns a list of {start, end, text} segments.
    """
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)
    return transcribe_chunk_whisper(chunk_path)


def _wav_duration(path: str) -> float:
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


def transcribe_all_with_segments(chunks: list, language: str = "english") -> list:
    """Return [{start, end, text}, ...] with times relative to the full video."""
    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    all_segments = []
    offset = 0.0 

    for i, chunk in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        for seg in transcribe_chunk(chunk, language=language):
            all_segments.append({
                "start": seg["start"] + offset,
                "end": seg["end"] + offset,
                "text": seg["text"],
            })

        offset += _wav_duration(chunk) 

    print("Transcription complete.")
    return all_segments


def transcribe_all(chunks: list, language: str = "english") -> str:
    """Plain-text transcript, so existing code keeps working."""
    segments = transcribe_all_with_segments(chunks, language)
    return " ".join(s["text"] for s in segments)