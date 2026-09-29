# Protocol 4: descriptive distribution visualization

## Scope

The distribution tool is an **exploratory descriptive visualization aid**. It applies the same stress/marked-vowel word-final signature and optional consonantal correspondence engine used by the passage-inspection tool, then maps local participation across the five Torah books.

It is not presented as:

- a comparison with an external control corpus;
- a statistical significance or non-randomness test;
- evidence that one Torah book is more "poetic" than another;
- a claim that the Torah is exceptional relative to other Hebrew corpora;
- an inference about authorship, source division, date, melody, or historical meter.

The map answers a narrower descriptive question: **under one explicit set of matching parameters, where within each Torah book do eligible words participate more or less densely in accepted local word-final correspondences?**

## Optional visualization dependency

Passage inspection has no third-party Python dependency. The distribution figure requires Matplotlib:

```bat
python -m pip install -r requirements-visualization.txt
```

## Default run

From the repository root:

```bat
run\visualize_distribution.bat --label default_strict
```

With no other options, the defaults are:

- strict segment identity (`--equiv` omitted);
- exact repeated words **included**;
- no morphological endings stripped;
- each eligible word compared with the preceding 20 eligible words (`--window-left 20`);
- local descriptive window of 250 eligible words (`--density-window 250`);
- window step of 50 eligible words (`--step 50`);
- displayed metric: proportion of words in each local window participating in at least one accepted correspondence (`participating_rate`);
- blue-to-purple `BuPu` palette (`--palette bluepurple`).

These are fixed visualization defaults, not a claim about a unique natural poetic span.

## Signature and matching rule

The tool imports `src/rhyme.py`, so its word-final signatures are identical to those used by `inspect_passage.py`:

1. locate the final vowel carrying an acute prominence mark in the computational transliteration;
2. take that vowel and all following segments through word end;
3. if that marked vowel is itself word-final, extend exactly one segment left;
4. with no `--equiv` setting, accept only segment-by-segment identity.

See `02_PASSAGE_INSPECTION.md` for the full matching specification.

## Optional sensitivity settings

The same documented consonantal switches may be supplied, for example:

```bat
run\visualize_distribution.bat --equiv vf --equiv qk --label vf-qk
```

or:

```bat
run\visualize_distribution.bat --equiv all --label all-close
```

Exact repeated words can be excluded as a sensitivity view:

```bat
run\visualize_distribution.bat --exact-words exclude --label without-exact-repetition
```

The local radius and smoothing window can also be changed explicitly:

```bat
run\visualize_distribution.bat --window-left 30 --density-window 300 --step 50 --label L30-W300
```

Alternative display palettes are available without changing the underlying values:

```bat
--palette bluepurple
--palette blues
--palette purples
--palette gray
```

Optional settings are intended for inspection. They are not optimized or selected to maximize contrast between books.

## Outputs

Each run writes to:

```text
results/distribution/<label>/
```

with:

- `distribution.svg` — vector figure for repository/browser use;
- `distribution.pdf` — vector figure suitable for journal Supplementary Material;
- `distribution.png` — 300-dpi raster preview;
- `density.tsv` — local-window values used to draw the map;
- `summary.json` — parameters, corpus hashes, code hashes, environment, and book-level descriptive counts;
- `caption.txt` — a parameter-matched suggested caption for Supplementary Figure S1.

The three figure formats represent the same data and settings.

The figure uses a shared within-run color scale so the five books can be inspected under the same parameter set. Its horizontal axis is relative position within each book. Horizontal display position is normalized to 0–100% separately for each book; the underlying matching calculations are performed on the actual eligible-word sequence and are not rescaled.

## Interpreting the default map

The default committed map retains exact lexical repetition because repeated wording may itself participate in formal organization. Productive Hebrew morphology is likewise retained. The visualization therefore should not be read as isolating a morphology-free or repetition-free quantity called "rhyme." It displays the local behavior of the stated operational correspondence rule on the received computational text.

A reader who wants to examine sensitivity to exact lexical repetition or to optional close consonantal relations can regenerate the map under those settings without changing the underlying corpus.

## Suggested Supplementary Figure wording

The default run writes a full parameter-matched caption to `caption.txt`. For the article submission, the intended role is descriptive and supplementary: the figure provides a visible map of the repository tool's default output but is not used as an external-corpus comparison or statistical proof of poetic status.
