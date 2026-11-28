"""Build the ICAC 2026 talk deck from the released evaluation results."""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
FIGURES = ASSETS / "figures"
OUT = HERE / "deck"

SIZE = (13.333333, 7.5)
INK = "#0f172a"
SECONDARY = "#475569"
MUTED = "#94a3b8"
GRID = "#e2e8f0"
TITLE = "Mapping Free Text to SFIA Skills and Responsibility Levels"

STRATEGIES = (
    ("keyword-bm25", "BM25 lexical", "#94a3b8"),
    ("embedding-qwen3-llm-rerank", "Dense + rerank", "#0e7490"),
    ("llm-workers-ai", "Zero-shot LLM", "#7c3aed"),
    ("agentic-rag-crewai", "Agentic RAG", "#2563eb"),
    ("multi-agent-rag-crewai", "Multi-agent crew", "#dc2626"),
)

RESULTS = json.loads((ROOT / "evals" / "results.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Slide:
    title: str
    notes: str
    lines: tuple[str, ...] = ()
    image: Path | None = None
    kind: str = "bullets"


def metric(key: str, name: str) -> float:
    return RESULTS[key][name]


def save_figure(fig: Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=200, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def style_axis(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=SECONDARY, labelsize=14, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def fig_corpus() -> Path:
    stages = (
        ("1", "Crawl", "5,461", "pages", "Serverless browser rendering"),
        ("2", "Filter", "465", "content pages", "147 skill \u00b7 318 documentation"),
        ("3", "Brief", "114", "pages \u2192 notes", "Scout, then one synthesizer"),
        ("4", "Extract", "672", "pairs", "One call per skill page"),
        ("5", "Validate", "3", "rejected", "0 range rejects \u00b7 3 verbatim"),
        ("6", "Release", "669", "records", "All 147 SFIA 9 skills"),
    )
    w, h = 12.53, 5.45
    card_w, card_h = 3.65, 2.1
    xs = (0.15, 4.44, 8.73)
    top_y, bottom_y = 3.2, 0.2
    positions = (
        (xs[0], top_y), (xs[1], top_y), (xs[2], top_y),
        (xs[2], bottom_y), (xs[1], bottom_y), (xs[0], bottom_y),
    )
    with plt.rc_context({"font.family": ["Liberation Sans", "DejaVu Sans"]}):
        fig = plt.figure(figsize=(w, h))
        ax = fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, w)
        ax.set_ylim(0, h)
        ax.axis("off")
        for (num, name, value, unit, detail), (x, y) in zip(stages, positions):
            ax.add_patch(
                FancyBboxPatch(
                    (x, y), card_w, card_h,
                    boxstyle="round,pad=0.0,rounding_size=0.16",
                    facecolor="white", edgecolor=GRID, linewidth=1.4, zorder=2,
                )
            )
            ax.add_patch(
                FancyBboxPatch(
                    (x + 0.02, y + 0.02), 0.10, card_h - 0.04,
                    boxstyle="round,pad=0.0,rounding_size=0.05",
                    facecolor="#0e7490", edgecolor="none", zorder=3,
                )
            )
            ax.add_patch(Circle((x + 0.48, y + card_h - 0.45), 0.25, facecolor="#155e75", edgecolor="none", zorder=3))
            ax.text(x + 0.48, y + card_h - 0.46, num, ha="center", va="center",
                    fontsize=15, color="white", fontweight="bold", zorder=4)
            ax.text(x + 0.86, y + card_h - 0.45, name.upper(), ha="left", va="center",
                    fontsize=12.5, color="#0e7490", fontweight="bold", zorder=4)
            ax.text(x + 0.34, y + card_h - 1.22, value, ha="left", va="baseline",
                    fontsize=27, color=INK, fontweight="bold", zorder=4)
            value_width = len(value) * 0.60 * 27 / 72
            ax.text(x + 0.34 + value_width + 0.06, y + card_h - 1.24, unit, ha="left", va="baseline",
                    fontsize=13, color=SECONDARY, zorder=4)
            ax.text(x + 0.34, y + 0.30, detail, ha="left", va="baseline",
                    fontsize=11.5, color=SECONDARY, zorder=4)

        def arrow(start, end):
            ax.add_patch(
                FancyArrowPatch(
                    start, end, arrowstyle="-|>", mutation_scale=20,
                    color=MUTED, linewidth=2.8, shrinkA=0, shrinkB=0,
                    zorder=1, joinstyle="round", capstyle="round",
                )
            )

        mid_top = top_y + card_h / 2
        mid_bottom = bottom_y + card_h / 2
        arrow((xs[0] + card_w + 0.06, mid_top), (xs[1] - 0.06, mid_top))
        arrow((xs[1] + card_w + 0.06, mid_top), (xs[2] - 0.06, mid_top))
        arrow((xs[2] + card_w / 2, top_y - 0.06), (xs[2] + card_w / 2, bottom_y + card_h + 0.06))
        arrow((xs[2] - 0.06, mid_bottom), (xs[1] + card_w + 0.06, mid_bottom))
        arrow((xs[1] - 0.06, mid_bottom), (xs[0] + card_w + 0.06, mid_bottom))
        FIGURES.mkdir(parents=True, exist_ok=True)
        path = FIGURES / "corpus-pipeline.png"
        fig.savefig(path, dpi=200, facecolor="white")
        plt.close(fig)
    return path

def fig_skill_f1() -> Path:
    labels = [label for _, label, _ in STRATEGIES]
    values = [metric(key, "mean_f1") for key, _, _ in STRATEGIES]
    colors = [color for _, _, color in STRATEGIES]
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    bars = ax.barh(labels, values, color=colors, height=0.62)
    ax.invert_yaxis()
    for bar, value in zip(bars, values):
        ax.text(value + 0.004, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=15, color=INK)
    ax.set_xlim(0, 0.27)
    ax.set_xlabel("Skill F1 (higher is better)", fontsize=14, color=SECONDARY)
    style_axis(ax)
    return save_figure(fig, "skill-f1.png")


def fig_level() -> Path:
    labels = [label for _, label, _ in STRATEGIES]
    colors = [color for _, _, color in STRATEGIES]
    mae = [metric(key, "mean_level_mae") for key, _, _ in STRATEGIES]
    exact = [metric(key, "mean_level_accuracy_exact") for key, _, _ in STRATEGIES]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.6))
    for ax, values, xmax, title, fmt in (
        (axes[0], mae, 1.85, "Level MAE (lower is better)", "{:.2f}"),
        (axes[1], exact, 0.62, "Exact level accuracy (higher is better)", "{:.3f}"),
    ):
        bars = ax.barh(labels, values, color=colors, height=0.62)
        ax.invert_yaxis()
        ax.set_xlim(0, xmax)
        ax.set_xlabel(title, fontsize=13.5, color=SECONDARY)
        for bar, value in zip(bars, values):
            ax.text(value + xmax * 0.015, bar.get_y() + bar.get_height() / 2, fmt.format(value), va="center", fontsize=14, color=INK)
        style_axis(ax)
    fig.tight_layout(w_pad=2.5)
    return save_figure(fig, "level-accuracy.png")


def fig_links() -> Path:
    import numpy as np
    import qrcode

    links = (
        ("https://github.com/prdai/sfia-structured-skill-extraction", "GitHub repo", "github.com/prdai/sfia-structured-skill-extraction"),
        ("https://sfia.prdai.dev", "Live demo", "sfia.prdai.dev"),
    )
    with plt.rc_context({"font.family": ["Liberation Sans", "DejaVu Sans"]}):
        fig = plt.figure(figsize=(7.0, 3.5), facecolor="white")
        left = 0.06
        for i, (url, caption, sub) in enumerate(links):
            code = qrcode.make(url).convert("L")
            ax = fig.add_axes((left + i * 0.47, 0.26, 0.38, 0.64))
            ax.imshow(np.array(code), cmap="gray", vmin=0, vmax=255)
            ax.axis("off")
            fig.text(left + i * 0.47 + 0.19, 0.17, caption, ha="center", va="center",
                     fontsize=15, fontweight="bold", color=INK)
            fig.text(left + i * 0.47 + 0.19, 0.10, sub, ha="center", va="center",
                     fontsize=9.5, color=SECONDARY)
        FIGURES.mkdir(parents=True, exist_ok=True)
        path = FIGURES / "links.png"
        fig.savefig(path, dpi=200, facecolor="white")
        plt.close(fig)
    return path


def slides() -> list[Slide]:
    return [
        Slide(
            TITLE,
            "ICAC 2026, 12-minute slot: ten minutes of content and two minutes of questions. "
            "Everything shown is released: corpus, five matchers, evaluation harness, and the live explorer. "
            "The paper is on arXiv, 2609.35806.",
            lines=(
                "Five techniques, one dataset, one evaluation harness",
                "ICAC 2026  \u00b7  9-10 December 2026  \u00b7  SLIIT, Malabe",
                "Ranuga Disansa  \u00b7  U. S. Samarasinghe  \u00b7  Lasith Gunawardena",
            ),
            kind="title",
        ),
        Slide(
            "Agenda",
            "Seven short sections. Keep the method and results sections to the clock.",
            lines=(
                "Background",
                "Existing works",
                "Identified gap",
                "Problem statement",
                "Aim and objectives",
                "Methodology",
                "Results",
            ),
        ),
        Slide(
            "Background",
            "SFIA attaches every skill to one or more of seven responsibility levels, defined by autonomy, influence, complexity and business skill. "
            "That level axis is what makes this structured prediction rather than multi-label classification.",
            lines=(
                "SFIA is a public framework of 147 digital skills.",
                "Each skill is defined at one or more of seven levels.",
                "A level describes autonomy, influence and complexity.",
                "Hiring tools usually tag skills without the level.",
            ),
        ),
        Slide(
            "Existing works and the gap",
            "ESCO and O*NET describe skills without a comparable SFIA level axis. Prior extraction work predicts flat tags. "
            "We found no open corpus and no benchmark that covers skill and level together.",
            lines=(
                "ESCO and O*NET describe skills but not SFIA levels.",
                "Earlier extraction models return flat skill tags.",
                "No open dataset links SFIA skills to levels.",
                "No benchmark tests skill and level together.",
            ),
        ),
        Slide(
            "Problem and objectives",
            "The task is free text in, a set of skill and level pairs out, from a closed vocabulary. Four goals, all released together.",
            lines=(
                "Input: free text, such as a role description.",
                "Output: SFIA skill and level pairs.",
                "Goal 1: build a validated SFIA 9 corpus.",
                "Goal 2: compare five matching strategies.",
                "Goal 3: evaluate on 30 expert-mapped roles.",
            ),
        ),
        Slide(
            "Methodology: how the corpus is built",
            "The crawler stores 5,461 pages as markdown and HTML. Downstream stages use 147 skill pages and 318 documentation pages. "
            "A scout reads the documentation, a synthesizer condenses its notes, and one extractor call per skill page returns (code, level, text, reasoning). "
            "A deterministic guard checks every pair against the SFIA 9 chart. The verifier rejected 3 records, so the release holds 669 records covering all 147 skills.",
            image=fig_corpus(),
            kind="figure",
        ),
        Slide(
            "Methodology: how we evaluate",
            "The gold standard is 30 European ICT role profiles, each mapped by experts to SFIA 7 skills and levels. "
            "One query per role, the summary statement. Skill identification is scored with precision, recall and F1. "
            "Level is scored with MAE, exact match, and within one. Speed is wall-clock seconds per record.",
            lines=(
                "Test set: 30 European ICT role profiles.",
                "Experts mapped each role to SFIA skills and levels.",
                "One query per role: its summary statement.",
                "Skills scored by precision, recall and F1.",
                "Level scored by error, exact match and speed.",
            ),
        ),
        Slide(
            "Methodology: five matchers compared",
            "Five matchers behind one interface. BM25 is the lexical baseline. Dense rerank embeds every record with Qwen3, retrieves the top 20, then reranks pointwise with Llama-3.3-70B. "
            "Zero-shot LLM makes one schema-constrained call over 147 names. Agentic RAG gives one CrewAI agent dense and BM25 tools. "
            "The multi-agent crew chains retriever, matcher and verifier, sharing tools and one model.",
            lines=(
                "BM25: ranks records by keyword overlap.",
                "Dense + rerank: embeddings, then a reranker.",
                "Zero-shot LLM: one structured call, 147 skills.",
                "Agentic RAG: one agent with search tools.",
                "Multi-agent: retriever, matcher and verifier.",
            ),
        ),
        Slide(
            "Results: retrieval finds more skills",
            "Dense retrieval records the highest skill F1, 0.232, through the highest recall, 0.243. The agentic strategies follow at 0.213 and 0.212. "
            "The margin is the same order as run-to-run variance, so we claim no strict ranking. "
            "The stable pattern is the trade-off: zero-shot is the precision extreme, 0.436 at recall 0.117, while retrieval buys recall back.",
            image=fig_skill_f1(),
            kind="figure",
        ),
        Slide(
            "Results: explicit levels predict better",
            "On the level dimension the ranking inverts. Dense retrieval is the worst level predictor by far: MAE 1.60, exact 0.181. "
            "Strategies that emit the level as an explicit decision sit in a different regime: single agent reaches MAE 0.68 and exact 0.526, zero-shot 0.74 MAE and 0.895 within one level.",
            image=fig_level(),
            kind="figure",
        ),
        Slide(
            "Takeaways",
            "Four points. First, make the level an explicit output, not a by-product of similarity. Second, dense retrieval maximises skill F1 but is the worst level predictor. "
            "Third, more agents add cost, not accuracy. Fourth, recall is capped by the SFIA 7 gold standard, and the corpus, matchers and harness are all released.",
            lines=(
                "Ask for the level explicitly, not as a side effect.",
                "Dense retrieval wins skill F1 but loses on level.",
                "More agents add cost without accuracy.",
                "Recall is capped by the SFIA 7 gold standard.",
                "Corpus, code and explorer are all released.",
            ),
        ),
        Slide(
            "Links",
            "The corpus and results are checked in, so the matchers and harness can be rerun without crawling SFIA. "
            "The commands are in the repository README. The explorer source is in explorer/.",
            image=fig_links(),
            kind="image",
        ),
    ]


def chart_image(path: Path) -> Image.Image:
    with Image.open(path) as original:
        rgb = original.convert("RGB")
        return rgb.crop((0, round(rgb.height * 0.02), rgb.width, rgb.height))


def render(slide: Slide) -> Figure:
    fig = plt.figure(figsize=SIZE, facecolor="white")
    if slide.kind in {"title", "section"}:
        fig.text(
            0.055,
            0.73,
            textwrap.fill(slide.title, width=36),
            fontsize=34 if slide.kind == "title" else 32,
            fontweight="bold",
            ha="left",
            va="top",
            color=INK,
        )
        for i, line in enumerate(slide.lines):
            fig.text(0.055, 0.38 - i * 0.085, line, fontsize=19 if i == 0 else 16, color=SECONDARY)
        return fig
    if slide.kind == "image":
        if slide.image is None:
            raise ValueError(f"image slide has no image: {slide.title}")
        image = chart_image(slide.image)
        box = (0.06, 0.06, 0.88, 0.88)
        available_width, available_height = SIZE[0] * box[2], SIZE[1] * box[3]
        scale = min(available_width / image.width, available_height / image.height)
        width, height = image.width * scale / SIZE[0], image.height * scale / SIZE[1]
        left = box[0] + (box[2] - width) / 2
        bottom = box[1] + (box[3] - height) / 2
        ax = fig.add_axes((left, bottom, width, height))
        ax.imshow(image)
        ax.set_axis_off()
        return fig
    title = textwrap.fill(slide.title, width=58)
    fig.text(0.045, 0.88, title, fontsize=28, fontweight="bold", ha="left", va="top", color=INK)
    if slide.kind in {"bullets", "bullets_image"}:
        cursor = 0.76
        for line in slide.lines:
            wrapped = textwrap.fill(line, width=58, subsequent_indent="   ")
            fig.text(
                0.06,
                cursor,
                "•  " + wrapped,
                fontsize=26,
                ha="left",
                va="top",
                color=INK,
                linespacing=1.25,
            )
            cursor -= (wrapped.count("\n") + 1) * 0.056 + 0.042
        if slide.kind == "bullets":
            return fig
    if slide.image is None:
        raise ValueError(f"figure slide has no image: {slide.title}")
    image = chart_image(slide.image)
    box = (0.03, 0.03, 0.94, 0.79 if "\n" not in title else 0.72) if slide.kind == "figure" else (0.22, 0.01, 0.56, 0.52)
    available_width, available_height = SIZE[0] * box[2], SIZE[1] * box[3]
    scale = min(available_width / image.width, available_height / image.height)
    width, height = image.width * scale / SIZE[0], image.height * scale / SIZE[1]
    left = box[0] + (box[2] - width) / 2
    bottom = box[1] + (box[3] - height) / 2
    ax = fig.add_axes((left, bottom, width, height))
    ax.imshow(image)
    ax.set_axis_off()
    return fig


def add_slide(presentation: Presentation, page: Slide, fig: Figure) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for label in fig.texts:
        bounds = label.get_window_extent(renderer).transformed(fig.transFigure.inverted())
        left = bounds.x0 * SIZE[0]
        top = (1 - bounds.y1) * SIZE[1]
        box = slide.shapes.add_textbox(
            Inches(left),
            Inches(max(0, top - 0.025)),
            Inches(SIZE[0] - left - 0.25),
            Inches(bounds.height * SIZE[1] + 0.15),
        )
        frame = box.text_frame
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.word_wrap = False
        for i, line in enumerate(label.get_text().splitlines()):
            paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            paragraph.text = line
            paragraph.space_before = paragraph.space_after = Pt(0)
            paragraph.line_spacing = 1.15
            paragraph.font.name = "Arial"
            paragraph.font.size = Pt(label.get_fontsize())
            paragraph.font.bold = label.get_fontweight() == "bold"
            paragraph.font.color.rgb = RGBColor.from_string(label.get_color().lstrip("#"))
    if page.image is not None:
        image = BytesIO()
        chart_image(page.image).save(image, format="PNG")
        image.seek(0)
        bounds = fig.axes[0].get_position()
        slide.shapes.add_picture(
            image,
            Inches(bounds.x0 * SIZE[0]),
            Inches((1 - bounds.y1) * SIZE[1]),
            width=Inches(bounds.width * SIZE[0]),
            height=Inches(bounds.height * SIZE[1]),
        )
    slide.notes_slide.notes_text_frame.text = page.title + "\n\n" + page.notes


def write_deck(pages: list[Slide]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = (Inches(value) for value in SIZE)
    presentation.core_properties.title = TITLE
    presentation.core_properties.subject = "ICAC 2026, 9-10 December 2026, SLIIT, Malabe"
    presentation.core_properties.author = "Ranuga Disansa, U. S. Samarasinghe, Lasith Gunawardena"
    metadata = {
        "Title": TITLE,
        "Author": "Ranuga Disansa, U. S. Samarasinghe, Lasith Gunawardena",
        "Subject": "ICAC 2026 talk",
    }
    with PdfPages(OUT / "sfia-icac-2026.pdf", metadata=metadata) as pdf:
        for page in pages:
            fig = render(page)
            pdf.savefig(fig, facecolor="white")
            add_slide(presentation, page, fig)
            plt.close(fig)
    presentation.save(OUT / "sfia-icac-2026.pptx")


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.bbox": None})
    write_deck(slides())
    print(f"wrote {OUT / 'sfia-icac-2026.pptx'}")
    print(f"wrote {OUT / 'sfia-icac-2026.pdf'}")


if __name__ == "__main__":
    main()
