"""
Unified Speech-to-Text Engine.
Supports high-speed Groq Whisper (cloud, ~200ms latency) with seamless
fallback to local Faster-Whisper (offline CPU).
"""

import io
import logging
import os
import wave
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# Common phrases Whisper hallucinates on background noise or silence
_HALLUCINATION_PATTERNS = {
    "", "thanks for watching", "thank you for watching", "thank you.",
    "thanks.", "you", ".", " ", "bye", "bye.", "okay", "okay.",
    "you.", "the", "the.", "[music]", "[ music ]", "(music)",
    "subtitles by", "transcribed by", "www.", ".com", "so", "oh",
    "thank you very much.", "subscribe", "please subscribe",
}


class STTWhisper:
    def __init__(self, model_size: str = "tiny", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.local_model = None
        self.groq_client = None
        self.groq_model = "whisper-large-v3"
        self._init_groq()

    def _init_groq(self):
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if api_key:
            try:
                import groq
                self.groq_client = groq.Groq(api_key=api_key)
                logger.info("STT: Groq Cloud Whisper ready (whisper-large-v3).")
            except Exception as e:
                logger.warning(f"STT: Could not initialize Groq client: {e}")

    def load(self, background: bool = False):
        """Loads local Faster-Whisper model into memory as primary/fallback."""
        if self.local_model is not None:
            return

        def _do_load():
            try:
                from faster_whisper import WhisperModel
                logger.info(f"STT: Loading local Faster-Whisper '{self.model_size}' on {self.device}...")
                self.local_model = WhisperModel(
                    self.model_size, device=self.device, compute_type="float32"
                )
                logger.info("STT: Local Faster-Whisper model loaded successfully.")
            except Exception as e:
                logger.error(f"STT: Failed to load local Whisper: {e}")

        if background:
            import threading
            threading.Thread(target=_do_load, daemon=True, name="WhisperLoad").start()
        else:
            _do_load()

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribes audio data (1D float32 array normalized -1.0 to 1.0 at 16000Hz).
        Tries Groq Cloud Whisper first for blazing speed; falls back to local Whisper.
        """
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Try Groq Cloud Whisper for fast, accurate response
        if self.groq_client:
            try:
                text = self._transcribe_groq(audio_data)
                if text:
                    clean = self._clean_text(text)
                    if clean:
                        return clean
            except Exception as e:
                logger.warning(f"Groq Whisper failed ({e}), falling back to local model...")

        # 2. Local Faster-Whisper fallback
        return self._transcribe_local(audio_data)

    def _transcribe_groq(self, audio_data: np.ndarray) -> str:
        # Convert float32 [-1, 1] to int16 PCM WAV in memory
        int_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
        bio = io.BytesIO()
        bio.name = "audio.wav"
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(int_data.tobytes())
        bio.seek(0)

        response = self.groq_client.audio.transcriptions.create(
            file=bio,
            model=self.groq_model,
            language="en",
            temperature=0.0,
            response_format="text",
        )
        if isinstance(response, str):
            return response.strip()
        return getattr(response, "text", "").strip()

    def _transcribe_local(self, audio_data: np.ndarray) -> str:
        if self.local_model is None:
            self.load()
        if self.local_model is None:
            logger.error("STT: No local model available.")
            return ""

        try:
            segments, _ = self.local_model.transcribe(
                audio_data,
                language="en",
                beam_size=3,
                best_of=1,
                temperature=0.0,
                no_speech_threshold=0.55,
                condition_on_previous_text=False,
                vad_filter=True,
            )
            parts = []
            for seg in segments:
                t = seg.text.strip()
                if t and t.lower() not in _HALLUCINATION_PATTERNS:
                    parts.append(t)
            return self._clean_text(" ".join(parts))
        except Exception as e:
            logger.error(f"Local Whisper transcription error: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        text = text.strip()
        if text.lower() in _HALLUCINATION_PATTERNS:
            return ""
        # Filter very short repetitive noise (e.g. single character or period)
        if len(text) <= 1:
            return ""
        return text
