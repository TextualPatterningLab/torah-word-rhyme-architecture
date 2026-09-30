# Revision notes

## 1.0.2 — 2026-09-30

- Clarify normalized horizontal position, eligible-word counts, and shared proportion scale in the README, visualization protocol, and generated caption.
- Document the final-consonant fallback and the limited handling of furtive patah, including possible missed matches.
- Keep the repository standalone and publication-neutral; examples, audio, visualization, and tests are documented as reusable repository resources.
- Preserve preprocessing, matching rules, corpus, audio bytes, and numerical results unchanged.
- Clarify reproducibility wording for generated visualization files.

## 1.0.1 — 2026-09-29

This revision keeps the digital component demonstrative. It does not implement a complete Hebrew stress resolver.

- Describe all three audio files as preliminary, approximate listening illustrations; retain their original bytes.
- Align catalogue evidence labels and source notes.
- Apply a general repeated-pashta rule: when exactly two pashta signs occur and the second is on the final letter, only the internal sign supplies a prominence target. Stored Hebrew remains unchanged.
- Regenerate all five processed books and the committed passage and distribution outputs from the unchanged raw snapshot.
- Document remaining limitations of the marked-vowel heuristic.
- Generate visualization captions from actual matching, radius, window, and metric parameters.
- Add small reading fixtures for tohu/vavohu, beveytékha/beshivtekhá, máyim, and ordinary or endings.

The correction changes 934 displayed token transliterations and 898 terminal signatures. Book-level eligible counts remain unchanged. Signature changes: Genesis 262; Exodus 192; Leviticus 115; Numbers 154; Deuteronomy 175.

Default STRICT pair counts before -> after:

| Book | Before | After |
|---|---:|---:|
| Genesis | 10084 | 10056 |
| Exodus | 8913 | 8864 |
| Leviticus | 6796 | 6799 |
| Numbers | 9175 | 9220 |
| Deuteronomy | 8167 | 8120 |

The committed Deuteronomy 11:10–15 example changes from 38 to 37 pairs. These counts describe the limited rule, not validated corpus-wide lexical rhyme rates.

Verification: `python -m unittest discover -s tests -v`, complete preprocessing, passage inspection, and distribution regeneration. No raw-source or audio change.
