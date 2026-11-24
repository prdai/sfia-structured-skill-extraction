# ICAC 2026 talk

Code-generated slide deck for the ICAC 2026 paper talk. The script reads
`evals/results.json`, draws the figures with matplotlib, renders the QR links
with qrcode, and writes an editable PPTX plus a PDF with speaker notes.

## Build

```bash
uv run --with matplotlib --with python-pptx --with pillow --with "qrcode[pil]" python talk/make_deck.py
```

Outputs:

- `deck/sfia-icac-2026.pptx` — editable slides with speaker notes
- `deck/sfia-icac-2026.pdf` — rendered deck

## Structure

- `make_deck.py` — slide list, figure builders, PPTX/PDF assembly
- `assets/figures/` — generated figures
- `deck/` — build output

Slides are defined in `slides()` in `make_deck.py`. Main results come from
`evals/results.json`.

## Timing

ICAC 2026 does not publish a per-paper slot. The deck targets a 10-minute slot:
12 slides, with the agenda following the paper structure from background to
results. Speaker notes carry the detail that is not on the slides.
