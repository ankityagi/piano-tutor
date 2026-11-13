# piano-tutor

**North star: every kid's home practice gets heard, scored and coached, and parents can see it happened and that it's working.**

Lesson apps like Simply Piano, Yousician, Flowkey and Fender Play already teach. What none of them does is close the loop on practice at home. A parent can't tell whether the 20 minutes happened, whether the piece is getting better, or what to nudge on. Practice trackers are timers and logs that kids fill in themselves, and none of them listens.

piano-tutor is the practice check, not another lesson library.

## What it does

1. **Your kid plays the assigned piece** into the phone. No app store, no special gear: a web page records it.
2. **The app listens and scores it:** right notes, wrong notes, missed notes and timing, against the piece it was supposed to be.
3. **Your kid gets one tip,** short and encouraging, about the next thing to fix.
4. **You get a weekly summary:** how often they practised, for how long, and how the scores are moving.

Piano and guitar, starting with kids who are beginners.

## Principles

- **Phone first.** The mic is the default; a USB keyboard is an option for exact notes.
- **Small and honest.** Score what it can hear reliably and say nothing it can't. A kid stops trusting a tool that marks a clean take wrong.
- **Encourage, don't nag.** One tip per session, no streak guilt.
- **Bring your own pieces.** Teacher-assigned and public-domain music, no licensed song catalog.

## Roadmap

| Stage | What | Status |
|---|---|---|
| 0 | [Accuracy test](accuracy-test/): can Basic Pitch hear real phone recordings well enough to score them? | Script ready, needs real clips |
| 1 | Practice check MVP: phone page, scoring server, LLM tip, weekly parent summary | Next, if stage 0 passes |
| 2 | USB keyboard input through Web MIDI, same scorer | Later |
| 3 | Teacher assigns pieces and sees practice results | Later |
| 4 | Hand position feedback from the camera, live feedback while playing | Someday |

## Stack

- **Hearing notes:** [Basic Pitch](https://github.com/spotify/basic-pitch) (Spotify, Apache 2.0) turns a recording into notes.
- **Scoring:** align heard notes to the target piece, then score notes and timing.
- **Coaching:** an LLM writes the kid's tip and the parent summary from the score.
- **Later:** Web MIDI for keyboards, MediaPipe hand tracking for posture.

## Not doing

- A lesson library or song catalog. Existing apps do that well.
- Live, note-by-note feedback in the first version. Scoring after the take is simpler and more accurate.
