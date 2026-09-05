"""
Audio Pipeline — Continuous, error-free microphone capture with adaptive VAD,
accurate device auto-selection, real-time energy broadcast, and deadlock prevention.
"""

import asyncio
import logging
import os
import threading
import time
import numpy as np
import pyaudio
from core.event_bus import EventBus
from perception.audio.stt_whisper import STTWhisper

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024
SAMPLE_RATE = 16000

# Compatible global flags for any legacy callers
MUTE_MIC = False


class AudioPipeline:
    """
    Manages continuous microphone stream, dynamic voice activity detection,
    real-time energy feedback, barge-in interruption, and wake-word modes.
    """

    def __init__(self, event_bus: EventBus, tts_engine=None, on_energy_callback=None, on_state_callback=None):
        self.bus = event_bus
        self.tts_engine = tts_engine
        self.stt = STTWhisper()
        self.loop = None

        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            logger.warning(f"PyAudio hardware initialization skipped ({e}). Operating in headless mode.")
            self.audio = None
        self.stream = None
        self.is_running = False
        self.is_muted = False
        self.state = "IDLE"  # IDLE | LISTENING | HEARING | PROCESSING | SPEAKING | MUTED

        # Listening Modes: "continuous" | "wakeword" | "ptt"
        self.listening_mode = os.environ.get("LISTENING_MODE", "continuous").lower()
        self.is_ptt_active = False

        self.on_energy = on_energy_callback
        self.on_state = on_state_callback

        # VAD Parameters
        self.ambient_floor = 0.0005
        self.silence_threshold = 0.0020
        self.min_speech_chunks = 6      # ~384ms minimum speech
        self.max_silence_chunks = 12    # ~768ms silence after voice signals end of utterance
        self.speech_buffer = []

        # Watchdog & throttling
        self.state_timestamp = time.time()
        self._last_energy_emit = 0.0
        self._device_index = None
        self._lock = threading.Lock()

    # ── State Management ───────────────────────────────────────────────────
    def set_state(self, new_state: str):
        with self._lock:
            if self.state == new_state:
                return
            self.state = new_state
            self.state_timestamp = time.time()

        logger.debug(f"[AudioPipeline] State → {new_state}")

        if self.on_state:
            try:
                self.on_state(new_state)
            except Exception:
                pass

        if self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.bus.publish("Audio.State", {"state": new_state}),
                    self.loop,
                )
            except Exception:
                pass

    # ── Mute / Unmute Controls ─────────────────────────────────────────────
    def mute(self):
        """Mutes the mic (e.g. while Jarvis is speaking or user toggles off)."""
        global MUTE_MIC
        self.is_muted = True
        MUTE_MIC = True
        self.speech_buffer.clear()
        self.set_state("MUTED")

    def unmute(self):
        """Unmutes the mic to listen continuously for commands."""
        global MUTE_MIC
        self.is_muted = False
        MUTE_MIC = False
        self.speech_buffer.clear()
        self.set_state("LISTENING")
        print("[Jarvis] Microphone active & listening...")

    # ── Device Resolution ──────────────────────────────────────────────────
    def _find_best_input_device(self) -> int:
        """Finds the default or best functional audio input device index."""
        if not self.audio:
            return None

        # 1. Check if user configured specific device index
        env_dev = os.environ.get("MIC_DEVICE_INDEX") or os.environ.get("AUDIO_INPUT_DEVICE")
        if env_dev and env_dev.isdigit():
            idx = int(env_dev)
            try:
                info = self.audio.get_device_info_by_index(idx)
                if info.get("maxInputChannels", 0) > 0:
                    logger.info(f"Using configured microphone: [{idx}] {info['name']}")
                    return idx
            except Exception:
                pass

        # 2. Try OS default input device
        try:
            default_dev = self.audio.get_default_input_device_info()
            idx = default_dev["index"]
            name = default_dev.get("name", "")
            logger.info(f"Using default system microphone: [{idx}] {name}")
            return idx
        except Exception as e:
            logger.warning(f"Could not get default input device: {e}")

        # 3. Fallback: Search for first real input hardware device
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    name = info.get("name", "").lower()
                    # Prefer real microphone array / microphone over generic mapper
                    if "sound mapper" not in name:
                        logger.info(f"Found input hardware device: [{i}] {info['name']}")
                        return i
            except Exception:
                continue

        return 0

    # ── Calibration ────────────────────────────────────────────────────────
    def _calibrate_ambient_noise(self):
        """Samples room background noise to set an adaptive silence threshold."""
        try:
            samples = []
            for _ in range(8):  # ~0.5s of audio
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                samples.append(float(np.sqrt(np.mean(arr ** 2))))

            avg_noise = float(np.mean(samples)) if samples else 0.0005
            self.ambient_floor = avg_noise

            # Set threshold dynamically: sensitive voice detection bounded within [0.0015, 0.0035]
            env_thresh = os.environ.get("SILENCE_THRESHOLD")
            if env_thresh:
                try:
                    raw_val = float(env_thresh)
                    self.silence_threshold = max(0.0015, min(raw_val, 0.0035))
                except ValueError:
                    self.silence_threshold = max(avg_noise * 2.5, 0.0018)
            else:
                self.silence_threshold = max(avg_noise * 2.5, 0.0018)

            self.silence_threshold = max(0.0015, min(self.silence_threshold, 0.0035))

            logger.info(
                f"[AudioPipeline] Calibrated ambient floor: {self.ambient_floor:.6f}, "
                f"Active voice threshold: {self.silence_threshold:.6f}"
            )
        except Exception as e:
            logger.warning(f"[AudioPipeline] Calibration warning: {e}")
            self.silence_threshold = 0.0025

    # ── Start / Stop ───────────────────────────────────────────────────────
    def start(self):
        if not self.audio:
            logger.info("Audio hardware not initialized — skipping microphone listener.")
            return

        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None

        self.stt.load(background=True)
        self._device_index = self._find_best_input_device()

        # Open stream with robust channel and rate selection
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=CHUNK_SIZE,
            )
        except Exception as e:
            logger.warning(f"Error opening 1-channel stream ({e}), trying stereo or default...")
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )

        self._calibrate_ambient_noise()
        self.is_running = True
        self.unmute()

        capture_thread = threading.Thread(
            target=self._listening_loop, daemon=True, name="ContinuousAudioCapture"
        )
        capture_thread.start()
        logger.info("Audio Pipeline continuous listener active.")

    def stop(self):
        self.is_running = False
        self.set_state("IDLE")
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.audio.terminate()
        except Exception:
            pass

    # ── Listening Mode Controls ───────────────────────────────────────────
    def set_listening_mode(self, mode: str):
        mode = (mode or "").lower().strip()
        if mode in ["continuous", "wakeword", "ptt"]:
            self.listening_mode = mode
            logger.info(f"[AudioPipeline] Listening mode changed to: {mode}")
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.bus.publish("Audio.ModeChanged", {"mode": mode}),
                    self.loop,
                )

    def set_ptt(self, active: bool):
        self.is_ptt_active = bool(active)
        if self.is_ptt_active:
            self.set_state("HEARING")
        else:
            if self.speech_buffer and len(self.speech_buffer) >= self.min_speech_chunks:
                buf_copy = list(self.speech_buffer)
                self.speech_buffer.clear()
                self.set_state("PROCESSING")
                threading.Thread(
                    target=self._process_speech_worker,
                    args=(buf_copy,),
                    daemon=True,
                    name="STTWorkerPTT",
                ).start()
            else:
                self.speech_buffer.clear()
                self.set_state("LISTENING")

    # ── Main Continuous Listening Loop ─────────────────────────────────────
    def _listening_loop(self):
        silence_count = 0
        barge_count = 0

        while self.is_running:
            try:
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if not data:
                    time.sleep(0.01)
                    continue

                audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                energy = float(np.sqrt(np.mean(audio_data ** 2)))

                # Broadcast live energy (throttled to ~30Hz)
                now = time.time()
                if now - self._last_energy_emit > 0.033:
                    self._last_energy_emit = now
                    normalized_energy = min(energy * 25.0, 1.0)
                    if self.on_energy:
                        try:
                            self.on_energy(normalized_energy, energy)
                        except Exception:
                            pass

                # Watchdog: if stuck in PROCESSING for > 12s, force return to LISTENING
                if self.state == "PROCESSING" and (now - self.state_timestamp > 12.0):
                    logger.warning("[AudioPipeline] Processing watchdog timeout — auto-reset to LISTENING")
                    self.unmute()

                # If assistant is speaking: check for user voice interruption (Barge-In)
                if self.state == "SPEAKING":
                    barge_thresh = max(self.silence_threshold * 2.4, 0.0055)
                    if energy > barge_thresh:
                        barge_count += 1
                        if barge_count >= 2:
                            logger.info("[AudioPipeline] Voice interruption detected! Halting TTS...")
                            if self.tts_engine:
                                self.tts_engine.stop()
                            if self.loop and self.loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    self.bus.publish("Audio.Interrupted", {}),
                                    self.loop
                                )
                            self.set_state("HEARING")
                            self.speech_buffer.append(audio_data)
                            barge_count = 0
                            silence_count = 0
                            continue
                    else:
                        barge_count = 0
                        self.speech_buffer.clear()
                    continue

                # If muted: drop captured chunks
                if self.is_muted or self.state == "MUTED":
                    self.speech_buffer.clear()
                    silence_count = 0
                    continue

                # If in PTT mode: only buffer when button/spacebar is held
                if self.listening_mode == "ptt" and not self.is_ptt_active:
                    self.speech_buffer.clear()
                    silence_count = 0
                    continue

                # If currently processing previous speech: don't buffer new speech yet
                if self.state == "PROCESSING":
                    self.speech_buffer.clear()
                    silence_count = 0
                    continue

                # ── Voice Detection ────────────────────────────────────────
                if energy > self.silence_threshold:
                    if not self.speech_buffer:
                        self.set_state("HEARING")
                    self.speech_buffer.append(audio_data)
                    silence_count = 0
                else:
                    silence_count += 1
                    # If we were capturing speech and silence reached limit
                    if self.speech_buffer and silence_count > self.max_silence_chunks:
                        captured_chunks = len(self.speech_buffer)
                        buf_copy = list(self.speech_buffer)
                        self.speech_buffer.clear()
                        silence_count = 0

                        if captured_chunks >= self.min_speech_chunks:
                            self.set_state("PROCESSING")
                            threading.Thread(
                                target=self._process_speech_worker,
                                args=(buf_copy,),
                                daemon=True,
                                name="STTWorker",
                            ).start()
                        else:
                            # Too short to be human speech (cough, click, or tap)
                            self.set_state("LISTENING")

            except Exception as e:
                logger.error(f"Audio stream error: {e}")
                time.sleep(0.05)

    # ── Speech Processing Worker ───────────────────────────────────────────
    def _process_speech_worker(self, buffer_chunks):
        try:
            audio_array = np.concatenate(buffer_chunks)
            text = self.stt.transcribe(audio_array)

            if text and text.strip():
                clean_text = text.strip()

                # Wake-word filter in wakeword mode
                if self.listening_mode == "wakeword":
                    import re
                    match = re.search(r"\b(jarvis|mini)\b", clean_text, re.IGNORECASE)
                    if not match:
                        logger.debug(f"[WakeWord] Non-wake utterance ignored: '{clean_text}'")
                        self.set_state("LISTENING")
                        return
                    # Strip the wake-word trigger prefix
                    clean_text = re.sub(r"^(?:hey\s+)?(?:jarvis|mini)[,\s]*", "", clean_text, flags=re.IGNORECASE).strip()
                    if not clean_text:
                        clean_text = "Hello"

                print(f"\n[Mic] Heard: \"{clean_text}\"")
                logger.info(f"Transcribed: '{clean_text}'")

                # Forward speech to EventBus
                if self.loop and self.loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self.bus.publish("Input.Text", {"text": clean_text, "source": "voice"}),
                        self.loop,
                    )
                else:
                    self.unmute()
            else:
                self.unmute()

        except Exception as e:
            logger.error(f"Speech processing error: {e}", exc_info=True)
            self.unmute()
