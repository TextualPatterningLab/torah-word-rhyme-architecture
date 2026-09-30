# Generated and frozen results

## Passage inspection

Each local inspection run creates a subdirectory under `results/passages/`.

The repository includes one frozen strict example, Deut. 11:10–15, because the Example Catalogue refers to that audit. Other user-generated passage outputs need not be committed.

## Descriptive distribution visualization

`results/distribution/default_strict/` contains the committed default output of the descriptive Pentateuch-wide visualization:

- `distribution.svg` — vector repository/browser figure;
- `distribution.pdf` — vector figure;
- `distribution.png` — 300-dpi preview;
- `density.tsv` — local-window values;
- `summary.json` — parameters, counts, hashes, and environment;
- `caption.txt` — parameter-matched descriptive caption.

It is generated with strict segment identity, exact repeated words included, no morphological stripping, comparison radius `L=20`, local window `250`, step `50`, and the default blue-to-purple palette. It is an exploratory descriptive map, not a control-corpus comparison or significance test.

Additional user-generated distribution runs are ignored by default and need not be committed.
