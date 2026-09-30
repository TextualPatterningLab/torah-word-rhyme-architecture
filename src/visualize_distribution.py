#!/usr/bin/env python3
"""Create a descriptive map of stress-defined word-final correspondences across the Torah.

This tool reuses the same signature and optional consonantal-correspondence engine as
``inspect_passage.py``. It is an exploratory visualization aid, not a significance test,
control-corpus comparison, poetry classifier, or estimate of corpus-level exceptionalness.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import re

from rhyme import (
    EQUIVALENCE_ORDER,
    RhymeError,
    compare,
    extract_signature,
    normalize_equivalences,
    normalized_word,
)

ROOT = Path(__file__).resolve().parents[1]
TORAH = ("genesis", "exodus", "leviticus", "numbers", "deuteronomy")
BOOK_LABELS = {
    "genesis": "Genesis",
    "exodus": "Exodus",
    "leviticus": "Leviticus",
    "numbers": "Numbers",
    "deuteronomy": "Deuteronomy",
}
PALETTES = {
    "bluepurple": "BuPu",
    "blues": "Blues",
    "purples": "Purples",
    "gray": "Greys",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_book(root: Path, book: str) -> tuple[dict, Path]:
    path = root / "data" / "processed" / f"{book}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; restore the frozen data or run preprocessing first")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "torah_word_rhyme.word-rhyme-corpus.v2" or data.get("key") != book:
        raise ValueError(f"Unexpected processed corpus in {path}")
    return data, path


def prepare_words(data: dict) -> tuple[list[dict], int]:
    eligible: list[dict] = []
    skipped = 0
    for word in data["words"]:
        try:
            signature = extract_signature(word.get("transliteration", ""))
        except RhymeError:
            skipped += 1
            continue
        if signature is None:
            skipped += 1
            continue
        item = dict(word)
        item["eligible_index"] = len(eligible) + 1
        item["signature"] = signature
        item["normalized_word"] = normalized_word(word["transliteration"])
        eligible.append(item)
    return eligible, skipped


def analyze_book(
    data: dict,
    *,
    enabled: tuple[str, ...],
    exact_words: str,
    window_left: int,
    density_window: int,
    step: int,
) -> tuple[list[dict], dict]:
    eligible, skipped = prepare_words(data)
    count = len(eligible)
    arrivals = [0] * count
    exact_arrivals = [0] * count
    close_arrivals = [0] * count
    participates = [False] * count
    accepted_pairs = 0
    exact_pairs = 0
    close_pairs = 0
    repeated_word_pairs = 0

    for target_index, target in enumerate(eligible):
        lower = max(0, target_index - window_left) if window_left else 0
        for source_index in range(lower, target_index):
            source = eligible[source_index]
            same_word = source["normalized_word"] == target["normalized_word"]
            if exact_words == "exclude" and same_word:
                continue
            match = compare(source["signature"], target["signature"], enabled)
            if not match.accepted:
                continue
            accepted_pairs += 1
            repeated_word_pairs += int(same_word)
            if match.relation == "EXACT":
                exact_pairs += 1
                exact_arrivals[target_index] += 1
            else:
                close_pairs += 1
                close_arrivals[target_index] += 1
            arrivals[target_index] += 1
            participates[source_index] = True
            participates[target_index] = True

    rows: list[dict] = []
    if count:
        width = min(density_window, count)
        starts = list(range(0, max(1, count - width + 1), step))
        if not starts:
            starts = [0]
        final_start = count - width
        if starts[-1] != final_start:
            starts.append(final_start)
        for window_index, start in enumerate(starts, 1):
            end = start + width
            participating = sum(participates[start:end])
            active_targets = sum(value > 0 for value in arrivals[start:end])
            rows.append(
                {
                    "book": data["key"],
                    "window": window_index,
                    "start_word": start + 1,
                    "end_word": end,
                    "center_word": (start + 1 + end) / 2,
                    "relative_center": ((start + end) / 2) / count,
                    "window_words": width,
                    "participating_rate": participating / width,
                    "active_target_rate": active_targets / width,
                    "arrivals_per_target": sum(arrivals[start:end]) / width,
                    "exact_arrivals_per_target": sum(exact_arrivals[start:end]) / width,
                    "close_arrivals_per_target": sum(close_arrivals[start:end]) / width,
                }
            )

    summary = {
        "book": data["key"],
        "eligible_words": count,
        "skipped_words": skipped,
        "accepted_pairs": accepted_pairs,
        "exact_pairs": exact_pairs,
        "close_pairs": close_pairs,
        "exact_repeated_word_pairs": repeated_word_pairs,
        "participating_words": sum(participates),
        "participating_rate": sum(participates) / count if count else None,
    }
    return rows, summary


def write_density(path: Path, rows: list[dict]) -> None:
    fields = (
        "book",
        "window",
        "start_word",
        "end_word",
        "center_word",
        "relative_center",
        "window_words",
        "participating_rate",
        "active_target_rate",
        "arrivals_per_target",
        "exact_arrivals_per_target",
        "close_arrivals_per_target",
    )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def metric_label(metric: str) -> str:
    if metric == "participating_rate":
        return "Local proportion of eligible words participating in ≥1 accepted correspondence"
    if metric == "active_target_rate":
        return "Local proportion of eligible target words receiving ≥1 accepted correspondence"
    return "Accepted correspondence arrivals per eligible target word"


def build_figure(
    output_dir: Path,
    rows: list[dict],
    summaries: list[dict],
    parameters: dict,
) -> str:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import Normalize
        from matplotlib.patches import Rectangle
    except ImportError as exc:
        raise SystemExit(
            "The distribution visualization requires matplotlib. "
            "Install it with: python -m pip install -r requirements-visualization.txt"
        ) from exc

    by_book = {book: [] for book in TORAH}
    for row in rows:
        by_book[row["book"]].append(row)
    for values in by_book.values():
        values.sort(key=lambda item: int(item["window"]))

    metric = parameters["metric"]
    values = [float(row[metric]) for row in rows]
    observed_max = max(values) if values else 1.0
    if observed_max <= 0:
        observed_max = 1.0

    cmap = plt.get_cmap(PALETTES[parameters["palette"]])
    norm = Normalize(vmin=0.0, vmax=observed_max)

    fig, ax = plt.subplots(figsize=(12.2, 6.2))
    y_positions = {book: 4 - index for index, book in enumerate(TORAH)}
    book_counts = {item["book"]: item["eligible_words"] for item in summaries}

    for book in TORAH:
        y = y_positions[book]
        local_rows = by_book[book]
        centers = [100.0 * float(item["relative_center"]) for item in local_rows]
        if centers:
            edges = [0.0]
            for first, second in zip(centers, centers[1:]):
                edges.append((first + second) / 2)
            edges.append(100.0)
            for item, x0, x1 in zip(local_rows, edges, edges[1:]):
                value = float(item[metric])
                ax.add_patch(
                    Rectangle(
                        (x0, y - 0.31),
                        max(0.05, x1 - x0),
                        0.62,
                        facecolor=cmap(norm(value)),
                        edgecolor="none",
                    )
                )
        ax.add_patch(
            Rectangle((0, y - 0.31), 100, 0.62, fill=False, edgecolor="0.25", linewidth=0.7)
        )
        ax.text(
            101.2,
            y,
            f"n={book_counts.get(book, 0):,}",
            va="center",
            ha="left",
            fontsize=9,
        )

    ax.set_xlim(0, 106)
    ax.set_ylim(-0.75, 4.75)
    ax.set_yticks([y_positions[book] for book in TORAH])
    ax.set_yticklabels([BOOK_LABELS[book] for book in TORAH], fontsize=11)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Relative position within each book (%)", fontsize=10.5)
    ax.tick_params(axis="x", labelsize=9.5)
    ax.tick_params(axis="y", length=0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.7)

    eq_label = (
        ", ".join(parameters["equivalences"])
        if parameters["equivalences"]
        else "strict identity only"
    )
    fig.suptitle(
        "Demonstrative word-final correspondence distribution across the Pentateuch",
        fontsize=15,
        fontweight="bold",
        y=0.955,
    )

    is_default = (
        not parameters["equivalences"]
        and parameters["exact_words"] == "include"
        and parameters["window_left"] == 20
        and parameters["density_window"] == 250
        and parameters["step"] == 50
        and parameters["metric"] == "participating_rate"
    )
    if is_default:
        fig.text(
            0.5,
            0.905,
            "Default STRICT settings",
            ha="center",
            fontsize=10,
        )

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(
        sm,
        ax=ax,
        orientation="horizontal",
        fraction=0.055,
        pad=0.18,
        aspect=55,
    )
    cbar.set_label(metric_label(metric), fontsize=9.5)
    cbar.ax.tick_params(labelsize=8.5)
    cbar.outline.set_linewidth(0.6)

    fig.subplots_adjust(left=0.13, right=0.94, top=0.84, bottom=0.19)

    svg_path = output_dir / "distribution.svg"
    pdf_path = output_dir / "distribution.pdf"
    png_path = output_dir / "distribution.png"

    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Matplotlib may emit visually harmless trailing spaces inside multiline
    # SVG path data. Normalize only end-of-line whitespace so generated SVG
    # output remains clean under `git diff --check`.
    svg_text = svg_path.read_text(encoding="utf-8")
    normalized_svg = "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n"
    svg_path.write_text(normalized_svg, encoding="utf-8", newline="\n")

    return matplotlib.__version__


def suggested_caption(parameters: dict) -> str:
    matching = (
        "STRICT normalized segment identity"
        if not parameters["equivalences"]
        else "optional consonantal correspondences: " + ", ".join(parameters["equivalences"])
    )
    radius = (
        "all earlier eligible words within each book"
        if parameters["window_left"] == 0
        else f"the preceding {parameters['window_left']} eligible words"
    )
    return (
        "Demonstrative distribution of word-final "
        "correspondences under the documented final-marked-vowel heuristic. "
        f"Matching: {matching}; identical normalized words: {parameters['exact_words']}. "
        f"Each eligible word is compared with {radius}. "
        f"Displayed metric: {metric_label(parameters['metric'])}. "
        f"Local windows contain up to {parameters['density_window']} eligible words "
        f"and advance by {parameters['step']} eligible words. "
        "Horizontal position is normalized separately to 0–100% of each book's eligible-word sequence; equal strip widths do not represent equal book lengths. The n labels give eligible-word counts. Matching distances and local windows use actual word counts, not percentages. The shared color scale represents local proportions, not absolute numbers of words. "
        "The map illustrates the operational rule; it is not a test of poetic status "
        "or a complete model of Hebrew lexical stress."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument(
        "--equiv",
        action="append",
        default=[],
        metavar="NAME",
        help="optional consonantal correspondence; repeat or comma-separate. Choices: none, "
        + ", ".join(EQUIVALENCE_ORDER)
        + ", all",
    )
    parser.add_argument("--exact-words", choices=("include", "exclude"), default="include")
    parser.add_argument(
        "--window-left",
        type=int,
        default=20,
        help="compare each eligible word to N previous eligible words; 0 = all earlier words in the book",
    )
    parser.add_argument(
        "--density-window",
        type=int,
        default=250,
        help="eligible words in each local descriptive window",
    )
    parser.add_argument("--step", type=int, default=50, help="eligible-word step between local windows")
    parser.add_argument(
        "--metric",
        choices=("participating_rate", "active_target_rate", "arrivals_per_target"),
        default="participating_rate",
    )
    parser.add_argument(
        "--palette",
        choices=tuple(PALETTES),
        default="bluepurple",
        help="figure palette; default bluepurple (ColorBrewer BuPu)",
    )
    parser.add_argument("--label", help="output folder label; generated automatically if omitted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.window_left < 0 or args.density_window < 1 or args.step < 1:
        raise SystemExit("window-left must be >= 0; density-window and step must be positive")
    try:
        enabled = normalize_equivalences(args.equiv)
    except RhymeError as exc:
        raise SystemExit(str(exc)) from exc

    eq_label = "strict" if not enabled else "close-" + "-".join(enabled)
    label = args.label or (
        f"{eq_label}_exact-{args.exact_words}_L{args.window_left}_"
        f"W{args.density_window}_S{args.step}"
    )
    if not re.fullmatch(r"[A-Za-z0-9._-]+", label):
        raise SystemExit("label may contain only letters, numbers, dot, underscore, and hyphen")

    output_dir = args.root / "results" / "distribution" / label
    output_dir.mkdir(parents=True, exist_ok=True)

    density_rows: list[dict] = []
    summaries: list[dict] = []
    input_hashes: dict[str, str] = {}

    for book in TORAH:
        data, input_path = load_book(args.root, book)
        input_hashes[book] = sha(input_path)
        rows, summary = analyze_book(
            data,
            enabled=enabled,
            exact_words=args.exact_words,
            window_left=args.window_left,
            density_window=args.density_window,
            step=args.step,
        )
        density_rows.extend(rows)
        summaries.append(summary)
        print(
            f"{book}: eligible={summary['eligible_words']} pairs={summary['accepted_pairs']} "
            f"participating={summary['participating_rate']:.3f}"
        )

    parameters = {
        "equivalences": list(enabled),
        "exact_words": args.exact_words,
        "window_left": args.window_left,
        "density_window": args.density_window,
        "step": args.step,
        "metric": args.metric,
        "palette": args.palette,
        "signature_rule": (
            "final marked vowel through word end; extend one segment left "
            "if that vowel is word-final"
        ),
    }

    write_density(output_dir / "density.tsv", density_rows)
    matplotlib_version = build_figure(output_dir, density_rows, summaries, parameters)
    (output_dir / "caption.txt").write_text(
        suggested_caption(parameters) + "\n", encoding="utf-8"
    )

    summary = {
        "schema": "torah_word_rhyme.descriptive-distribution.v2",
        "created_utc": now(),
        "purpose": (
            "descriptive exploratory visualization only; not a control-corpus "
            "comparison or significance test"
        ),
        "label": label,
        "parameters": parameters,
        "environment": {
            "python": platform.python_version(),
            "matplotlib": matplotlib_version,
        },
        "input_sha256": input_hashes,
        "script_sha256": sha(Path(__file__)),
        "engine_sha256": sha(Path(__file__).with_name("rhyme.py")),
        "books": summaries,
        "outputs": [
            "distribution.svg",
            "distribution.pdf",
            "distribution.png",
            "density.tsv",
            "summary.json",
            "caption.txt",
        ],
    }
    (output_dir / "summary.json").write_bytes(
        (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )

    print(f"WROTE: {output_dir}")
    print("FIGURES: distribution.svg / distribution.pdf / distribution.png")
    print("CAPTION: caption.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
