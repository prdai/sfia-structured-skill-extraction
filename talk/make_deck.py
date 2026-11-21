"""Build the ICAC 2026 talk deck from the released evaluation results."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
FIGURES = ASSETS / "figures"
SCREENS = ASSETS / "screens"
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

SWEEP = (
    ("Gemma-4-26B-A4B", 0.176, 0.368, 0.74, 0),
    ("Nemotron-3-120B", 0.174, 0.438, 0.88, 0),
    ("Llama-3.1-8B", 0.166, 0.194, 1.64, 0),
    ("Llama-4-Scout-17B", 0.153, 0.694, 0.36, 0),
    ("Qwen3-30B-A3B", 0.152, 0.400, 0.93, 0),
    ("Mistral-Small-3.1", 0.139, 0.393, 0.75, 0),
    ("Kimi-K2.6", 0.136, 0.286, 0.79, 3),
    ("Kimi-K2.7-Code", 0.134, 0.500, 0.50, 5),
    ("GLM-5.2", 0.123, 0.500, 0.58, 7),
    ("GLM-4.7-Flash", 0.100, 0.600, 0.40, 9),
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
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    stages = (
        ("1  Crawl", "5,461 pages", "Serverless browser rendering"),
        ("2  Filter", "465 content pages", "147 skill + 318 documentation"),
        ("3  Brief", "114 pages \u2192 notes", "Scout, then one synthesizer"),
        ("4  Extract", "672 pairs", "One call per skill page"),
        ("5  Validate", "3 rejected", "0 range rejects; 3 verbatim"),
        ("6  Release", "669 records", "All 147 SFIA 9 skills"),
    )
    width, height = 3.35, 1.45
    xs = (0.25, 4.425, 8.6, 8.6, 4.425, 0.25)
    ys = (2.75, 2.75, 2.75, 0.55, 0.55, 0.55)
    for (label, value, detail), x, y in zip(stages, xs, ys):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.02,rounding_size=0.12",
                facecolor="#f8fafc",
                edgecolor=GRID,
                linewidth=1.5,
            )
        )
        ax.text(x + 0.2, y + height - 0.28, label, fontsize=15, color="#0e7490", fontweight="bold")
        ax.text(x + 0.2, y + height - 0.68, value, fontsize=16, color=INK, fontweight="bold")
        ax.text(x + 0.2, y + 0.22, detail, fontsize=11, color=SECONDARY)
    arrows = (
        ((3.6, 3.47), (4.42, 3.47)),
        ((7.78, 3.47), (8.6, 3.47)),
        ((10.27, 2.73), (10.27, 2.02)),
        ((8.6, 1.27), (7.78, 1.27)),
        ((4.43, 1.27), (3.6, 1.27)),
    )
    for start, end in arrows:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=18,
                color=MUTED,
                linewidth=1.8,
                shrinkA=0,
                shrinkB=0,
            )
        )
    return save_figure(fig, "corpus-pipeline.png")


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


def fig_tradeoff() -> Path:
    offsets = {
        "keyword-bm25": (0, 18),
        "embedding-qwen3-llm-rerank": (0, 18),
        "llm-workers-ai": (0, 18),
        "agentic-rag-crewai": (-14, -42),
        "multi-agent-rag-crewai": (0, 18),
    }
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    for key, label, color in STRATEGIES:
        precision = metric(key, "mean_precision")
        recall = metric(key, "mean_recall")
        ax.scatter(recall, precision, s=260, color=color, edgecolor="white", linewidth=2, zorder=3)
        alignment = "right" if key == "agentic-rag-crewai" else "center"
        ax.annotate(
            f"{label}\nF1 {metric(key, 'mean_f1'):.3f}",
            (recall, precision),
            xytext=offsets[key],
            textcoords="offset points",
            fontsize=12,
            color=INK,
            ha=alignment,
        )
    ax.set_xlim(0, 0.30)
    ax.set_ylim(0, 0.52)
    ax.set_xlabel("Skill recall", fontsize=14, color=SECONDARY)
    ax.set_ylabel("Skill precision", fontsize=14, color=SECONDARY)
    ax.text(
        0.295,
        0.025,
        "Recall ceiling 0.69: gold standard uses SFIA 7 vocabulary",
        ha="right",
        va="bottom",
        fontsize=11,
        color=SECONDARY,
        style="italic",
    )
    ax.grid(color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=SECONDARY, labelsize=13, length=0)
    return save_figure(fig, "precision-recall.png")


def fmt_seconds(seconds: float) -> str:
    if seconds < 0.001:
        return "<0.001"
    if seconds < 1:
        return f"{seconds:.2f}"
    if seconds < 100:
        return f"{seconds:.1f}"
    return f"{seconds:.0f}"


def fig_cost() -> Path:
    offsets = {
        "keyword-bm25": (14, 10, "left"),
        "embedding-qwen3-llm-rerank": (14, 10, "left"),
        "llm-workers-ai": (14, 10, "left"),
        "agentic-rag-crewai": (-14, -46, "right"),
        "multi-agent-rag-crewai": (-10, 20, "right"),
    }
    fig, ax = plt.subplots(figsize=(10.4, 5.3))
    for key, label, color in STRATEGIES:
        seconds = metric(key, "mean_seconds_per_record")
        f1 = metric(key, "mean_f1")
        ax.scatter(seconds, f1, s=300, color=color, edgecolor="white", linewidth=2, zorder=3)
        dx, dy, alignment = offsets[key]
        ax.annotate(
            f"{label}\n{fmt_seconds(seconds)} s/record",
            (seconds, f1),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=11.5,
            color=INK,
            ha=alignment,
        )
    ax.set_xscale("log")
    ax.set_xlim(0.0004, 1200)
    ax.set_ylim(0.10, 0.26)
    ax.set_xlabel("Seconds per record (log scale, lower is better)", fontsize=14, color=SECONDARY)
    ax.set_ylabel("Skill F1", fontsize=14, color=SECONDARY)
    ax.grid(color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=SECONDARY, labelsize=13, length=0)
    return save_figure(fig, "cost-vs-f1.png")


def fig_sweep() -> Path:
    labels = [f"{row[0]} ({row[4]} failed)" if row[4] else row[0] for row in SWEEP]
    f1 = [row[1] for row in SWEEP]
    exact = [row[2] for row in SWEEP]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.2))
    for ax, values, xmax, title, fmt in (
        (axes[0], f1, 0.20, "Skill F1", "{:.3f}"),
        (axes[1], exact, 0.78, "Exact level accuracy", "{:.3f}"),
    ):
        bars = ax.barh(labels, values, color="#7c3aed", height=0.62)
        ax.invert_yaxis()
        ax.set_xlim(0, xmax)
        ax.set_xlabel(title, fontsize=13.5, color=SECONDARY)
        for bar, value in zip(bars, values):
            ax.text(value + xmax * 0.015, bar.get_y() + bar.get_height() / 2, fmt.format(value), va="center", fontsize=12, color=INK)
        style_axis(ax)
    fig.tight_layout(w_pad=2.5)
    return save_figure(fig, "zero-shot-sweep.png")


def fig_results_table() -> Path:
    columns = ("Strategy", "P", "R", "F1", "MAE", "Exact", "W1", "s/rec")
    rows = []
    for key, label, _ in STRATEGIES:
        seconds = metric(key, "mean_seconds_per_record")
        seconds_text = f"{seconds:.3f}" if seconds < 1 else f"{seconds:.0f}"
        rows.append(
            (
                label,
                f"{metric(key, 'mean_precision'):.3f}",
                f"{metric(key, 'mean_recall'):.3f}",
                f"{metric(key, 'mean_f1'):.3f}",
                f"{metric(key, 'mean_level_mae'):.2f}",
                f"{metric(key, 'mean_level_accuracy_exact'):.3f}",
                f"{metric(key, 'mean_level_accuracy_within_1'):.3f}",
                seconds_text,
            )
        )
    fig, ax = plt.subplots(figsize=(11.6, 3.9))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="right")
    table.auto_set_font_size(False)
    table.set_fontsize(13.5)
    table.scale(1, 2.1)
    for (row, column), cell in table.get_celld().items():
        cell.set_width(0.30 if column == 0 else 0.10)
        cell.set_edgecolor(GRID)
        cell.set_linewidth(1)
        if row == 0:
            cell.set_facecolor("#0f172a")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("white" if row % 2 else "#f8fafc")
            cell.set_text_props(color=INK)
        if column == 0:
            cell.set_text_props(ha="left", color=INK)
            cell._loc = "left"
    return save_figure(fig, "results-table.png")


def capture(name: str, url: str, refresh: bool, crop: tuple[int, int, int, int] | None = None) -> Path:
    target = SCREENS / f"{name}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not refresh:
        return target
    browser = next(
        (path for path in (shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("google-chrome")) if path),
        None,
    )
    if browser is None:
        if target.exists():
            print(f"no browser found; reusing cached {target.name}")
            return target
        raise RuntimeError(f"no chromium found and no cached screenshot for {url}")
    result = subprocess.run(
        [
            browser,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=1600,1000",
            f"--screenshot={target}",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0 or not target.exists():
        if target.exists():
            print(f"capture failed for {url}; reusing cached {target.name}\n{result.stderr.strip()}")
            return target
        raise RuntimeError(f"failed to capture {url}: {result.stderr.strip()}")
    if crop is not None:
        with Image.open(target) as screenshot:
            screenshot.crop(crop).save(target)
    return target


def slides(refresh: bool) -> list[Slide]:
    return [
        Slide(
            TITLE,
            "ICAC 2026 talk. 15-minute slot assumed: 12 minutes of content, 3 minutes of questions.\n\n"
            "The paper is on arXiv (2609.35806). The live demo is sfia.prdai.dev. Everything shown is released: corpus, five matchers, evaluation harness.",
            lines=(
                "Five matchers, one corpus, one evaluation harness",
                "ICAC 2026  ·  9-10 December 2026  ·  SLIIT, Malabe",
                "Ranuga Disansa  ·  U. S. Samarasinghe  ·  Lasith Gunawardena",
            ),
            kind="title",
        ),
        Slide(
            "The problem: skills are labels, work has levels",
            "Skill extraction normally returns flat labels. SFIA attaches every skill to one or more of seven responsibility levels, defined by autonomy, influence, complexity, and business skill.\n\n"
            "That level axis is what makes the task structured prediction rather than multi-label classification. It is also what most prior work ignores: ESCO and O*NET have no comparable level axis, and we found no automated LLM extraction targeting SFIA.",
            lines=(
                "Workforce tools extract skills as flat tags: Python, cloud, security.",
                "SFIA: 147 digital skills, each at one or more of seven responsibility levels.",
                "The level captures autonomy, influence, complexity, and business skill, not just seniority.",
                "No prior automated LLM extraction targets SFIA; ESCO and O*NET lack this level axis.",
                "Task: free text in, a set of (skill, level) pairs out, from a closed vocabulary.",
            ),
        ),
        Slide(
            "Three questions",
            "RQ1 is the closed-vocabulary mapping problem. RQ2 is the level problem, which is the harder one because the level is not a property of the query alone. RQ3 tests whether the current agentic designs actually help on a closed-label task.",
            lines=(
                "RQ1  How accurately can free text be mapped onto SFIA's closed vocabulary?",
                "RQ2  Which strategies predict the responsibility level alongside the skill?",
                "RQ3  Do agentic and multi-agent designs improve on simpler retrieval and prompting?",
            ),
        ),
        Slide(
            "What we built",
            "Four artifacts, all released together. The corpus pipeline is fully automated per run, given one curated reference: the SFIA 9 skill-level chart, transcribed once into JSON. The five matchers share one interface, so the harness treats them identically.",
            lines=(
                "A fully automated pipeline that turns public SFIA 9 documentation into a validated corpus.",
                "Five matching strategies behind one interface, from BM25 to a three-agent crew.",
                "An evaluation harness over 30 expert-mapped European ICT role profiles.",
                "A live explorer at sfia.prdai.dev.",
            ),
        ),
        Slide(
            "Corpus: public documentation to validated records",
            "The crawler stores 5,461 pages as markdown and HTML. Downstream stages use the 147 skill pages and 318 documentation pages with extractable content.\n\n"
            "A scout reads the non-skill pages; a synthesizer condenses its notes into a 400-token briefing; one extractor call per skill page returns (code, level, text, reasoning) records. A deterministic guard checks every pair against the SFIA 9 chart, and a verifier rejects records that are not verbatim copies.\n\n"
            "Outcome: the extractor produced exactly the 672 pairs the chart defines, so the guard fired zero times. The verifier rejected 3 records, 0.45%. The released corpus holds 669 records covering all 147 skills.",
            image=fig_corpus(),
            kind="figure",
        ),
        Slide(
            "Evaluation: 30 expert-mapped roles",
            "The gold standard is the 30 European ICT professional role profiles from CWA 16458:2018, each mapped to SFIA 7 skills and levels. One query per role, using its summary statement.\n\n"
            "Skill identification is precision, recall, and F1 on skill names. Level accuracy is computed only on skills the matcher got right by name, and because levels are ordinal we report MAE, exact accuracy, and within-one accuracy. Speed is wall-clock seconds per record.",
            lines=(
                "30 European ICT role profiles, each mapped to SFIA 7 skills and levels.",
                "One query per role: the role's summary statement; expected output: all listed skills.",
                "Skill identification: precision, recall, F1 on names.",
                "Level: MAE, exact, and within-one, only on correctly named skills.",
                "Speed: wall-clock seconds per record.",
            ),
        ),
        Slide(
            "Five strategies, one interface",
            "The lexical baseline returns every record scoring at least 0.7 of the query's top BM25 score. The dense pipeline embeds every record with Qwen3-Embedding-0.6B, retrieves the top 20, and reranks each candidate pointwise with Llama-3.3-70B, keeping scores at or above 0.6.\n\n"
            "The zero-shot matcher is a single schema-constrained call with no retrieval: the schema enumerates all 147 skill names and constrains level to 1-7. The single agent holds the same dense and BM25 retrieval as tools and iterates up to 8 times. The crew shares one model across three sequential agents: retriever, matcher, verifier.",
            lines=(
                "BM25 lexical: every record at least 0.7 of the top score.",
                "Dense + rerank: Qwen3 embeddings, top 20, Llama-3.3-70B pointwise, keep >= 0.6.",
                "Zero-shot LLM: one schema-constrained call, 147 names, level 1-7.",
                "Agentic RAG: one CrewAI agent with dense and BM25 tools, up to 8 iterations.",
                "Multi-agent crew: retriever → matcher → verifier, same tools and one shared model.",
            ),
        ),
        Slide(
            "Retrieval finds more skills; generative matchers are more precise",
            "Dense retrieval records the highest skill F1, 0.232, through the highest recall, 0.243. The agentic strategies follow at 0.213 and 0.212. The margin is the same order as run-to-run variance, so we claim no strict ranking.\n\n"
            "The robust pattern is the trade-off. The zero-shot matcher is the precision extreme, 0.436 at recall 0.117; retrieval tools buy recall back while keeping precision well above the dense pipeline's 0.266.",
            image=fig_skill_f1(),
            kind="figure",
        ),
        Slide(
            "Only explicit level decisions predict level well",
            "On the level dimension the ranking inverts. Dense retrieval is the worst level predictor by far: MAE 1.60, exact 0.181. Its level is a by-product of which record embeds closest, and even the reranker scores relevance rather than committing to a level.\n\n"
            "Strategies that emit the level as an explicit decision sit in a different regime. The single agent reaches MAE 0.68 and exact 0.526; zero-shot reaches 0.74 MAE and 0.895 within one level; BM25 carries the level of its top record (0.94 MAE). The gap to dense retrieval far exceeds run-to-run variance.",
            image=fig_level(),
            kind="figure",
        ),
        Slide(
            "More agents is not better",
            "The crew matches the single agent on skill F1, 0.212 versus 0.213, at double the latency: 327 versus 167 seconds per record, because three sequential agents each make their own model calls.\n\n"
            "Level fidelity is markedly worse: MAE 1.16 versus 0.68. Passing evidence as conversation text appears to lose the descriptor grounding the single agent gets from reading tool output directly. The verifier raises precision slightly, 0.361 to 0.398, and recall, 0.172 to 0.218, but not enough to justify the cost.",
            image=fig_cost(),
            kind="figure",
        ),
        Slide(
            "Live: 147 skills, each with a level range",
            "The explorer is a port of the research implementation, not the Python artifact. The catalogue shows every SFIA 9 skill and the levels it is defined at; the main screen maps pasted role text to (skill, level) pairs.\n\n"
            "Astro static pages plus one React island, a Cloudflare Worker with the Vercel AI SDK, Vectorize for semantic retrieval, Orama for BM25, and Nemotron-3-120B behind AI Gateway. The agent holds the two tools and must call both before submitting matches.",
            image=capture("skills", "https://sfia.prdai.dev/skills", refresh, crop=(280, 70, 1330, 900)),
            kind="figure",
        ),
        Slide(
            "Takeaways",
            "Four points to leave with. First, make the level an explicit output; similarity alone is not a level decision. Second, the precision-recall trade-off is a design choice, not a bug. Third, adding agents adds cost here without adding accuracy. Fourth, the whole stack is reproducible and online.",
            lines=(
                "Structured prediction, not classification: ask for the level explicitly.",
                "Dense retrieval maximises skill F1 but is the worst level predictor.",
                "More agents is not more accuracy: the crew doubles cost for no F1 gain.",
                "Released: corpus, five matchers, evaluation harness, and a live demo.",
            ),
        ),
        Slide("Appendix", "Backup slides for questions.", kind="section"),
        Slide(
            "Full results",
            "Best swept configuration per strategy on the 30-role harness. F1 is the mean of per-role F1, not the harmonic mean of the P and R columns. Level metrics are computed on correctly named skills only. s/record is mean wall-clock seconds per record.\n\n"
            "The zero-shot timing comes from the sweep run; the final run repeated identical temperature-0 prompts and was largely served from the gateway cache.",
            image=fig_results_table(),
            kind="figure",
        ),
        Slide(
            "The trade-off is the result",
            "No strategy wins on both axes. Which profile is preferable depends on the application: recall matters when a human reviewer sees the candidates, precision when the output feeds an automated pipeline.\n\n"
            "Recall is capped at 0.69 for every strategy because the gold standard uses SFIA 7 vocabulary while the corpus is SFIA 9.",
            image=fig_tradeoff(),
            kind="figure",
        ),
        Slide(
            "Model choice changes the answer",
            "On the zero-shot sweep, skill F1 and level accuracy rank models differently. Llama-4-Scout is mid-pack on F1, 0.153, but posts the best level numbers: exact 0.694, MAE 0.36, on the subset it names correctly. Gemma leads F1 at 0.176.\n\n"
            "Four of ten models intermittently spent their whole output budget on hidden reasoning under schema-constrained decoding and returned nothing. Robustness to constrained decoding proved as decisive as raw capability.",
            image=fig_sweep(),
            kind="figure",
        ),
        Slide(
            "Threats to validity",
            "The gold standard uses SFIA 7 vocabulary, which caps recall at 0.69. Thirty roles is a small harness, and the level metrics are conditioned on correctly named skills. Model serving and caching change latency, so treat seconds per record as order-of-magnitude. The corpus pipeline assumes one curated reference artifact, the SFIA 9 skill-level chart.",
            lines=(
                "Gold standard uses SFIA 7 vocabulary; recall is capped at 0.69.",
                "Thirty roles is a small harness; per-role variance is material.",
                "Level metrics are conditioned on correctly named skills.",
                "Latency depends on the serving path and gateway cache.",
                "'Fully automated' is per run, given one curated SFIA 9 chart.",
            ),
        ),
        Slide(
            "Reproduce it",
            "The corpus and results are checked in, so the matchers and harness can be rerun without crawling SFIA. The full rebuild path is crawl, extract, copy the corpus, then re-ingest and rerun the harness.\n\n"
            "The commands are in the repository README. The explorer source is in explorer/.",
            lines=(
                "Repo: github.com/prdai/sfia-structured-skill-extraction",
                "Paper: arxiv.org/abs/2609.35806",
                "Demo: sfia.prdai.dev",
                "uv run eval-compare  # rebuild the results table",
            ),
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
    title = textwrap.fill(slide.title, width=62)
    fig.text(0.045, 0.95, title, fontsize=26, fontweight="bold", ha="left", va="top", color=INK)
    if slide.kind == "bullets":
        cursor = 0.77
        for line in slide.lines:
            wrapped = textwrap.fill(line, width=82, subsequent_indent="   ")
            fig.text(
                0.06,
                cursor,
                "•  " + wrapped,
                fontsize=19,
                ha="left",
                va="top",
                color=INK,
                linespacing=1.35,
            )
            cursor -= (wrapped.count("\n") + 1) * 0.050 + 0.036
        return fig
    if slide.image is None:
        raise ValueError(f"figure slide has no image: {slide.title}")
    image = chart_image(slide.image)
    box = (0.03, 0.03, 0.94, 0.83 if "\n" not in title else 0.76)
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-screens", action="store_true", help="recapture the explorer screenshots")
    args = parser.parse_args()
    plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.bbox": None})
    write_deck(slides(args.refresh_screens))
    print(f"wrote {OUT / 'sfia-icac-2026.pptx'}")
    print(f"wrote {OUT / 'sfia-icac-2026.pdf'}")


if __name__ == "__main__":
    main()
