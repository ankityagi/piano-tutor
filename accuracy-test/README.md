# Basic Pitch accuracy test

One question before building anything: can Basic Pitch tell right notes from wrong ones on real phone recordings of a kid practising?

## Setup (once)
- Python 3.10 on an Apple-silicon Mac (Basic Pitch's own note), 3.11 elsewhere. It does not install on 3.13.
- `brew install ffmpeg` so it can read the phone's .m4a files.
- `python3.10 -m venv venv && ./venv/bin/pip install -r requirements.txt`

## Run
- One clip: `./venv/bin/python accuracy_test.py twinkle.txt clean_take.m4a`
- All clips: `./venv/bin/python accuracy_test.py --batch clips.csv`

The target is a .txt of note names in order (`C4 C4 G4 G4 ...`, right hand only) or a .mid file. A .mid also gives a timing score. Wrong octave counts as right unless you add `--exact-octave`.

## The test (about 20 minutes)
1. Pick a piece your kid already knows and write its notes in a .txt (twinkle.txt is an example).
2. Record on the phone (Voice Memos), phone about a foot or two from the instrument:
   - a clean take
   - a take with 2 mistakes made on purpose (write down how many)
   - a clean take with the TV or room noise on
   - a faster take
   - a short single-note guitar riff, with its own .txt
3. Copy the clips next to the script, fill in clips.csv (expected_mistakes = how many mistakes were really made), run the batch.

Go: it counts the mistakes right on at least 4 of 5 clips and never flags a clean take.
No-go: it flags mistakes on clean takes. A kid stops trusting it fast, so switch to the USB keyboard route.
