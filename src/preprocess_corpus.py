#!/usr/bin/env python3
"""Create the compact and readable Torah word corpus used by rhyme analysis."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
TORAH = ("genesis", "exodus", "leviticus", "numbers", "deuteronomy")

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשתךםןףץ")
FINAL_TO_BASE = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
DAGESH = "\u05bc"
SHEVA = "\u05b0"
SHIN_DOT = "\u05c1"
SIN_DOT = "\u05c2"
METEG = "\u05bd"
MAQAF = "\u05be"
PASEQ = "\u05c0"
SOF_PASUQ = "\u05c3"
QAMATS_QATAN = "\u05c7"
MASORA_CIRCLE = "\u05af"
RAFE = "\u05bf"
UPPER_DOT = "\u05c4"
COMBINING_ACUTE = "\u0301"

VOWELS = {
    "\u05b1": "e",  # hataf segol
    "\u05b2": "a",  # hataf patah
    "\u05b3": "o",  # hataf qamats
    "\u05b4": "i",
    "\u05b5": "e",
    "\u05b6": "e",
    "\u05b7": "a",
    "\u05b8": "a",  # ordinary qamats: deliberately simple mapping
    "\u05b9": "o",
    "\u05ba": "o",
    "\u05bb": "u",
    QAMATS_QATAN: "o",
}
HEBREW_ACCENTS = {chr(cp) for cp in range(0x0591, 0x05AF)}
ACCENT_MARKS = HEBREW_ACCENTS | {METEG}
VOCALIZATION_MARKS = set(VOWELS) | {DAGESH, SHEVA, SHIN_DOT, SIN_DOT}
GUTTURALS = {"א", "ה", "ח", "ע"}
VOCALIC_FALLBACK_LETTERS = {"ו", "י", "א", "ע"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def letters_only(text: str) -> str:
    return "".join(FINAL_TO_BASE.get(ch, ch) for ch in text if ch in HEBREW_LETTERS)


def token_has_vocalization(token: str) -> bool:
    return any(ch in VOCALIZATION_MARKS for ch in token)


def split_hebrew_words(fragment: str) -> list[str]:
    """Extract Hebrew word spans; maqaf splits words and format controls do not."""
    fragment = unicodedata.normalize("NFC", fragment).replace(MAQAF, " ")
    output: list[str] = []
    current: list[str] = []
    for ch in fragment:
        if unicodedata.category(ch) == "Cf":
            continue
        is_hebrew_material = ch in HEBREW_LETTERS or 0x0591 <= ord(ch) <= 0x05C7
        if is_hebrew_material and ch not in {PASEQ, SOF_PASUQ}:
            current.append(ch)
        else:
            if current:
                word = "".join(current)
                if any(c in HEBREW_LETTERS for c in word):
                    output.append(word)
                current = []
    if current:
        word = "".join(current)
        if any(c in HEBREW_LETTERS for c in word):
            output.append(word)
    return output


def validate_source_marks(text: str) -> dict[str, int]:
    known = set(VOWELS) | {
        DAGESH,
        SHEVA,
        SHIN_DOT,
        SIN_DOT,
        METEG,
        PASEQ,
        SOF_PASUQ,
        MASORA_CIRCLE,
        RAFE,
        UPPER_DOT,
    } | HEBREW_ACCENTS
    unknown: dict[str, int] = {}
    for ch in unicodedata.normalize("NFC", text):
        cp = ord(ch)
        if 0x0591 <= cp <= 0x05C7 and unicodedata.category(ch).startswith("M") and ch not in known:
            unknown[ch] = unknown.get(ch, 0) + 1
    if unknown:
        detail = ", ".join(
            f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNKNOWN')} ({count})"
            for ch, count in sorted(unknown.items(), key=lambda item: ord(item[0]))
        )
        raise ValueError("Unsupported Hebrew combining mark(s): " + detail)
    return {
        "masora_circle_ignored": text.count(MASORA_CIRCLE),
        "rafe_ignored": text.count(RAFE),
        "upper_dot_ignored": text.count(UPPER_DOT),
    }


def select_reading_words(source_text: str) -> tuple[list[str], int]:
    """Choose bracketed qere and return only the performed Hebrew word stream."""
    text = unicodedata.normalize("NFC", source_text)
    if "<" in text or ">" in text:
        raise ValueError("HTML-like markup encountered in source verse")
    selected: list[dict] = []
    qere_events = 0
    pending = ""
    index = 0

    def flush(fragment: str) -> None:
        for word in split_hebrew_words(fragment):
            selected.append({"word": word, "plain": True})

    while index < len(text):
        ch = text[index]
        if ch == "[":
            flush(pending)
            pending = ""
            end = text.find("]", index + 1)
            if end < 0:
                raise ValueError("Unclosed square bracket in source verse")
            qere_words = split_hebrew_words(text[index + 1 : end])
            if not qere_words:
                raise ValueError("Bracketed qere contains no Hebrew word")
            while selected and selected[-1]["plain"] and not token_has_vocalization(selected[-1]["word"]):
                selected.pop()
            selected.extend({"word": word, "plain": False} for word in qere_words)
            qere_events += 1
            index = end + 1
            continue
        if ch == "(":
            flush(pending)
            pending = ""
            end = text.find(")", index + 1)
            if end < 0:
                raise ValueError("Unclosed parenthesis in source verse")
            index = end + 1
            continue
        pending += ch
        index += 1
    flush(pending)
    words = [item["word"] for item in selected]
    if not words:
        raise ValueError("No selected Hebrew words in source verse")
    return words, qere_events


def parse_units(token: str) -> list[tuple[str, list[str]]]:
    units: list[tuple[str, list[str]]] = []
    index = 0
    while index < len(token):
        ch = token[index]
        if ch in HEBREW_LETTERS:
            marks: list[str] = []
            cursor = index + 1
            while cursor < len(token) and token[cursor] not in HEBREW_LETTERS and token[cursor] != MAQAF:
                if 0x0591 <= ord(token[cursor]) <= 0x05C7:
                    marks.append(token[cursor])
                cursor += 1
            units.append((FINAL_TO_BASE.get(ch, ch), marks))
            index = cursor
        else:
            index += 1
    return units


def unit_info(unit: tuple[str, list[str]]) -> dict:
    letter, marks = unit
    return {
        "letter": letter,
        "marks": marks,
        "dagesh": DAGESH in marks,
        "sheva": SHEVA in marks,
        "sin_dot": SIN_DOT in marks,
        "vowel_marks": [mark for mark in marks if mark in VOWELS],
    }


def own_vowel(letter: str, info: dict) -> str:
    if letter == "ו" and info["dagesh"] and not info["vowel_marks"]:
        return "u"
    for mark in info["marks"]:
        if mark in VOWELS:
            return VOWELS[mark]
    return ""


def target_unit_for_accent(units: list, infos: list[dict], source_index: int, mark_index: int) -> int:
    letter, marks = units[source_index]
    before = marks[:mark_index]
    if any(mark in VOWELS for mark in before):
        return source_index
    if letter == "ו" and DAGESH in before and not any(mark in VOWELS for mark in marks):
        return source_index
    for index in range(source_index + 1, len(units)):
        if infos[index]["letter"] in VOCALIC_FALLBACK_LETTERS and own_vowel(infos[index]["letter"], infos[index]):
            return index
        if own_vowel(infos[index]["letter"], infos[index]):
            break
    if letter in VOCALIC_FALLBACK_LETTERS and not own_vowel(letter, infos[source_index]):
        for index in range(source_index + 1, len(units)):
            if own_vowel(infos[index]["letter"], infos[index]) or infos[index]["letter"] in VOCALIC_FALLBACK_LETTERS:
                return index
    for index in range(source_index - 1, -1, -1):
        if own_vowel(infos[index]["letter"], infos[index]):
            return index
    for index in range(source_index + 1, len(units)):
        if own_vowel(infos[index]["letter"], infos[index]) or infos[index]["letter"] in VOCALIC_FALLBACK_LETTERS:
            return index
    return source_index


def accent_targets(units: list, infos: list[dict]) -> list[int]:
    targets: list[int] = []
    for index, (_letter, marks) in enumerate(units):
        for mark_index, mark in enumerate(marks):
            if mark in ACCENT_MARKS:
                targets.append(target_unit_for_accent(units, infos, index, mark_index))
    return targets


def add_acute(segment: str) -> str:
    if COMBINING_ACUTE in unicodedata.normalize("NFD", segment):
        return segment
    for index, ch in enumerate(segment):
        if ch in "aeiou":
            return segment[: index + 1] + COMBINING_ACUTE + segment[index + 1 :]
    return segment


def add_acute_to_last_vowel(segment: str) -> str:
    for index in range(len(segment) - 1, -1, -1):
        if segment[index] in "aeiou":
            return segment[: index + 1] + COMBINING_ACUTE + segment[index + 1 :]
    return segment


def map_consonant(letter: str, info: dict, index: int, count: int, vowel: str) -> str:
    if letter in ("א", "ע"):
        return ""
    if letter == "ה":
        return "h" if index < count - 1 or info["dagesh"] else ""
    if letter == "ב":
        return "b" if info["dagesh"] else "v"
    if letter == "כ":
        return "k" if info["dagesh"] else "kh"
    if letter == "פ":
        return "p" if info["dagesh"] else "f"
    if letter == "ש":
        return "s" if info["sin_dot"] else "sh"
    if letter == "צ":
        return "ts"
    if letter == "ק":
        return "q"
    if letter == "ח":
        return "ch"
    if letter in ("ט", "ת"):
        return "t"
    if letter == "ו":
        if vowel == "o" and "\u05b9" in info["marks"]:
            return ""
        if vowel == "u" and (DAGESH in info["marks"] or "\u05bb" in info["marks"]):
            return ""
        return "v"
    if letter == "י":
        return "y"
    return {"ג": "g", "ד": "d", "ז": "z", "ל": "l", "מ": "m", "נ": "n", "ס": "s", "ר": "r"}.get(letter, letter)


def computational_sheva(index: int, infos: list[dict], previous_has_vowel: bool, base_letters: str) -> str:
    """Fixed limited sheva model; not a complete reading tradition."""
    count = len(infos)
    if index == count - 1:
        return ""
    if index == count - 2 and infos[index + 1]["sheva"]:
        return ""
    if index == 0:
        return "" if base_letters in {"שתי", "שתימ"} else "e"
    if infos[index - 1]["sheva"]:
        return "e"
    if infos[index]["dagesh"] and previous_has_vowel:
        return "e"
    if index + 1 < count and infos[index + 1]["sheva"]:
        return ""
    return ""


def should_drop_suffix_yod(units: list, infos: list[dict], index: int) -> bool:
    count = len(units)
    if index != count - 2 or infos[index]["letter"] != "י" or infos[index + 1]["letter"] != "ו" or index == 0:
        return False
    if "\u05b8" not in set(infos[index - 1]["marks"]):
        return False
    disallowed = set(VOWELS) | {SHEVA, DAGESH, SHIN_DOT, SIN_DOT}
    return not (set(infos[index]["marks"]) & disallowed) and not (set(infos[index + 1]["marks"]) & disallowed)


def transliterate_word(token: str) -> str:
    token = unicodedata.normalize("NFC", token)
    base_letters = letters_only(token)
    has_accent = any(ch in ACCENT_MARKS for ch in token)
    if base_letters == "יהוה":
        return add_acute_to_last_vowel("adonai") if has_accent else "adonai"
    if base_letters in {"אלהים", "אלוהים"}:
        return add_acute_to_last_vowel("elohim") if has_accent else "elohim"
    if base_letters and not token_has_vocalization(token):
        return ""

    units = parse_units(token)
    if not units:
        return ""
    infos = [unit_info(unit) for unit in units]
    segments: list[str] = []
    unit_to_segment: list[int | None] = [None] * len(units)
    previous_vowel = ""
    count = len(units)

    def append(unit_index: int, segment: str) -> None:
        if segment:
            unit_to_segment[unit_index] = len(segments)
            segments.append(segment)

    for index, (letter, _marks) in enumerate(units):
        info = infos[index]
        vowel = own_vowel(letter, info)
        if should_drop_suffix_yod(units, infos, index):
            continue
        if letter == "י" and not vowel and not info["sheva"]:
            if index == 0 or previous_vowel != "i":
                append(index, "y")
            continue
        if letter == "י" and vowel:
            segment = "i" if vowel == "i" and previous_vowel == "i" else "y" + vowel
            append(index, segment)
            previous_vowel = vowel
            continue

        realized_vowel = vowel
        if not vowel and info["sheva"]:
            previous_has_vowel = index > 0 and bool(infos[index - 1]["vowel_marks"])
            realized_vowel = computational_sheva(index, infos, previous_has_vowel, base_letters)
        if letter == "ח" and index == count - 1 and vowel == "a":
            append(index, "ach")
            previous_vowel = "a"
            continue
        consonant = map_consonant(letter, info, index, count, vowel)
        segment = vowel if letter == "ו" and vowel in ("o", "u") and not consonant else consonant + realized_vowel
        append(index, segment)
        if vowel or realized_vowel:
            previous_vowel = vowel or realized_vowel

    if not segments:
        return ""
    accented_segments: set[int] = set()
    for target in accent_targets(units, infos):
        segment_index = unit_to_segment[target]
        if segment_index is None or not any(ch in "aeiou" for ch in segments[segment_index]):
            candidates = [
                (abs(unit_index - target), unit_index, mapped)
                for unit_index, mapped in enumerate(unit_to_segment)
                if mapped is not None and any(ch in "aeiou" for ch in segments[mapped])
            ]
            if not candidates:
                continue
            segment_index = sorted(candidates)[0][2]
        if segment_index not in accented_segments:
            segments[segment_index] = add_acute(segments[segment_index])
            accented_segments.add(segment_index)
    return unicodedata.normalize("NFC", "".join(segments))


def count_marked_vowels(text: str) -> int:
    nfd = unicodedata.normalize("NFD", text)
    return sum(1 for index, ch in enumerate(nfd) if ch == COMBINING_ACUTE and index > 0 and nfd[index - 1] in "aeiou")


def process_book(source_path: Path, output_dir: Path, key: str) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    if source.get("schema") != "torah_word_rhyme.torah-source.v1" or source.get("key") != key:
        raise ValueError(f"Unexpected source file {source_path}")
    words: list[dict] = []
    readable_lines: list[str] = []
    qere_events = 0
    missing = 0
    ignored = {"masora_circle_ignored": 0, "rafe_ignored": 0, "upper_dot_ignored": 0}

    for verse_record in source["verses"]:
        counts = validate_source_marks(verse_record["text"])
        for name, count in counts.items():
            ignored[name] += count
        selected, verse_qere = select_reading_words(verse_record["text"])
        qere_events += verse_qere
        display: list[str] = []
        for position, hebrew in enumerate(selected, 1):
            transliteration = transliterate_word(hebrew)
            if not transliteration:
                missing += 1
            marked = count_marked_vowels(transliteration)
            words.append(
                {
                    "index": len(words) + 1,
                    "chapter": verse_record["chapter"],
                    "verse": verse_record["verse"],
                    "word_in_verse": position,
                    "hebrew": hebrew,
                    "transliteration": transliteration,
                    "marked_vowels": marked,
                    "eligible": bool(transliteration and marked),
                }
            )
            display.append(transliteration if transliteration else f"⟦{letters_only(hebrew)}⟧")
        readable_lines.append(" ".join(display) + " |")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{key}.json"
    payload = {
        "schema": "torah_word_rhyme.word-rhyme-corpus.v2",
        "key": key,
        "book": source["book"],
        "source_sha256": sha(source_path),
        "transliteration_rules": "simple-v1",
        "words": words,
    }
    output_path.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (output_dir / f"{key}.txt").write_bytes(("\n".join(readable_lines) + "\n").encode("utf-8"))
    return {
        "book": key,
        "word_count": len(words),
        "eligible_count": sum(word["eligible"] for word in words),
        "qere_event_count": qere_events,
        "unresolved_count": missing,
        "ignored_source_marks": ignored,
        "source_sha256": sha(source_path),
        "output_sha256": sha(output_path),
    }


def main() -> int:
    raw_dir = ROOT / "data/raw"
    output_dir = ROOT / "data/processed"
    summaries = []
    for key in TORAH:
        source_path = raw_dir / f"{key}.json"
        if not source_path.exists():
            raise SystemExit(f"Missing {source_path}; run run\\download_sources.bat first")
        summary = process_book(source_path, output_dir, key)
        summaries.append(summary)
        print(
            f"{key}: words={summary['word_count']} eligible={summary['eligible_count']} "
            f"qere={summary['qere_event_count']} unresolved={summary['unresolved_count']}"
        )
    manifest = {
        "schema": "torah_word_rhyme.word-rhyme-preprocessing-run.v2",
        "created_utc": now(),
        "rules": "simple-v1",
        "script_sha256": sha(Path(__file__)),
        "books": summaries,
    }
    (output_dir / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
