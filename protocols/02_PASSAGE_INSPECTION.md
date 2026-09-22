# Protocol 2: passage inspection of word-final correspondences

## Scope

The tool is an inspection aid. It reports mechanically accepted word-final correspondences inside a user-selected Torah passage. It does not infer literary function, intention, genre, date, melody, or meter.

The strict result and the optional close-correspondence result are intentionally kept distinct.

## Signature rule

For each eligible word:

1. segment the computational transliteration; `ch`, `kh`, `sh`, and `ts` count as single segments;
2. locate the final vowel bearing an acute prominence mark;
3. take that vowel and all following segments through word end;
4. if the marked vowel is the final phonetic segment, extend exactly one segment left.

Words without a mapped marked vowel remain in the processed corpus but do not enter the eligible comparison stream.

## Strict identity

With no `--equiv` option, two signatures are accepted only when:

- they contain the same number of segments; and
- every corresponding segment is identical.

These matches are reported as `EXACT`.

## Optional close consonantal correspondences

The following heuristic switches may be activated independently:

| Switch | Accepted non-identical consonantal pair(s) |
| --- | --- |
| `vf` | v ~ f |
| `dt` | d ~ t |
| `pb` | p ~ b |
| `qk` | q ~ k |
| `chkh` | ch ~ kh |
| `dental` | every direct pair among t, ts, s, z |
| `all` | activates all switches above |

Vowels remain exact under every setting.

The switches are pairwise and non-transitive. For example, enabling `dt` and `dental` does not license an arbitrary new d ~ s relation unless such a pair is itself explicitly defined.

A match requiring at least one enabled non-identical pair is reported as `CLOSE`, and `pairs.tsv` records the switch or switches actually used.

The optional switches are sensitivity/inspection parameters. Their availability does not imply that all listed pairs are equivalent in every Hebrew reading tradition or historical period.

## Exact repeated words

Exact normalized lexical repetition is included by default:

```text
--exact-words include
```

It can be excluded:

```text
--exact-words exclude
```

Repeated words and productive endings are not presumed to be analytically irrelevant. No morphological suffix is automatically stripped.

## Comparison radius

`--window-left N` compares each eligible target word with the preceding `N` eligible words.

- default: `20`;
- `0`: compare with every earlier eligible word in the selected passage.

The radius is an inspection parameter rather than a claim about a fixed poetic span.

## Passage selection

Required arguments:

```text
--book BOOK
--start CHAPTER:VERSE
--end CHAPTER:VERSE
```

Book aliases include `gen`, `ex`, `lev`, `num`, and `deut`.

## Outputs

Each run writes four files below `results/passages/<label>/`:

- `annotated.txt`: selected passage, one verse per line, with the terminal signature appended to each participating word;
- `pairs.txt`: readable exact groups followed, when enabled, by pairwise close correspondences;
- `pairs.tsv`: complete machine-readable pair inventory with positions, Hebrew forms, transliterations, distances, relation type, and equivalence audit;
- `summary.json`: parameters, counts, and SHA-256 hashes of the processed input, inspection script, and matching engine.

For a non-transitive optional setting, only the pairs actually tested and accepted are reported. Connected chains are never silently converted into larger equivalence classes.

## Reproducible strict example

The repository includes a frozen run for Deut. 11:10–15:

```bat
run\inspect_passage.bat --book deuteronomy --start 11:10 --end 11:15 --exact-words include --window-left 20 --label deuteronomy_11-10_11-15_strict
```

This run activates no optional sound correspondences.
