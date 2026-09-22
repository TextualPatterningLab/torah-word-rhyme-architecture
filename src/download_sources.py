#!/usr/bin/env python3
"""Download and validate a version-pinned Sefaria Torah snapshot."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "Tanach with Ta'amei Hamikra"
BOOKS = {
    "genesis": "Genesis",
    "exodus": "Exodus",
    "leviticus": "Leviticus",
    "numbers": "Numbers",
    "deuteronomy": "Deuteronomy",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def encode(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_response(payload: bytes, key: str, requested_version: str) -> tuple[dict, bytes]:
    response = json.loads(payload.decode("utf-8-sig"))
    title = BOOKS[key]
    if not isinstance(response, dict) or response.get("error"):
        raise ValueError("Sefaria returned an API error or invalid object")
    if response.get("ref") != title or response.get("sections", []) or response.get("isComplex"):
        raise ValueError(f"Expected complete simple book {title!r}; received {response.get('ref')!r}")
    returned_version = response.get("heVersionTitle")
    if not isinstance(returned_version, str) or normalized(returned_version) != normalized(requested_version):
        raise ValueError(f"Requested {requested_version!r}; returned {returned_version!r}; fallback rejected")
    chapters = response.get("he")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("Missing chapter array")

    verses: list[dict] = []
    raw_lines: list[str] = []
    chapter_lengths: list[int] = []
    for chapter_number, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, list) or not chapter:
            raise ValueError(f"Invalid or empty chapter {chapter_number}")
        chapter_lengths.append(len(chapter))
        for verse_number, text in enumerate(chapter, 1):
            if not isinstance(text, str) or not text.strip() or not re.search("[א-ת]", text):
                raise ValueError(f"Invalid Hebrew text at {chapter_number}:{verse_number}")
            line = re.sub(r"\s+", " ", text).strip()
            verses.append({"chapter": chapter_number, "verse": verse_number, "text": text})
            raw_lines.append(line)
    if not re.search("[\u05b0-\u05bb\u05c7]", "".join(raw_lines)):
        raise ValueError("No Hebrew vowel points found")

    raw = ("\n".join(raw_lines) + "\n").encode("utf-8")
    source = {
        "schema": "torah_word_rhyme.torah-source.v1",
        "key": key,
        "book": title,
        "requested_version": requested_version,
        "returned_version": returned_version,
        "source_metadata": {
            field: response.get(field)
            for field in ("heVersionSource", "heLicense", "heStatus", "heVersionNotes")
        },
        "chapter_count": len(chapters),
        "chapter_lengths": chapter_lengths,
        "verse_count": len(verses),
        "raw_sha256": sha(raw),
        "response_sha256": sha(payload),
        "verses": verses,
    }
    return source, raw


def validate_saved(source_path: Path, raw_path: Path, key: str, version: str) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    if source.get("schema") != "torah_word_rhyme.torah-source.v1":
        raise ValueError(f"Unexpected source schema in {source_path}")
    if source.get("key") != key or source.get("book") != BOOKS[key]:
        raise ValueError(f"Book mismatch in {source_path}")
    if normalized(str(source.get("requested_version", ""))) != normalized(version):
        raise ValueError("Saved source uses another requested version; inspect it or use --refresh")
    raw = raw_path.read_bytes()
    rebuilt = ("\n".join(re.sub(r"\s+", " ", v["text"]).strip() for v in source["verses"]) + "\n").encode("utf-8")
    if raw != rebuilt or sha(raw) != source.get("raw_sha256"):
        raise ValueError(f"Saved source checksum or verse map mismatch for {key}")
    if len(source["verses"]) != source.get("verse_count"):
        raise ValueError(f"Saved verse count mismatch for {key}")
    return source


def fetch(url: str, timeout: int, retries: int) -> tuple[bytes, str]:
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "torah-word-rhyme-architecture/1.0"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries:
                raise
        time.sleep(min(2**attempt, 8))
    raise RuntimeError("unreachable")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0 or not 0 <= args.retries <= 5:
        raise SystemExit("timeout must be positive and retries must be between 0 and 5")
    raw_dir = args.root / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    failures = 0
    print(f"Requested version: {args.version}", flush=True)

    for key, title in BOOKS.items():
        source_path = raw_dir / f"{key}.json"
        raw_path = raw_dir / f"{key}.txt"
        try:
            if not args.refresh and source_path.exists() and raw_path.exists():
                source = validate_saved(source_path, raw_path, key, args.version)
                status = "cached"
            else:
                if not args.refresh and (source_path.exists() or raw_path.exists()):
                    raise ValueError("Partial source files exist; inspect them or use --refresh")
                params = urllib.parse.urlencode(
                    {
                        "lang": "he",
                        "vhe": args.version,
                        "context": 0,
                        "pad": 0,
                        "commentary": 0,
                        "wrapLinks": 0,
                        "fallbackOnDefaultVersion": 0,
                    }
                )
                url = "https://www.sefaria.org/api/texts/" + urllib.parse.quote(title, safe="") + "?" + params
                print(f"Downloading {title} ...", flush=True)
                payload, final_url = fetch(url, args.timeout, args.retries)
                source, raw = validate_response(payload, key, args.version)
                source.update(
                    {
                        "retrieved_utc": now(),
                        "request_url": url,
                        "final_url": final_url,
                        "downloader_sha256": sha(Path(__file__).read_bytes()),
                    }
                )
                atomic(source_path, encode(source))
                atomic(raw_path, raw)
                source = validate_saved(source_path, raw_path, key, args.version)
                status = "downloaded"
            rows.append(
                {
                    "book": key,
                    "status": status,
                    "chapters": source["chapter_count"],
                    "verses": source["verse_count"],
                    "source_sha256": sha(source_path.read_bytes()),
                    "raw_sha256": source["raw_sha256"],
                }
            )
            print(f"{key}: chapters={source['chapter_count']} verses={source['verse_count']} {status} OK", flush=True)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            failures += 1
            rows.append({"book": key, "status": "error", "error": str(exc)})
            print(f"{key}: ERROR: {exc}", flush=True)
        time.sleep(0.25)

    manifest = {
        "schema": "torah_word_rhyme.torah-download-run.v1",
        "finished_utc": now(),
        "requested_version": args.version,
        "results": rows,
        "errors": failures,
    }
    atomic(raw_dir / "manifest.json", encode(manifest))
    print(f"Finished: {len(BOOKS) - failures} OK; {failures} errors.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
