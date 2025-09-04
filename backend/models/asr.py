import os
import wave
import json
from vosk import Model, KaldiRecognizer
from langdetect import detect

# Paths to vosk models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR_EN = os.path.join(BASE_DIR, "vosk-model-small-en-us-0.15")
MODEL_DIR_HI = os.path.join(BASE_DIR, "vosk-model-small-hi-0.22")

VOSK_OK = os.path.isdir(MODEL_DIR_EN) and os.path.isdir(MODEL_DIR_HI)

model_en = Model(MODEL_DIR_EN) if os.path.isdir(MODEL_DIR_EN) else None
model_hi = Model(MODEL_DIR_HI) if os.path.isdir(MODEL_DIR_HI) else None


def asr_file_vosk(audio_path, language=None):
    """
    Transcribe a WAV file with VOSK.
    - audio_path: path to wav file
    - language: 'en' or 'hi'. If None, auto-detect.
    """
    if not VOSK_OK:
        raise RuntimeError("VOSK models not found")

    wf = wave.open(audio_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        raise ValueError("Audio file must be WAV format, mono PCM16")

    # Default recognizer (English)
    rec = KaldiRecognizer(model_en, wf.getframerate())

    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()).get("text", ""))
    results.append(json.loads(rec.FinalResult()).get("text", ""))
    text = " ".join(r for r in results if r).strip()

    # Auto detect language if not forced
    if not language and text:
        try:
            lang_code = detect(text)
            if lang_code.startswith("hi"):
                language = "hi"
            else:
                language = "en"
        except Exception:
            language = "en"

    # If Hindi requested or detected, redo transcription with Hindi model
    if language == "hi" and model_hi:
        wf.rewind()
        rec = KaldiRecognizer(model_hi, wf.getframerate())
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                results.append(json.loads(rec.Result()).get("text", ""))
        results.append(json.loads(rec.FinalResult()).get("text", ""))
        text = " ".join(r for r in results if r).strip()

    return text
