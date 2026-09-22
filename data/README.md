# Frozen Torah data

`raw/` contains the version-pinned Sefaria source snapshot and source metadata.

`processed/` contains the deterministic word corpus used by the passage-inspection tool plus a readable transliteration view.

The repository ships with these files so inspection does not depend on live API access. See `protocols/01_SOURCE_AND_PREPROCESSING.md` before interpreting the transliteration.
