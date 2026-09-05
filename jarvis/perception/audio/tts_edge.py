"""
Text-to-speech engine powered by edge-tts and pygame.mixer.
Includes clean Windows file handle management and speaking state events.
"""

import asyncio
import logging
import os
import random
import tempfile
import edge_tts
import pygame

try:
    from core.capabilities import has_audio_output, NO_SPEAKER_MSG
except ImportError:
    def has_audio_output():
        return sys.platform == "win32"
    NO_SPEAKER_MSG = "Local speaker output is unavailable in cloud mode."

logger = logging.getLogger(__name__)


class TTSEdge:
    def __init__(self, voice: str = "en-US-AriaNeural", on_start=None, on_end=None):
        self.voice = voice
        self.temp_dir = tempfile.gettempdir()
        self.on_start = on_start
        self.on_end = on_end
        self.is_speaking = False
        self.rate = "+0%"
        self._should_stop = False
        self.has_hardware = has_audio_output()
        if self.has_hardware:
            self._init_mixer()
        else:
            logger.info("TTSEdge initialized in headless/cloud mode (local speaker disabled).")

    def _init_mixer(self):
        if not has_audio_output():
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=2048)
                logger.info(f"TTS Edge initialized with voice: {self.voice}")
        except (pygame.error, OSError, Exception) as e:
            logger.warning(f"Pygame mixer init warning: {e}")

    def set_voice(self, voice_choice: str):
        v = (voice_choice or "").strip().lower()
        if "male" in v and "fe" not in v:
            self.voice = "en-US-GuyNeural"
        elif "female" in v:
            self.voice = "en-US-AriaNeural"
        elif v:
            self.voice = voice_choice
        logger.info(f"TTSEdge voice updated to: {self.voice}")

    def set_rate(self, rate_percent: int):
        """Sets speech rate, e.g. +10%, -10%."""
        prefix = "+" if rate_percent >= 0 else ""
        self.rate = f"{prefix}{rate_percent}%"
        logger.info(f"TTSEdge rate updated to: {self.rate}")

    def stop(self):
        """Immediately halts any active speech playback (barge-in interruption)."""
        self._should_stop = True
        self.is_speaking = False
        if not has_audio_output():
            return
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                logger.info("TTS playback stopped by interruption.")
        except Exception as e:
            logger.debug(f"Error stopping mixer: {e}")

    async def speak(self, text: str):
        text = (text or "").strip()
        if not text:
            return

        self._should_stop = False
        self.is_speaking = True
        if self.on_start:
            try:
                res = self.on_start(text)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

        if not has_audio_output():
            logger.debug(f"{NO_SPEAKER_MSG} Speech synthesized for UI only: '{text[:50]}...'")
            self.is_speaking = False
            if self.on_end:
                try:
                    res = self.on_end()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass
            return

        temp_file = os.path.join(
            self.temp_dir, f"jarvis_tts_{random.randint(100000, 999999)}.mp3"
        )

        try:
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            await communicate.save(temp_file)

            if self._should_stop:
                return

            if not pygame.mixer.get_init():
                self._init_mixer()

            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and not self._should_stop:
                await asyncio.sleep(0.03)

            if self._should_stop:
                pygame.mixer.music.stop()

            # Unload music file so Windows allows deleting it
            try:
                if hasattr(pygame.mixer.music, "unload"):
                    pygame.mixer.music.unload()
                else:
                    pygame.mixer.music.stop()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"TTS error: {e}")
            print(f"[Jarvis says]: {text}")
        finally:
            self.is_speaking = False
            if self.on_end:
                try:
                    res = self.on_end()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass

            # Safe cleanup
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
