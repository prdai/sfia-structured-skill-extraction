# ICAC 2026 talk

Code-generated slide deck for the ICAC 2026 paper talk. The script reads
`evals/results.json`, draws the figures with matplotlib, captures the live
explorer with headless Chromium, and writes an editable PPTX plus a PDF with
speaker notes.

## Build

```bash
uv run --with matplotlib --with python-pptx --with pillow python talk/make_deck.py
```

Outputs:

- `deck/sfia-icac-2026.pptx` — editable slides with speaker notes
- `deck/sfia-icac-2026.pdf` — rendered deck

Screenshots are cached in `assets/screens/`. Pass `--refresh-screens` to
recapture `sfia.prdai.dev`; without Chromium the script falls back to the
cached images.

## Structure

- `make_deck.py` — slide list, figure builders, PPTX/PDF assembly
- `assets/screens/` — captured screenshots
- `assets/figures/` — generated figures
- `deck/` — build output

Slides are defined in `slides()` in `make_deck.py`. Main results come from
`evals/results.json`; the zero-shot model sweep is transcribed from the paper
and lives in `SWEEP`.

## Timing

ICAC 2026 does not publish a per-paper slot. The deck targets a 15-minute slot:
12 main slides (about 12 minutes) plus a six-slide appendix for questions.
Trim the model-sweep slide first if the slot is shorter.
