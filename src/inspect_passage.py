#!/usr/bin/env python3
"""Inspect stress-defined word-final correspondences in a selected Torah passage."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
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
BOOK_ALIASES = {
    "gen": "genesis",
    "genesis": "genesis",
    "ex": "exodus",
    "exo": "exodus",
    "exodus": "exodus",
    "lev": "leviticus",
    "leviticus": "leviticus",
    "num": "numbers",
    "numbers": "numbers",
    "deut": "deuteronomy",
    "deuteronomy": "deuteronomy",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_reference(value: str) -> tuple[int, int]:
    try:
        chapter, verse = (int(part) for part in value.split(":", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected chapter:verse, received {value!r}") from exc
    if chapter < 1 or verse < 1:
        raise ValueError("chapter and verse must be positive")
    return chapter, verse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Examples: --book deuteronomy --start 11:10 --end 11:15; "
            "add --equiv vf --equiv qk or --equiv all for optional close correspondences."
        ),
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--book", required=True, help="Torah book, e.g. genesis or deut")
    parser.add_argument("--start", required=True, help="start reference as chapter:verse")
    parser.add_argument("--end", required=True, help="end reference as chapter:verse")
    parser.add_argument(
        "--equiv",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "optional consonantal correspondence; repeat or comma-separate. "
            "Choices: none, " + ", ".join(EQUIVALENCE_ORDER) + ", all"
        ),
    )
    parser.add_argument(
        "--exact-words",
        choices=("include", "exclude"),
        default="include",
        help="include or omit pairs that repeat the same normalized word (default: include)",
    )
    parser.add_argument(
        "--window-left",
        type=int,
        default=20,
        help="compare each eligible word to N previous eligible words; 0 = all earlier words in passage",
    )
    parser.add_argument("--label", help="output folder label; generated automatically if omitted")
    return parser.parse_args()


def write_pairs(path: Path, pairs: list[dict]) -> None:
    fields = (
        "pair",
        "relation",
        "equivalences_used",
        "matched_signature",
        "distance_eligible_words",
        "source_chapter",
        "source_verse",
        "source_position",
        "source_hebrew",
        "source_word",
        "source_signature",
        "target_chapter",
        "target_verse",
        "target_position",
        "target_hebrew",
        "target_word",
        "target_signature",
        "exact_word",
    )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(pairs)


def main() -> int:
    args = parse_args()
    key = BOOK_ALIASES.get(args.book.strip().lower())
    if key is None:
        raise SystemExit(f"Unknown Torah book: {args.book}")
    try:
        start = parse_reference(args.start)
        end = parse_reference(args.end)
        enabled = normalize_equivalences(args.equiv)
    except (ValueError, RhymeError) as exc:
        raise SystemExit(str(exc)) from exc
    if start > end:
        raise SystemExit("start must not follow end")
    if args.window_left < 0:
        raise SystemExit("window-left must be >= 0")

    input_path = args.root / "data/processed" / f"{key}.json"
    if not input_path.exists():
        raise SystemExit(f"Missing {input_path}; restore the frozen data or run preprocessing first")
    data = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "torah_word_rhyme.word-rhyme-corpus.v2" or data.get("key") != key:
        raise SystemExit(f"Unexpected processed corpus in {input_path}")

    selected = [
        dict(word)
        for word in data["words"]
        if start <= (word["chapter"], word["verse"]) <= end
    ]
    if not selected:
        raise SystemExit("No words found in the selected range")

    eligible: list[dict] = []
    for word in selected:
        try:
            signature = extract_signature(word.get("transliteration", ""))
        except RhymeError:
            continue
        if signature is None:
            continue
        word["signature"] = signature
        word["normalized_word"] = normalized_word(word["transliteration"])
        word["passage_index"] = len(eligible) + 1
        eligible.append(word)

    pairs: list[dict] = []
    word_pairs: dict[int, list[str]] = {word["index"]: [] for word in selected}
    for target_position, target in enumerate(eligible):
        lower = max(0, target_position - args.window_left) if args.window_left else 0
        for source_position in range(lower, target_position):
            source = eligible[source_position]
            exact_word = source["normalized_word"] == target["normalized_word"]
            if args.exact_words == "exclude" and exact_word:
                continue
            match = compare(source["signature"], target["signature"], enabled)
            if not match.accepted:
                continue
            pair_id = f"P{len(pairs) + 1:04d}"
            word_pairs[source["index"]].append(pair_id)
            word_pairs[target["index"]].append(pair_id)
            pairs.append(
                {
                    "pair": pair_id,
                    "relation": match.relation,
                    "equivalences_used": ",".join(match.equivalences_used),
                    "matched_signature": match.display,
                    "distance_eligible_words": target["passage_index"] - source["passage_index"],
                    "source_chapter": source["chapter"],
                    "source_verse": source["verse"],
                    "source_position": source["word_in_verse"],
                    "source_hebrew": source["hebrew"],
                    "source_word": source["transliteration"],
                    "source_signature": source["signature"].display,
                    "target_chapter": target["chapter"],
                    "target_verse": target["verse"],
                    "target_position": target["word_in_verse"],
                    "target_hebrew": target["hebrew"],
                    "target_word": target["transliteration"],
                    "target_signature": target["signature"].display,
                    "exact_word": exact_word,
                }
            )

    suffix = "strict" if not enabled else "close_" + "-".join(enabled)
    label = args.label or f"{key}_{args.start.replace(':', '-')}_{args.end.replace(':', '-')}_{suffix}"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", label):
        raise SystemExit("label may contain only letters, numbers, dot, underscore, and hyphen")
    output_dir = args.root / "results/passages" / label
    output_dir.mkdir(parents=True, exist_ok=True)

    write_pairs(output_dir / "pairs.tsv", pairs)

    signature_by_word = {
        word["index"]: word["signature"].display
        for word in eligible
        if word_pairs[word["index"]]
    }
    by_verse: dict[tuple[int, int], list[dict]] = {}
    for word in selected:
        by_verse.setdefault((word["chapter"], word["verse"]), []).append(word)
    lines: list[str] = []
    for (chapter, verse), words in sorted(by_verse.items()):
        rendered = []
        for word in words:
            text = word.get("transliteration") or f"⟦{word['hebrew']}⟧"
            signature = signature_by_word.get(word["index"])
            rendered.append(text + ("{" + signature + "}" if signature else ""))
        lines.append(f"{chapter}:{verse}\t" + " ".join(rendered) + " |")
    (output_dir / "annotated.txt").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    human = [
        f"{data['book']} {args.start}-{args.end}",
        f"equivalences: {', '.join(enabled) if enabled else 'none (strict identity only)'}",
        f"exact words: {args.exact_words}; L={args.window_left}",
        f"eligible words: {len(eligible)}; accepted pairs: {len(pairs)}",
        "",
    ]
    exact_pairs = [pair for pair in pairs if pair["relation"] == "EXACT"]
    close_pairs = [pair for pair in pairs if pair["relation"] == "CLOSE"]

    if exact_pairs:
        groups: dict[str, dict[tuple[int, int, int], tuple[int, int, str]]] = {}
        for pair in exact_pairs:
            members = groups.setdefault(pair["source_signature"], {})
            source_key = (pair["source_chapter"], pair["source_verse"], pair["source_position"])
            target_key = (pair["target_chapter"], pair["target_verse"], pair["target_position"])
            members[source_key] = (pair["source_chapter"], pair["source_verse"], pair["source_word"])
            members[target_key] = (pair["target_chapter"], pair["target_verse"], pair["target_word"])
        human.append("EXACT TERMINAL GROUPS")
        for signature, members in groups.items():
            human.append(f"[{signature}]")
            occurrences = Counter(members.values())
            for (chapter, verse, word), count in occurrences.items():
                multiplicity = f"  ×{count}" if count > 1 else ""
                human.append(f"  {chapter}:{verse}  {word}{multiplicity}")

    if close_pairs:
        if exact_pairs:
            human.append("")
        human.append("OPTIONAL CLOSE CORRESPONDENCES")
        for pair in close_pairs:
            notes = []
            if pair["equivalences_used"]:
                notes.append(pair["equivalences_used"])
            if pair["exact_word"]:
                notes.append("same word")
            note = f"; {', '.join(notes)}" if notes else ""
            human.append(
                f"{pair['source_chapter']}:{pair['source_verse']} {pair['source_word']}  ↔  "
                f"{pair['target_chapter']}:{pair['target_verse']} {pair['target_word']}  "
                f"[{pair['matched_signature']}{note}]"
            )

    if not pairs:
        human.append("(no accepted correspondences)")
    (output_dir / "pairs.txt").write_bytes(("\n".join(human) + "\n").encode("utf-8"))

    summary = {
        "schema": "torah_word_rhyme.passage-inspection.v1",
        "created_utc": now(),
        "book": data["book"],
        "start": args.start,
        "end": args.end,
        "parameters": {
            "equivalences": list(enabled),
            "exact_words": args.exact_words,
            "window_left": args.window_left,
            "signature_rule": "final marked vowel through word end; extend one segment left if that vowel is word-final",
        },
        "selected_words": len(selected),
        "eligible_words": len(eligible),
        "accepted_pairs": len(pairs),
        "exact_pairs": len(exact_pairs),
        "close_pairs": len(close_pairs),
        "input_sha256": sha(input_path),
        "script_sha256": sha(Path(__file__)),
        "engine_sha256": sha(Path(__file__).with_name("rhyme.py")),
    }
    (output_dir / "summary.json").write_bytes((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"eligible_words={len(eligible)} accepted_pairs={len(pairs)} exact={len(exact_pairs)} close={len(close_pairs)}")
    print(f"WROTE: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
