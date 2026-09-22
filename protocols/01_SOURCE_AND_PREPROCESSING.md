# Protocol 1: source and preprocessing

## Source

The downloader requests the complete five books of the Torah from Sefaria using the Hebrew version title `Tanach with Ta'amei Hamikra`. It rejects a silent fallback to another version.

For each book it stores:

- `data/raw/<book>.json`: source metadata plus the API chapter/verse text as returned;
- `data/raw/<book>.txt`: one whitespace-normalized API verse per line for convenient inspection.

`data/raw/manifest.json` records hashes, counts, version information, and retrieval time. A saved source is reused only after structural and hash validation. `--refresh` explicitly replaces it.

The repository includes a frozen snapshot so passage inspection does not require network access.

## Reading stream

- Bracketed qere supplied by the source is selected for analysis.
- The untouched qere/ketiv notation remains recoverable in the raw source.
- Parenthesized section signs are not analytical words.
- Maqaf separates analytical words.
- Unicode format controls inside a Hebrew token are ignored and may not split the word.

## Computational transliteration

The transliteration is a deterministic computational representation, not a complete reconstruction of historical or living pronunciation.

- U+05B8 qamats -> `a`.
- U+05C7 qamats qatan -> `o`.
- U+05B3 hataf qamats -> `o`.
- Sheva is resolved by the fixed limited rules implemented in `src/preprocess_corpus.py`.
- `ch`, `kh`, `sh`, and `ts` are computational multigraphs.
- Article-facing spelling may use `tz` for computational `ts`.

The pipeline does not add passage-specific pronunciation corrections. Fuller reading rules may be used in close-reading examples without silently altering the analytical corpus.

## Prominence marking

Every recognized in-word taam or meteg event is mapped to an acute accent on its selected Latin vowel. Taam names themselves are not printed in the processed reading view.

A word may contain more than one marked vowel. The passage-inspection signature uses the **final marked vowel**. In ordinary cases this captures the final lexical-accent prominence while retaining a deterministic treatment of the source marks.

## Outputs

For each book:

- `data/processed/<book>.json`: authoritative compact machine corpus;
- `data/processed/<book>.txt`: one verse per line, computational transliteration plus final `|` only.

The JSON retains sequential word index, chapter, verse, word position, Hebrew token, transliteration, marked-vowel count, and eligibility.

`data/processed/manifest.json` records counts and hashes.
