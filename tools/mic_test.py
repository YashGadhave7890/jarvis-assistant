#!/usr/bin/env python3
"""
Real-Time Microphone Energy Calibration Tool
Prints dynamic visual meter to help determine optimal SILENCE_THRESHOLD.
Usage: python tools/mic_test.py
"""

import time
import pyaudio
import numpy as np

CHUNK = 1024
RATE = 16000
DURATION = 10  # seconds

def main():
    try:
        audio = pyaudio.PyAudio()
    except Exception as e:
        print(f"[ERROR] Could not initialize audio hardware subsystem: {e}")
        return

    # Find default input device
    device_index = None
    try:
        def_dev = audio.get_default_input_device_info()
        device_index = def_dev["index"]
        print(f"\nUsing Default Microphone: [{device_index}] {def_dev['name']}")
    except Exception:
        for i in range(audio.get_device_count()):
            try:
                info = audio.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    device_index = i
                    print(f"\nUsing First Available Microphone: [{device_index}] {info['name']}")
                    break
            except Exception:
                pass

    if device_index is None:
        print("[ERROR] No microphone detected on this system.")
        audio.terminate()
        return

    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK,
        )
    except Exception as e:
        print(f"[ERROR] Could not open audio stream: {e}")
        audio.terminate()
        return

    print(f"\nListening for {DURATION} seconds... speak normally to calibrate energy levels!")
    print("=" * 60)
    print("  Ambient silence is typically: 0.0001 – 0.0010")
    print("  Active speaking is typically:  0.0030 – 0.0500")
    print("=" * 60 + "\n")

    max_energy = 0.0
    start = time.time()

    while time.time() - start < DURATION:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            energy = float(np.sqrt(np.mean(audio_data ** 2)))
            max_energy = max(max_energy, energy)

            bar_len = int(energy * 1500)
            bar = "█" * min(bar_len, 40)
            status = "🎙️  VOICE DETECTED" if energy > 0.0020 else "💤 Silence"
            print(f"\rEnergy: {energy:.5f} |{bar:<40}| {status:<18}", end="", flush=True)
        except Exception:
            pass

    stream.stop_stream()
    stream.close()
    audio.terminate()

    print(f"\n\nCalibration Complete! Peak energy: {max_energy:.5f}")
    rec_threshold = max(0.0015, round(max_energy * 0.25, 4))
    print(f"Recommended SILENCE_THRESHOLD for .env: {rec_threshold}\n")

if __name__ == "__main__":
    main()
