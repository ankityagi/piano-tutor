#!/usr/bin/env python3
"""Basic Pitch accuracy test for the practice-check idea.

Scores a practice recording against the piece it was supposed to be, using
Spotify's Basic Pitch to hear the notes. Use it to answer one question before
building anything: can Basic Pitch tell right notes from wrong ones on real
phone recordings of a kid practising?

Usage:
  python accuracy_test.py TARGET RECORDING [RECORDING ...]
  python accuracy_test.py --batch clips.csv

TARGET is either a .mid file of the piece or a .txt file of note names in
order, e.g. "C4 C4 G4 G4 A4 A4 G4". RECORDING is any audio file the phone
makes (.m4a, .wav, .mp3); .m4a needs ffmpeg installed.

clips.csv has columns: recording,target,expected_mistakes
(expected_mistakes is how many wrong/missed/extra notes you actually made;
leave blank if you don't know).
"""
import argparse
import csv
import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")  # quiet TensorFlow
warnings.filterwarnings("ignore")

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def name_to_midi(name):
    import re
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d)", name.strip())
    if not m:
        raise ValueError(f"Can't read note name {name!r}; use forms like C4, F#3, Bb4")
    letter = m.group(1).upper() + m.group(2)
    letter = FLATS.get(letter, letter)
    return NOTE_NAMES.index(letter) + 12 * (int(m.group(3)) + 1)


def midi_to_name(m):
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


def load_target(path):
    """Return a list of (onset_seconds or None, midi_pitch) in playing order."""
    path = Path(path)
    if path.suffix.lower() in (".mid", ".midi"):
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(str(path))
        notes = [n for inst in pm.instruments if not inst.is_drum for n in inst.notes]
        notes.sort(key=lambda n: (n.start, -n.pitch))
        return [(n.start, n.pitch) for n in notes]
    text = path.read_text().replace(",", " ").split()
    return [(None, name_to_midi(t)) for t in text]


def hear_notes(recording, min_amplitude=0.3, min_note_ms=80, chord_window_ms=60,
               melody_only=True):
    """Run Basic Pitch and return a cleaned list of (onset_seconds, midi_pitch)."""
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict
    _, _, events = predict(str(recording), ICASSP_2022_MODEL_PATH,
                           minimum_note_length=min_note_ms)
    events = [e for e in events if e[3] >= min_amplitude and (e[1] - e[0]) * 1000 >= min_note_ms]
    events.sort(key=lambda e: e[0])
    if not melody_only:
        return [(e[0], e[2]) for e in events]
    # One note at a time: notes starting within chord_window_ms of each other
    # are treated as one attack, and the loudest wins (drops overtone ghosts).
    out, group = [], []
    for e in events:
        if group and (e[0] - group[0][0]) * 1000 > chord_window_ms:
            best = max(group, key=lambda g: g[3])
            out.append((group[0][0], best[2]))
            group = []
        group.append(e)
    if group:
        best = max(group, key=lambda g: g[3])
        out.append((group[0][0], best[2]))
    return out


def same_note(a, b, octave_tolerant):
    return (a % 12 == b % 12) if octave_tolerant else a == b


