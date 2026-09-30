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
- Human-readable close-reading examples may use `tz` for computational `ts`.

The pipeline does not add passage-specific pronunciation corrections. Fuller reading rules may be used in close-reading examples without silently altering the analytical corpus.

## Prominence marking

Recognized in-word taam or meteg events are mapped to acute accents on selected Latin vowels, with one general exception: when a word has two pashta signs and the second is on its final letter, the internal pashta supplies the prominence target; the final, postpositive repetition does not add another acute. Both signs remain intact in the stored Hebrew and raw source. This rule applies uniformly, not through passage-specific corrections. Taam names themselves are not printed in the processed reading view.

A word may contain more than one marked vowel. The passage-inspection signature uses the **final marked vowel**. In ordinary cases this captures the final lexical-accent prominence while retaining a deterministic treatment of the source marks.

This is a demonstrative marked-vowel heuristic, not a complete lexical-stress resolver. Other prepositive/postpositive signs and meteg combinations may still produce a mapped prominence different from the reading tradition. Inspect Hebrew and check pronunciation manually before interpreting an individual match or absence. Close-reading examples are evaluated independently of this utility; the distribution map is not a statistical test of poetic status.

Two implementation details are relevant when checking individual words. A mark on a final consonant without its own vowel is mapped back to the preceding available vowel. Final chet with patah is rendered as `ach`, as in `rúach`; however, furtive-patah handling is not generalized to all final gutturals, and the mapping does not separately prevent an acute on that final `a` when the source mark targets it. Such cases require manual reading checks. These limitations can affect both reported correspondences and omissions; an absent match is not evidence that a literary echo is absent.

The rule identifier `simple-v2-pashta` distinguishes this limited correction from the original `simple-v1` mapping. No other pronunciation rule is changed.

## Outputs

For each book:

- `data/processed/<book>.json`: authoritative compact machine corpus;
- `data/processed/<book>.txt`: one verse per line, computational transliteration plus final `|` only.

The JSON retains sequential word index, chapter, verse, word position, Hebrew token, transliteration, marked-vowel count, and eligibility.

`data/processed/manifest.json` records counts and hashes.
