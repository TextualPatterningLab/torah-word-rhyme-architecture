#!/usr/bin/env python3
"""Stress/marked-vowel word-final correspondence engine for passage inspection."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence
import unicodedata

COMBINING_ACUTE = "\u0301"
VOWELS = frozenset("aeiou")
MULTIGRAPHS = ("kh", "ch", "sh", "ts")
ANNOTATION_RE = re.compile(r"\[[^\]]*\]|\{[^}]*\}")

# Optional heuristic consonantal correspondences. These are deliberately explicit
# and independently switchable; they are not treated as claims of phonological identity.
EQUIVALENCE_GROUPS: dict[str, frozenset[frozenset[str]]] = {
    "vf": frozenset({frozenset(("v", "f"))}),
    "dt": frozenset({frozenset(("d", "t"))}),
    "pb": frozenset({frozenset(("p", "b"))}),
    "qk": frozenset({frozenset(("q", "k"))}),
    "chkh": frozenset({frozenset(("ch", "kh"))}),
    "dental": frozenset(
        frozenset((left, right))
        for i, left in enumerate(("t", "ts", "s", "z"))
        for right in ("t", "ts", "s", "z")[i + 1 :]
    ),
}
EQUIVALENCE_ORDER = tuple(EQUIVALENCE_GROUPS)


class RhymeError(ValueError):
    pass


@dataclass(frozen=True)
class Segment:
    text: str
    stressed: bool


@dataclass(frozen=True)
class Signature:
    word: str
    segments: tuple[str, ...]
    display: str
    extended_left: bool


@dataclass(frozen=True)
class Match:
    accepted: bool
    relation: str | None = None  # EXACT or CLOSE
    display: str | None = None
    equivalences_used: tuple[str, ...] = ()


def clean_word(token: str) -> str:
    text = unicodedata.normalize("NFD", ANNOTATION_RE.sub("", token).strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch).startswith(("L", "M")))
    return text


def normalized_word(token: str) -> str:
    return unicodedata.normalize("NFC", clean_word(token).replace(COMBINING_ACUTE, ""))


def base_units(word: str) -> list[tuple[str, tuple[str, ...]]]:
    units: list[tuple[str, tuple[str, ...]]] = []
    for ch in unicodedata.normalize("NFD", word):
        if unicodedata.combining(ch):
            if not units:
                raise RhymeError("combining mark precedes the first letter")
            base, marks = units[-1]
            units[-1] = (base, marks + (ch,))
        else:
            units.append((ch, ()))
    return units


def segment_word(token: str) -> tuple[Segment, ...]:
    units = base_units(clean_word(token))
    plain = "".join(base for base, _marks in units)
    output: list[Segment] = []
    index = 0
    while index < len(units):
        # tsh must be read as t + sh, never as ts + h.
        if plain.startswith("tsh", index):
            for width in (1, 2):
                chosen = units[index : index + width]
                output.append(
                    Segment(
                        "".join(base for base, _marks in chosen),
                        any(COMBINING_ACUTE in marks for _base, marks in chosen),
                    )
                )
                index += width
            continue
        multigraph = next((item for item in MULTIGRAPHS if plain.startswith(item, index)), None)
        width = len(multigraph) if multigraph else 1
        chosen = units[index : index + width]
        output.append(
            Segment(
                "".join(base for base, _marks in chosen),
                any(COMBINING_ACUTE in marks for _base, marks in chosen),
            )
        )
        index += width
    return tuple(output)


def is_vowel(segment: Segment) -> bool:
    return segment.text in VOWELS


def _display(segments: Sequence[Segment], indices: Sequence[int]) -> str:
    return "".join(("ˈ" if segments[index].stressed else "") + segments[index].text for index in indices)


def extract_signature(token: str) -> Signature | None:
    """Return the word-final signature beginning at the final marked vowel.

    If the final marked vowel is also the final phonetic segment, extend one
    segment left so a bare final vowel is not used as a one-segment signature.
    """
    word = clean_word(token)
    if not word:
        return None
    segments = segment_word(word)
    marked_vowels = [index for index, segment in enumerate(segments) if segment.stressed and is_vowel(segment)]
    if not marked_vowels:
        raise RhymeError(f"no marked vowel in {token!r}")
    marked = marked_vowels[-1]
    start = marked
    extended_left = False
    if marked == len(segments) - 1 and marked > 0:
        start = marked - 1
        extended_left = True
    indices = tuple(range(start, len(segments)))
    return Signature(
        word=unicodedata.normalize("NFC", word),
        segments=tuple(segments[index].text for index in indices),
        display=_display(segments, indices),
        extended_left=extended_left,
    )


def normalize_equivalences(values: Iterable[str]) -> tuple[str, ...]:
    requested: list[str] = []
    for raw in values:
        for value in raw.split(","):
            name = value.strip().lower()
            if not name or name == "none":
                continue
            if name == "all":
                for item in EQUIVALENCE_ORDER:
                    if item not in requested:
                        requested.append(item)
                continue
            if name not in EQUIVALENCE_GROUPS:
                allowed = ", ".join(("none", *EQUIVALENCE_ORDER, "all"))
                raise RhymeError(f"unknown equivalence {name!r}; choose from {allowed}")
            if name not in requested:
                requested.append(name)
    return tuple(requested)


def equivalence_for_pair(left: str, right: str, enabled: Sequence[str]) -> str | None:
    if left == right:
        return "IDENTICAL"
    if left in VOWELS or right in VOWELS:
        return None
    pair = frozenset((left, right))
    for name in enabled:
        if pair in EQUIVALENCE_GROUPS[name]:
            return name
    return None


def compare(left: Signature, right: Signature, enabled: Sequence[str] = ()) -> Match:
    if len(left.segments) != len(right.segments):
        return Match(False)
    used: list[str] = []
    for first, second in zip(left.segments, right.segments):
        relation = equivalence_for_pair(first, second, enabled)
        if relation is None:
            return Match(False)
        if relation != "IDENTICAL" and relation not in used:
            used.append(relation)
    if not used:
        return Match(True, "EXACT", left.display, ())
    return Match(
        True,
        "CLOSE",
        f"{left.display} <-> {right.display}",
        tuple(used),
    )


def compare_words(left: str, right: str, enabled: Sequence[str] = ()) -> Match:
    first = extract_signature(left)
    second = extract_signature(right)
    if first is None or second is None:
        return Match(False)
    return compare(first, second, enabled)