def align(target, heard, octave_tolerant=True):
    """Edit-distance alignment of two pitch sequences.

    Returns a list of (op, target_index, heard_index) where op is
    'ok', 'wrong', 'missed' or 'extra'.
    """
    t = [p for _, p in target]
    h = [p for _, p in heard]
    n, m = len(t), len(h)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i
    for j in range(1, m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = 0 if same_note(t[i - 1], h[j - 1], octave_tolerant) else 1
            cost[i][j] = min(cost[i - 1][j - 1] + sub, cost[i - 1][j] + 1, cost[i][j - 1] + 1)
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            sub = 0 if same_note(t[i - 1], h[j - 1], octave_tolerant) else 1
            if cost[i][j] == cost[i - 1][j - 1] + sub:
                ops.append(("ok" if sub == 0 else "wrong", i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            ops.append(("missed", i - 1, None))
            i -= 1
        else:
            ops.append(("extra", None, j - 1))
            j -= 1
    return list(reversed(ops))


def timing_report(target, heard, ops):
    """For MIDI targets: compare the gap between each pair of back-to-back
    right notes with the gap in the file, after matching the kid's overall
    tempo. A skipped note doesn't count as a timing error."""
    matched = {ti: hi for op, ti, hi in ops if op == "ok"}
    gaps = []
    for ti, hi in matched.items():
        if ti + 1 in matched and target[ti][0] is not None:
            t_gap = target[ti + 1][0] - target[ti][0]
            h_gap = heard[matched[ti + 1]][0] - heard[hi][0]
            if t_gap > 0:
                gaps.append((t_gap, h_gap))
    if len(gaps) < 3:
        return None
    ratios = sorted(h / t for t, h in gaps)
    tempo = ratios[len(ratios) // 2]  # median: how much slower/faster than the file
    errs = [abs(h - tempo * t) * 1000 for t, h in gaps]
    return {"tempo_ratio": 1 / tempo if tempo else None,
            "mean_ms": sum(errs) / len(errs), "max_ms": max(errs)}


def score(target_path, recording, octave_tolerant=True, verbose=True):
    target = load_target(target_path)
    heard = hear_notes(recording)
    # Drop notes far outside the piece's range: usually overtones or noise.
    lo = min(p for _, p in target) - 12
    hi = max(p for _, p in target) + 12
    heard = [(t, p) for t, p in heard if lo <= p <= hi]
    ops = align(target, heard, octave_tolerant)
    ok = sum(1 for o in ops if o[0] == "ok")
    mistakes = [o for o in ops if o[0] != "ok"]
    accuracy = 100.0 * ok / len(target) if target else 0.0
    timing = timing_report(target, heard, ops)
    if verbose:
        print(f"\n{Path(recording).name} vs {Path(target_path).name}")
        print(f"  target notes {len(target)}, heard {len(heard)}, right {ok}, accuracy {accuracy:.0f}%")
        print("  heard: " + " ".join(midi_to_name(p) for _, p in heard))
        for op, ti, hi in mistakes:
            if op == "wrong":
                print(f"  wrong  at {heard[hi][0]:6.2f}s: played {midi_to_name(heard[hi][1])}, "
                      f"expected {midi_to_name(target[ti][1])} (note {ti + 1})")
            elif op == "missed":
                print(f"  missed note {ti + 1}: {midi_to_name(target[ti][1])}")
            else:
                print(f"  extra  at {heard[hi][0]:6.2f}s: {midi_to_name(heard[hi][1])}")
        if timing:
            print(f"  timing: off by {timing['mean_ms']:.0f} ms on average, "
                  f"worst {timing['max_ms']:.0f} ms (played at {timing['tempo_ratio']:.2f}x the file's speed)")
    return {"accuracy": accuracy, "mistakes": len(mistakes), "heard": len(heard),
            "target": len(target), "timing": timing}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?")
    ap.add_argument("recordings", nargs="*")
    ap.add_argument("--batch", help="CSV with recording,target,expected_mistakes")
    ap.add_argument("--exact-octave", action="store_true",
                    help="count a right note in the wrong octave as wrong")
    args = ap.parse_args()
    tol = not args.exact_octave

    if args.batch:
        rows = list(csv.DictReader(open(args.batch)))
        base = Path(args.batch).parent
        hits = 0
        print("recording,accuracy,found_mistakes,expected_mistakes,match")
        for r in rows:
            res = score(base / r["target"], base / r["recording"], tol, verbose=False)
            exp = r.get("expected_mistakes", "").strip()
            match = "" if exp == "" else ("yes" if int(exp) == res["mistakes"] else "no")
            hits += match == "yes"
            print(f"{r['recording']},{res['accuracy']:.0f}%,{res['mistakes']},{exp},{match}")
        known = sum(1 for r in rows if r.get("expected_mistakes", "").strip())
        if known:
            print(f"\nBasic Pitch counted the mistakes exactly right on {hits} of {known} clips.")
        return
    if not args.target or not args.recordings:
        ap.print_help()
        sys.exit(1)
    for rec in args.recordings:
        score(args.target, rec, tol)


if __name__ == "__main__":
    main()
