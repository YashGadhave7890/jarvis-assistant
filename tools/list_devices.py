#!/usr/bin/env python3
"""
Audio Hardware Diagnostics — Lists all available input/microphone devices
and measures real-time audio energy levels.
Usage: python tools/list_devices.py
"""

import pyaudio
import numpy as np

def main():
    try:
        audio = pyaudio.PyAudio()
    except Exception as e:
        print(f"[ERROR] Could not initialize audio hardware subsystem: {e}")
        return

    print("\n" + "=" * 70)
    print("ALL DETECTED AUDIO INPUT DEVICES:")
    print("=" * 70)

    input_devices = []
    for i in range(audio.get_device_count()):
        try:
            info = audio.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                input_devices.append((i, info["name"], info["maxInputChannels"]))
                print(f"  Index {i:2d}: {info['name']}")
                print(f"          Channels: {info['maxInputChannels']}, Default Rate: {int(info['defaultSampleRate'])}Hz")
        except Exception:
            pass

    if not input_devices:
        print("  No audio input hardware detected.")
        audio.terminate()
        return

    print("=" * 70)
    print("\nMeasuring energy level on each device for 2 seconds... speak now!\n")

    best_device = 0
    best_energy = 0.0

    for idx, name, channels in input_devices:
        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=idx,
                frames_per_buffer=1024,
            )
            energies = []
            for _ in range(30):  # ~2 seconds
                data = stream.read(1024, exception_on_overflow=False)
                chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                energies.append(float(np.sqrt(np.mean(chunk ** 2))))
            stream.stop_stream()
            stream.close()

            avg_energy = float(np.mean(energies))
            max_energy = float(np.max(energies))
            print(f"  Device {idx:2d}: avg={avg_energy:.6f}  max={max_energy:.6f}  -> {name}")

            if max_energy > best_energy:
                best_energy = max_energy
                best_device = idx

        except Exception as e:
            print(f"  Device {idx:2d}: ERROR - {e}")

    audio.terminate()
    print("\n" + "=" * 70)
    print(f"Recommended Microphone Index: {best_device} (Peak Energy: {best_energy:.6f})")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
