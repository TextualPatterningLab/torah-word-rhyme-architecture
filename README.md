# Torah Poetic Organization — Inspection and Demonstration Toolkit

Anonymous research repository for inspecting selected forms of sound recurrence and poetic organization in the Torah.

The repository is designed as a standalone, reusable research resource. It provides:

1. a frozen, auditable Torah text snapshot and deterministic computational transliteration;
2. a passage-inspection tool for examining marked-vowel word-final correspondences in any selected Torah range;
3. a documented set of optional consonantal similarity settings for sensitivity inspection;
4. an extended Example Catalogue for close-reading examples beyond the terminal matching rule;
5. experimental rhythmic audio realizations with listening notes;
6. an optional descriptive distribution visualization using the same word-final matching engine;
7. small regression tests for selected preprocessing rules.

The digital tools are intentionally limited and transparent. The passage inspector implements one reproducible final-marked-vowel heuristic; it is not a complete lexical-stress, pronunciation, morphology, or poetics model. The repeated-pashta correction and remaining limitations are documented in Protocol 1. The tools do not decide literary function, authorial intention, genre, historical meter, or melody.

## Start here

The frozen processed corpus is already included, so the inspection tool can be run immediately with Python 3.10+ and no third-party packages.

From the repository root on Windows:

```bat
run\inspect_passage.bat --book deuteronomy --start 11:10 --end 11:15
```

This uses strict segment identity, includes exact repeated words, and compares each eligible word with the preceding 20 eligible words.

To compare every earlier eligible word inside the selected passage:

```bat
run\inspect_passage.bat --book deuteronomy --start 11:10 --end 11:15 --window-left 0
```

To add selected close consonantal correspondences:

```bat
run\inspect_passage.bat --book deuteronomy --start 11:10 --end 11:15 --equiv vf --equiv qk
```

To activate all documented optional correspondences:

```bat
run\inspect_passage.bat --book deuteronomy --start 11:10 --end 11:15 --equiv all
```

The available equivalence switches are:

- `vf`: v ~ f
- `dt`: d ~ t
- `pb`: p ~ b
- `qk`: q ~ k
- `chkh`: ch ~ kh
- `dental`: every direct pair among t, ts, s, z
- `all`: all of the above

These options are heuristic sensitivity settings. They are not treated as transitive equivalence classes and do not alter vowels.

## Rhyme/correspondence rule

For each eligible computationally transliterated word, the tool:

1. segments the transliteration (`ch`, `kh`, `sh`, and `ts` count as single segments);
2. locates the final vowel carrying an acute prominence mark;
3. takes that vowel and every following segment through the end of the word;
4. if the marked vowel is itself word-final, extends exactly one segment to the left.

With no `--equiv` option, two signatures match only if every segment is identical. When optional equivalences are enabled, a non-identical pair is reported separately as a **CLOSE** correspondence and records which switch was used.

Exact repeated words are included by default because repetition may itself be structurally relevant. They can be excluded with:

```bat
--exact-words exclude
```

No morphological endings are automatically stripped.

## Output

Each inspection run creates a folder under `results/passages/` containing:

- `annotated.txt` — the selected passage with signatures marked on participating words;
- `pairs.txt` — a readable grouping of exact terminal correspondences plus any optional close correspondences;
- `pairs.tsv` — every accepted pair with locations, distance, Hebrew, transliteration, signatures, and audit fields;
- `summary.json` — parameters, counts, and SHA-256 hashes.

A frozen strict example for Deut. 11:10–15 is included at:

```text
results/passages/deuteronomy_11-10_11-15_strict/
```

## Descriptive distribution visualization

The repository also provides an optional Pentateuch-wide visualization of the same final-marked-vowel correspondence rule:

```bat
run\visualize_distribution.bat --label default_strict
```

The default view uses strict segment identity, includes exact repeated words, strips no morphological endings, compares each eligible word with the preceding 20 eligible words, and maps local participation in 250-word windows stepped by 50 eligible words. The five books are displayed under one shared within-run scale with a blue-to-purple palette.

