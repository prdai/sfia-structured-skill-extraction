# ICAC 2026 talk

Slides for the ICAC 2026 paper talk, built into the official conference
template. `make_deck.py` draws the figures from `evals/results.json`;
`build_template_deck.py` places them into
`assets/icac-2026-template.pptx` and adds the title, copy, references, and
QR code.

## Talk format

ICAC 2026 allows 12 minutes per presentation: 10 minutes of talk and 2
minutes of Q&A. Submit the slides as `ICAC2026_<PaperID>.pptx` by midnight on
2 December 2026.

## Build

```bash
uv run --with matplotlib --with python-pptx --with pillow --with "qrcode[pil]" python talk/build_template_deck.py
```

Outputs:

- `deck/sfia-icac-2026.pptx` — template deck, editable
- `deck/sfia-icac-2026.pdf` — rendered deck

Rename the PPTX to `ICAC2026_<PaperID>.pptx` before uploading.

The PDF is exported with LibreOffice when it is installed.

## Structure

The talk follows the template sections: Title, Context (Problem) & Purpose,
Novelty & Expected Contribution, Methodology, Results & Discussion, Results
Contd., Conclusion, References.

- `build_template_deck.py` — template assembly and text
- `make_deck.py` — figure builders (corpus pipeline, skill F1, level accuracy)
- `assets/icac-2026-template.pptx` — official ICAC 2026 template
- `assets/figures/` — generated figures and QR codes
- `deck/` — build output

References are APA 7 and appear both as in-slide markers and on the final
References slide.
