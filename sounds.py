"""Generates the notification sounds (WAV) with pure Python - no downloads needed."""
import math
import os
import struct
import wave

RATE = 22050

# name -> list of (frequency Hz, duration seconds); frequency 0 = silence
SOUNDS = {
    "success": [(660, 0.12), (880, 0.18)],                      # two rising notes
    "complete": [(523, 0.1), (659, 0.1), (784, 0.1), (1047, 0.3)],  # cheerful chime
    "info": [(988, 0.15)],                                      # soft ping
    "warning": [(740, 0.12), (0, 0.06), (740, 0.12)],           # double beep
    "danger": [(330, 0.18), (247, 0.3)],                        # low falling buzz
    "focus_start": [(440, 0.1), (554, 0.1), (659, 0.2)],        # session starts
    "focus_end": [(784, 0.2), (0, 0.08), (784, 0.2), (0, 0.08), (1047, 0.45)],  # alarm bell
    "break_end": [(659, 0.15), (523, 0.15), (659, 0.3)],        # back to work
    "tick": [(1500, 0.02)],
}


def _tone(freq, dur, volume=0.45):
    n = int(RATE * dur)
    frames = bytearray()
    for i in range(n):
        if freq == 0:
            v = 0.0
        else:
            env = min(1.0, i / (RATE * 0.01)) * math.exp(-3.0 * i / n)
            v = volume * env * (math.sin(2 * math.pi * freq * i / RATE)
                                + 0.3 * math.sin(4 * math.pi * freq * i / RATE))
        frames += struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32000))
    return bytes(frames)


def ensure_sounds(static_folder):
    folder = os.path.join(static_folder, "sounds")
    os.makedirs(folder, exist_ok=True)
    for name, notes in SOUNDS.items():
        path = os.path.join(folder, f"{name}.wav")
        if os.path.exists(path):
            continue
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(b"".join(_tone(f, d) for f, d in notes))
