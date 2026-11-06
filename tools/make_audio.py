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


def saw_tone(freq, dur, amp=0.2, n_harm=10, detune=0.006, vib=0.0):
    """Warm, slightly detuned saw stack - the core synthwave pad voice."""
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    vibrato = (1 + vib * np.sin(2 * np.pi * 5 * t)) if vib else 1.0
    sig = np.zeros(n)
    for voice, dt in ((1.0, 0.0), (0.6, detune), (0.6, -detune)):
        f = freq * (1 + dt) * vibrato
        for h in range(1, n_harm + 1):
            sig += voice * (1.0 / h) * np.sin(2 * np.pi * f * h * t)
    return amp * sig / n_harm


def lowpass(sig, cutoff_k=24):
    """Gentle smoothing low-pass (moving average) for analog warmth."""
    kern = np.ones(cutoff_k) / cutoff_k
    return np.convolve(sig, kern, mode="same")


def pingpong(left, right, delay=0.33, feedback=0.42, taps=5, mix=0.4):
    """Stereo ping-pong echo - the classic neon/synthwave space."""
    d = int(delay * SR)
    outl, outr = left.copy(), right.copy()
    tapl, tapr = left.copy(), right.copy()
    for i in range(taps):
        tapl = np.concatenate([np.zeros(d), tapl[:-d]]) * feedback
        tapr = np.concatenate([np.zeros(d), tapr[:-d]]) * feedback
        # swap channels each repeat -> bounces left/right
        tapl, tapr = tapr, tapl
        outl += tapl * mix
        outr += tapr * mix
    return outl, outr


def sidechain(n, beat, depth=0.45, attack=0.012):
    """A soft 'breathing' pump synced to the beat (subtle sidechain duck)."""
    env = np.ones(n)
    step = int(beat * SR)
    ai = int(attack * SR)
    for start in range(0, n, step):
        rel = min(step, n - start)
        shape = np.ones(rel)
        if ai and rel > ai:
            shape[:ai] = np.linspace(1 - depth, 1 - depth, ai)  # held dip at onset
            shape[ai:] = np.linspace(1 - depth, 1.0, rel - ai) ** 0.6  # smooth recovery
        env[start:start + rel] = shape
    return env


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
    """A chill cyberpunk / synthwave loop in A minor.

    Dark detuned saw pads over a soft pulsing synth bass, a neon ping-pong
    arpeggio and an airy noise bed, all gently 'breathing' with a subtle
    beat-synced sidechain. Relaxing, not busy - meant to sit under the game.
    """
    beat = 0.75  # ~80 BPM, laid-back
    bars = 16
    bar_len = int(4 * beat * SR)
    total = bars * bar_len
    left = np.zeros(total)
    right = np.zeros(total)
    pad_bus_l = np.zeros(total)   # pads + arp get the sidechain pump
    pad_bus_r = np.zeros(total)

    # i - VI - III - VII voicings with added colour (noir synthwave)
    #   Am9 - Fmaj7 - Cmaj7 - G6
    prog = [
        [("A", 3), ("C", 4), ("E", 4), ("B", 4)],
        [("F", 3), ("A", 3), ("C", 4), ("E", 4)],
        [("C", 3), ("E", 3), ("G", 3), ("B", 3)],
        [("G", 3), ("B", 3), ("D", 4), ("E", 4)],
    ]

    # --- Pads: warm detuned saw, slow swell, wide stereo -------------------
    for b in range(bars):
        chord = prog[b % len(prog)]
        start = b * bar_len
        for j, (nm, octv) in enumerate(chord):
            f = note(nm, octv)
            pad = saw_tone(f, 4 * beat, amp=0.10, n_harm=9, detune=0.007, vib=0.003)
            pad = lowpass(pad, 40)   # soften the saw into a warm pad
            pad *= adsr(len(pad), a=0.9, d=0.8, s=0.6, r=1.1, sustain=0.65)
            end = min(start + len(pad), total)
            pan = 0.5 + 0.35 * np.sin(j * 1.3 + 0.5)   # spread voices across the field
            pad_bus_l[start:end] += pad[:end - start] * (1 - pan) * 1.2
            pad_bus_r[start:end] += pad[:end - start] * pan * 1.2

    # --- Arp: plucky ping-pong line through the chord (neon shimmer) -------
    eighth = int(beat / 2 * SR)
    arp_pattern = [0, 2, 1, 3, 2, 1, 2, 0]  # index into the current chord, octave up
    for b in range(bars):
        chord = prog[b % len(prog)]
        for s in range(8):
            idx = arp_pattern[s % len(arp_pattern)]
            nm, octv = chord[idx % len(chord)]
            f = note(nm, octv + 1)
            pos = b * bar_len + s * eighth
            pl = tone(f, beat * 0.45, amp=0.05, harmonics=(1.0, 0.5, 0.25, 0.1))
            pl *= adsr(len(pl), 0.004, 0.06, 0.25, 0.18, sustain=0.2)
            end = min(pos + len(pl), total)
            pad_bus_l[pos:end] += pl[:end - pos]
            pad_bus_r[pos:end] += pl[:end - pos]

    # breathing pump on pads + arp, then fold into the mix
    pump = sidechain(total, beat, depth=0.38)
    pl, pr = pingpong(pad_bus_l * pump, pad_bus_r * pump,
                      delay=beat * 0.5, feedback=0.4, taps=5, mix=0.35)
    left += pl
    right += pr

    # --- Synth bass: soft pulse on every beat (chill, not driving) --------
    bass_amp = [0.9, 0.5, 0.7, 0.5]  # accent the downbeat
    for b in range(bars):
        nm, octv = prog[b % len(prog)][0]
        f = note(nm, octv - 1)
        for beat_i in range(4):
            pos = b * bar_len + beat_i * int(beat * SR)
            bs = saw_tone(f, beat * 0.9, amp=0.16 * bass_amp[beat_i], n_harm=6, detune=0.003)
            bs = lowpass(bs, 30)
            bs *= adsr(len(bs), 0.006, 0.12, 0.55, 0.12, sustain=0.5)
            end = min(pos + len(bs), total)
            left[pos:end] += bs[:end - pos]
            right[pos:end] += bs[:end - pos]

    # --- Airy noise bed: very quiet, slowly swelling (lo-fi atmosphere) ----
    noise = np.random.uniform(-1, 1, total)
    noise = lowpass(noise, 80) * 0.03
    swell = 0.5 + 0.5 * np.sin(np.linspace(0, 2 * np.pi * 2, total))  # two slow swells
    left += noise * swell
    right += np.concatenate([noise[200:], noise[:200]]) * swell  # slight decorrelation

    # overall warmth + space
    left = lowpass(soft_reverb(left, 0.22, 0.12), 8)
    right = lowpass(soft_reverb(right, 0.22, 0.14), 8)

    # crossfade the tail into the head so it loops seamlessly
    xf = int(1.5 * SR)
    for ch in (left, right):
        head = ch[:xf].copy()
        tail = ch[-xf:].copy()
        fade = np.linspace(0, 1, xf)
        ch[:xf] = head * fade + tail * (1 - fade)

    stereo = np.vstack([normalize(left, 0.72), normalize(right, 0.72)])
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
