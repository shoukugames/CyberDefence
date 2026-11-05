#!/usr/bin/env python3
"""Generate the ambient background music loop and UI sound effects.

Pure-numpy additive synthesis -> OGG Vorbis (falls back to WAV). Run once to
populate assets/audio/. The result is light, slow and relaxing: soft sine pads
drifting over a gentle root, with a quiet arpeggio - meant to sit under a puzzle.
"""
import os
import struct
import sys
import wave

import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "assets", "audio")


def adsr(n, a, d, s, r, sustain=0.7):
    env = np.ones(n)
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    ai, di, ri = min(ai, n), min(di, n - 1), min(ri, n - 1)
    if ai:
        env[:ai] = np.linspace(0, 1, ai)
    if di:
        env[ai:ai + di] = np.linspace(1, sustain, di)
    env[ai + di:n - ri] = sustain
    if ri:
        env[n - ri:] = np.linspace(env[n - ri - 1] if n - ri - 1 >= 0 else sustain, 0, ri)
    return env


def tone(freq, dur, amp=0.2, harmonics=(1.0, 0.0, 0.0), detune=0.0, vib=0.0):
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    sig = np.zeros(n)
    vibrato = (1 + vib * np.sin(2 * np.pi * 5 * t)) if vib else 1.0
    for i, h in enumerate(harmonics, start=1):
        if h:
            f = freq * i * vibrato
            sig += h * np.sin(2 * np.pi * f * t)
            if detune:
                sig += h * 0.5 * np.sin(2 * np.pi * f * (1 + detune) * t)
    return amp * sig


def note(name, octave=4):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3,
             "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    semis = names[name] + (octave - 4) * 12
    return 440.0 * (2 ** (semis / 12))


def soft_reverb(sig, decay=0.3, delay=0.09):
    d = int(delay * SR)
    out = sig.copy()
    tap = sig.copy()
    for _ in range(4):
        tap = np.concatenate([np.zeros(d), tap[:-d]]) * decay
        out += tap
    return out


def normalize(sig, peak=0.85):
    m = np.max(np.abs(sig)) or 1.0
    return sig * (peak / m)


def _write_wav(wav, pcm):
    with wave.open(wav, "wb") as w:
        w.setnchannels(pcm.shape[0] if pcm.ndim > 1 else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        if pcm.ndim > 1:
            inter = np.empty((pcm.shape[1] * pcm.shape[0],), dtype="<i2")
            inter[0::2] = pcm[0]
            inter[1::2] = pcm[1]
            w.writeframes(inter.tobytes())
        else:
            w.writeframes(pcm.tobytes())


def write_ogg_or_wav(path_noext, stereo, quality="4"):
    """Write WAV, then transcode to OGG Vorbis with ffmpeg (keeps files tiny)."""
    import shutil
    import subprocess
    data = np.clip(stereo, -1, 1)
    pcm = (data * 32767).astype("<i2")
    wav = path_noext + ".wav"
    _write_wav(wav, pcm)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        ogg = path_noext + ".ogg"
        try:
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", wav,
                            "-c:a", "libvorbis", "-qscale:a", quality, ogg], check=True)
            os.remove(wav)
            return ogg
        except (subprocess.CalledProcessError, OSError):
            pass
    return wav


