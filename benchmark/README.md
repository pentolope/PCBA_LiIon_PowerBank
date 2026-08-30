# Benchmark entry — board 7 of 32

[metadata.json](metadata.json) is the supplied catalogue entry for this board,
preserved byte for byte from the seed pack. It is the same record that appears
in `boards_index.json` in
[PCBA_AutoDesignAndTest_Bench](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench), and the two must agree.

| | |
|---|---|
| Repository | `PCBA_LiIon_PowerBank` |
| Board id | `liion_power_bank` |
| Category | power-management |
| Difficulty | 2 / 5 |
| Brief detail | 2 / 5 |
| Likely layer count | 2 or 4 |
| Primary stressors | charger layout, power-path routing, battery safety, USB-C power |

`difficulty` is how hard the board is. `detail` is how much of it the brief
states — and a low `detail` is not a low bar. A detail-1 brief leaves the
architecture open on purpose, and an agent that fills the silence with invented
user requirements has failed the board more thoroughly than one that designs it
badly.

This is a difficulty-2, detail-2 power-management board whose stressors are charger layout, power-path routing, battery safety, and USB-C power. It tests whether an agent can turn a short functional brief into a defensible power chain — sizing, selecting, and laying out a charger, a power path, and a 5 V output stage — and whether it can substantiate a 2 A output claim with real datasheet, magnetics, and thermal evidence instead of asserting it. Because the brief names no parts and no mechanics, it equally tests whether the agent keeps its own choices visible as choices rather than smuggling them in as requirements.

## What goes here

Compact results only: metrics, verdicts, and the commit each was measured at.
The evidence for a result is the artefact the toolkit recomputes, not a summary
of it.

Routing search output, candidate pools, build trees and field-solver dumps do
**not** go here. They are ignored by [.gitignore](../.gitignore) and are
regenerated from what is committed. Thirty-two repositories share one benchmark
clone; weight here is paid thirty-two times.

## Protocol

The attempt protocol is defined once, in the umbrella repository, so that
thirty-two boards cannot drift into thirty-two protocols. See
[PCBA_AutoDesignAndTest_Bench/BENCHMARK.md](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench/blob/main/BENCHMARK.md).
