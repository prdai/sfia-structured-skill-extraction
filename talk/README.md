# ICAC 2026 talk

Slides for the ICAC 2026 paper talk, built into the official conference
template. `make_deck.py` draws the figures from `evals/results.json`;
`build_template_deck.py` places them into
`assets/icac-2026-template.pptx` and adds the title, copy, references, and
QR code.

## Build

```bash
uv run --with matplotlib --with python-pptx --with pillow --with "qrcode[pil]" python talk/build_template_deck.py
```

Outputs:

- `deck/sfia-icac-2026.pptx` — template deck, editable
- `deck/sfia-icac-2026.pdf` — rendered deck

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