Horizontal position is normalized separately to 0–100% of each book's eligible-word sequence; equal strip widths do not represent equal book lengths. The n labels give eligible-word counts. Matching distances and local windows use actual word counts, not percentages. The shared color scale represents local proportions, not absolute numbers of words.

The visualization requires Matplotlib, installed separately so the passage-inspection tool remains dependency-free:

```bat
python -m pip install -r requirements-visualization.txt
```

Each run writes the same visualization as **SVG, PDF, and 300-dpi PNG**, together with `density.tsv`, `summary.json`, and a parameter-matched `caption.txt`.

The tool accepts the same optional consonantal similarity switches as passage inspection, as well as `--exact-words exclude`, alternative comparison radii, local-window sizes, step sizes, and alternative display palettes. Full details are in `protocols/04_DISTRIBUTION_VISUALIZATION.md`.

This visualization is **descriptive and exploratory**. It is not a comparison with an external control corpus, a significance test, a poetry classifier, or evidence that the Torah is statistically exceptional relative to other Hebrew corpora. The committed default output is provided so users can inspect one fixed parameterization and regenerate the same data and visual output.

## Example Catalogue and audio

`examples/` contains the extended **Torah Poetic Organization — Example Catalogue**, which distinguishes core, supporting, textual-form, exploratory, and orientation examples. It includes mechanisms that the terminal inspection tool intentionally does not attempt to classify, such as medial echoes, consonantal fields, junctional effects, formulaic recurrence, and long-range rhetorical relations.

`audio/` contains preliminary rhythmic sketches and accompanying listening notes. They illustrate approximate rhythmic delivery and are provided as listening aids, not as reconstructions of ancient melody or historical meter. The documented Cubase tempo/meter values describe the individual realizations only.

The *Ana BeKoach* realization is explicitly comparative: its dense recurrent endings and short cadential units make several sound-organizational mechanisms easy to perceive before analogous but more distributed relations are considered in biblical examples. It is not part of the Torah corpus and is not evidence for Torah-wide conclusions.

See `protocols/03_EXAMPLES_AND_AUDIO.md` for the scope and status of these materials.

## Frozen text and preprocessing

The repository includes both the downloaded source snapshot and the processed corpus:

```text
data/raw/          version-pinned Sefaria snapshot + readable verse text
data/processed/    machine corpus + readable computational transliteration
```

The downloader requests the Sefaria Hebrew version titled `Tanach with Ta'amei Hamikra` and rejects silent fallback to another version. Qere supplied by the source is used for the performed reading stream; the raw source preserves the original source notation for audit.

The computational transliteration is deliberately deterministic and narrower than pronunciation-oriented transliteration used in the close-reading examples. See `protocols/01_SOURCE_AND_PREPROCESSING.md`.

## Rebuilding the frozen corpus

The included snapshot is sufficient for inspection. To validate or rebuild it:

```bat
run\download_sources.bat
run\preprocess_corpus.bat
```

`download_sources.bat` reuses and validates the frozen local snapshot unless `--refresh` is passed.

## Tests

Run the included regression tests with:

```bat
python -m unittest discover -s tests -v
```

The tests are small fixtures for selected preprocessing behavior; they are not a corpus-wide validation of Hebrew stress or pronunciation.

## Repository layout

```text
audio/             experimental rhythmic realizations + listening notes
data/raw/          frozen Sefaria source snapshot
data/processed/    deterministic analytical corpus
examples/          extended Example Catalogue
protocols/         source, inspection, examples/audio, and visualization specifications
results/passages/  reproducible passage-inspection outputs
results/distribution/default_strict/  committed default descriptive map + audit tables
run/               Windows launchers
src/               downloader, preprocessing, inspection, and visualization code
tests/             regression fixtures for selected preprocessing rules
```

## Version

`VERSION` identifies the repository release. Revision notes are recorded in `CHANGELOG.md`.
