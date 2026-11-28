"""Fill the official ICAC 2026 template with the talk content.

The template lives in ``assets/icac-2026-template.pptx``. Figures are built by
``make_deck.py`` and placed into the template's content areas.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import qrcode
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from make_deck import fig_level, fig_skill_f1

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "assets" / "icac-2026-template.pptx"
FIGURES = HERE / "assets" / "figures"
OUT = HERE / "deck"
PAPER_ID = "564"
DECK = OUT / f"ICAC2026_{PAPER_ID}.pptx"
GITHUB_URL = "https://github.com/prdai/sfia-structured-skill-extraction"

NAVY = RGBColor(0x15, 0x2E, 0x50)
BODY = RGBColor(0x58, 0x67, 0x7A)


def set_text(shape, lines: list[str], size: float, color=BODY, space: int = 8) -> None:
    frame = shape.text_frame
    frame.clear()
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.space_after = Pt(space)
        for run in paragraph.runs:
            run.font.size = Pt(size)
            run.font.name = "Times New Roman"
            run.font.color.rgb = color


def drop(shape) -> None:
    shape._element.getparent().remove(shape._element)


def add_pic(slide, path: Path, x: float, y: float, width: float):
    with Image.open(path) as image:
        height = width * image.height / image.width
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(width), height=Inches(height))


def cite(slide, text: str) -> None:
    box = slide.shapes.add_textbox(Inches(10.2), Inches(5.72), Inches(2.0), Inches(0.25))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = False
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = PP_ALIGN.RIGHT
    for run in paragraph.runs:
        run.font.size = Pt(11)
        run.font.name = "Times New Roman"
        run.font.color.rgb = NAVY
        run.font.bold = True


def build() -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEMPLATE, DECK)
    deck = Presentation(DECK)

    title = deck.slides[0]
    for shape in title.shapes:
        if shape.name == "Presentation title":
            shape.width = Inches(11.5)
            shape.text_frame.clear()
            for index, line in enumerate(
                (
                    "From Lexical Baselines to Agentic Retrieval-Augmented Generation:",
                    "Structured Skill and Responsibility-Level Extraction",
                    "with the SFIA Framework",
                )
            ):
                paragraph = shape.text_frame.paragraphs[0] if index == 0 else shape.text_frame.add_paragraph()
                paragraph.text = line
                for run in paragraph.runs:
                    run.font.size = Pt(24)
                    run.font.name = "Times New Roman"
                    run.font.bold = True
                    run.font.color.rgb = NAVY
        elif shape.name == "Presenter name":
            set_text(shape, ["Presenter Name: Ranuga Disansa"], 16, NAVY)
        elif shape.name == "Coauthors":
            set_text(shape, ["Co-Authors\u2019 Names: U. S. Samarasinghe, Lasith Gunawardena"], 15, NAVY)
        elif shape.name == "Affiliation":
            set_text(shape, ["Affiliation: Informatics Institute of Technology, Colombo, Sri Lanka", "Department of Information Technology, University of Sri Jayewardenepura, Colombo, Sri Lanka"], 14, NAVY, space=0)

    context = deck.slides[1]
    drop(next(s for s in context.shapes if s.name == "Content placeholder"))
    box = context.shapes.add_textbox(Inches(0.85), Inches(1.55), Inches(5.2), Inches(4.0))
    box.text_frame.word_wrap = True
    frame = box.text_frame
    for index, line in enumerate(
        (
            "Tools emit inconsistent tags and drop the level.",
            "SFIA defines 147 skills at seven levels, from autonomy to influence.",
            "Purpose: map free text to SFIA skills and levels, then compare five matchers on 30 expert-mapped roles.",
        )
    ):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.space_after = Pt(14)
        for run in paragraph.runs:
            run.font.size = Pt(19)
            run.font.name = "Times New Roman"
            run.font.color.rgb = BODY
    add_pic(context, FIGURES / "flat-tags.png", 6.25, 2.0, 6.65)
    cite(context, "[1]")

    novelty = deck.slides[2]
    set_text(
        next(s for s in novelty.shapes if s.name == "Content placeholder"),
        [
            "Gap: ESCO and O*NET are regional frameworks.",
            "Gap: prior matchers predict skills but not levels.",
            "Gap: no LLM extraction targets SFIA.",
            "Gap: no multi-agent work on a closed taxonomy.",
            "Contribution: a validated SFIA 9 corpus of 669 records.",
            "Contribution: five matchers and a released harness.",
        ],
        22,
        space=14,
    )
    cite(novelty, "[2, 3]")

    methodology = deck.slides[3]
    drop(next(s for s in methodology.shapes if s.name == "Content placeholder"))
    add_pic(methodology, FIGURES / "corpus-pipeline-figma.png", 1.55, 1.55, 10.2)
    cite(methodology, "[4\u20138]")

    results = deck.slides[4]
    drop(next(s for s in results.shapes if s.name == "Content placeholder"))
    add_pic(results, fig_skill_f1(), 1.55, 1.55, 10.2)

    results_cont = deck.slides[5]
    drop(next(s for s in results_cont.shapes if s.name == "Content placeholder"))
    add_pic(results_cont, fig_level(), 1.3, 1.6, 10.8)

    conclusion = deck.slides[6]
    set_text(
        next(s for s in conclusion.shapes if s.name == "Content placeholder"),
        [
            "Make the level a direct prediction, not a by-product of similarity.",
            "Dense retrieval wins skill F1 but is the worst level predictor.",
            "More agents add cost without accuracy.",
            "SFIA 7 gold standard caps recall near 0.69.",
            "Corpus, code and explorer are released.",
        ],
        20,
        space=10,
    )
    cite(conclusion, "[1, 2]")
    qr_path = FIGURES / "qr-github.png"
    qrcode.make(GITHUB_URL).convert("RGB").save(qr_path)
    add_pic(conclusion, qr_path, 9.95, 1.85, 2.0)
    caption = conclusion.shapes.add_textbox(Inches(9.75), Inches(3.95), Inches(2.4), Inches(0.3))
    caption.text_frame.clear()
    paragraph = caption.text_frame.paragraphs[0]
    paragraph.text = "GitHub"
    paragraph.alignment = PP_ALIGN.CENTER
    for run in paragraph.runs:
        run.font.size = Pt(14)
        run.font.name = "Times New Roman"
        run.font.color.rgb = NAVY
        run.font.bold = True

    references = deck.slides[7]
    set_text(
        next(s for s in references.shapes if s.name == "Content placeholder"),
        [
            "[1] SFIA Foundation. (2024). Skills Framework for the Information Age (SFIA 9). https://sfia-online.org/en/sfia-9",
            "[2] European Commission. (2024). European Skills, Competences, Qualifications and Occupations (ESCO). https://esco.ec.europa.eu",
            "[3] National Center for O*NET Development. (2024). O*NET OnLine. U.S. Department of Labor. https://www.onetonline.org",
            "[4] European Committee for Standardization. (2018). European ICT professionals role profiles - Part 1: 30 ICT profiles (CWA 16458-1:2018). CEN.",
            "[5] Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. Foundations and Trends in Information Retrieval, 3(4), 333-389. https://doi.org/10.1561/1500000019",
            "[6] Qwen Team. (2025). Qwen3 Embedding: Advancing text embedding and reranking through foundation models (arXiv:2506.05176). arXiv. https://arxiv.org/abs/2506.05176",
            "[7] Grattafiori, A., et al. (2024). The Llama 3 herd of models (arXiv:2407.21783). arXiv. https://arxiv.org/abs/2407.21783",
            "[8] CrewAI. (2025). CrewAI documentation. https://docs.crewai.com",
        ],
        12.5,
        space=4,
    )

    architecture = deck.slides.add_slide(deck.slide_layouts[5])
    architecture.shapes.add_picture(
        str(FIGURES / "architecture-slide.png"),
        0,
        0,
        width=deck.slide_width,
        height=deck.slide_height,
    )
    slide_ids = deck.slides._sldIdLst
    architecture_id = list(slide_ids)[-1]
    slide_ids.remove(architecture_id)
    slide_ids.insert(4, architecture_id)
    for index in range(5, 9):
        for shape in deck.slides[index].shapes:
            if shape.name == "Slide number":
                frame = shape.text_frame
                frame.clear()
                paragraph = frame.paragraphs[0]
                paragraph.text = str(index + 1)
                paragraph.alignment = PP_ALIGN.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(15)
                    run.font.name = "Times New Roman"
                    run.font.color.rgb = RGBColor(0x94, 0x6F, 0x2E)

    deck.save(DECK)
    return DECK


def export_pdf(deck_path: Path) -> None:
    if shutil.which("libreoffice") is None:
        print("libreoffice not found; PPTX written without a PDF")
        return
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(deck_path)],
        check=True,
        capture_output=True,
    )


def main() -> None:
    deck_path = build()
    export_pdf(deck_path)
    print(f"wrote {deck_path}")


if __name__ == "__main__":
    main()