def make_ambient():
    """A slow, calm ~40s loop in A minor (lo-fi 'study' feel)."""
    bars = 16
    beat = 1.4  # seconds - slow
    total = int(bars * 4 * beat * SR)
    left = np.zeros(total)
    right = np.zeros(total)

    # Chord progression: Am  -  Fmaj7  -  Cmaj7  -  G  (gentle, resolving)
    prog = [
        [("A", 3), ("C", 4), ("E", 4)],
        [("F", 3), ("A", 3), ("C", 4), ("E", 4)],
        [("C", 3), ("E", 3), ("G", 3), ("B", 3)],
        [("G", 3), ("B", 3), ("D", 4)],
    ]
    bar_len = int(4 * beat * SR)
    for b in range(bars):
        chord = prog[b % len(prog)]
        start = b * bar_len
        for nm, octv in chord:
            f = note(nm, octv)
            pad = tone(f, 4 * beat, amp=0.12, harmonics=(1.0, 0.25, 0.08), detune=0.004, vib=0.004)
            pad *= adsr(len(pad), a=1.0, d=1.0, s=0.6, r=1.3, sustain=0.6)
            end = min(start + len(pad), total)
            pan = 0.5 + 0.25 * np.sin(f)
            left[start:end] += pad[:end - start] * (1 - pan * 0.4)
            right[start:end] += pad[:end - start] * (0.6 + pan * 0.4)

    # Soft bell arpeggio, sparse
    arp_notes = [("A", 5), ("E", 5), ("C", 5), ("G", 4), ("E", 5), ("A", 5)]
    pos = int(2 * beat * SR)
    i = 0
    while pos < total - SR:
        nm, octv = arp_notes[i % len(arp_notes)]
        bell = tone(note(nm, octv), 1.6, amp=0.06, harmonics=(1.0, 0.4, 0.15, 0.05))
        bell *= adsr(len(bell), 0.01, 0.4, 0.3, 1.0, sustain=0.2)
        end = min(pos + len(bell), total)
        left[pos:end] += bell[:end - pos] * 0.8
        right[pos:end] += bell[:end - pos]
        pos += int(beat * 2 * SR)
        i += 1

    # Sub bass on the root of each bar
    for b in range(bars):
        nm, octv = prog[b % len(prog)][0]
        sub = tone(note(nm, octv - 1), 4 * beat, amp=0.14, harmonics=(1.0, 0.1))
        sub *= adsr(len(sub), 0.2, 0.5, 0.7, 1.0, sustain=0.7)
        start = b * bar_len
        end = min(start + len(sub), total)
        left[start:end] += sub[:end - start]
        right[start:end] += sub[:end - start]

    left = soft_reverb(left, 0.25, 0.11)
    right = soft_reverb(right, 0.25, 0.13)

    # gentle low-pass via moving average (warmth)
    k = 24
    kern = np.ones(k) / k
    left = np.convolve(left, kern, mode="same")
    right = np.convolve(right, kern, mode="same")

    # crossfade the tail into the head so it loops seamlessly
    xf = int(2.0 * SR)
    for ch in (left, right):
        head = ch[:xf].copy()
        tail = ch[-xf:].copy()
        fade = np.linspace(0, 1, xf)
        ch[:xf] = head * fade + tail * (1 - fade)
    left = ch  # noqa (right already updated in place)

    stereo = np.vstack([normalize(left, 0.7), normalize(right, 0.7)])
    return stereo


def make_sfx():
    sfx = {}
    # key click: tiny filtered noise burst
    n = int(0.05 * SR)
    click = np.random.uniform(-1, 1, n) * np.exp(-np.linspace(0, 8, n))
    click = np.convolve(click, np.ones(8) / 8, mode="same")
    sfx["key"] = normalize(click, 0.3)
    # select: short rising blip
    dur = 0.08
    sel = (tone(660, dur, 0.3) + tone(990, dur, 0.2)) * adsr(int(dur * SR), 0.005, 0.02, 0.3, 0.05, 0.4)
    sfx["select"] = normalize(sel, 0.4)
    # move: soft low blip
    sfx["move"] = normalize(tone(330, 0.06, 0.3) * adsr(int(0.06 * SR), 0.005, 0.02, 0.3, 0.03), 0.35)
    # error: low buzz
    ebuf = tone(140, 0.18, 0.3, harmonics=(1.0, 0.5, 0.3)) * adsr(int(0.18 * SR), 0.005, 0.05, 0.4, 0.08)
    sfx["error"] = normalize(ebuf, 0.4)
    # alert: two-tone warning
    a1 = tone(880, 0.12, 0.25) * adsr(int(0.12 * SR), 0.005, 0.02, 0.6, 0.04)
    a2 = tone(660, 0.14, 0.25) * adsr(int(0.14 * SR), 0.005, 0.02, 0.6, 0.05)
    sfx["alert"] = normalize(np.concatenate([a1, a2]), 0.4)
    # win: gentle ascending arpeggio
    seq = [note("C", 5), note("E", 5), note("G", 5), note("C", 6)]
    parts = []
    for i, f in enumerate(seq):
        tn = tone(f, 0.22, 0.25, harmonics=(1.0, 0.3, 0.1)) * adsr(int(0.22 * SR), 0.01, 0.05, 0.5, 0.12, 0.4)
        parts.append(tn)
    win = np.concatenate(parts)
    sfx["win"] = normalize(soft_reverb(win, 0.3, 0.08), 0.6)
    return sfx


def main():
    os.makedirs(OUT, exist_ok=True)
    print("Generating ambient loop...")
    amb = make_ambient()
    p = write_ogg_or_wav(os.path.join(OUT, "ambient"), amb)
    print("  ->", p)
    print("Generating sound effects...")
    for name, sig in make_sfx().items():
        st = np.vstack([sig, sig]) if sig.ndim == 1 else sig
        p = write_ogg_or_wav(os.path.join(OUT, name), st)
        print("  ->", p)
    print("Done.")


if __name__ == "__main__":
    main()
