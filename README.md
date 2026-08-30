# Single-Cell Li-Ion Power Bank

Single-cell Li-ion power bank board: USB-C input, battery charging and protection, and a regulated 5 V output capable of at least 2 A.

This repository holds the design problem for `PCBA_LiIon_PowerBank`, a single-cell Li-ion power bank board. The brief fixes the functional envelope: a USB-C input, battery charging, battery protection, a regulated 5 V output capable of at least 2 A, fuel/status indication, and a pushbutton-controlled output enable. It also states two process constraints — choose an integrated charger/power-path/boost solution where practical, and respect the layout guidance of the selected power ICs while minimizing high-current loop area — and instructs that stated requirements be treated as authoritative. Everything else is open: the brief names no part, vendor, IC, connector, cell, capacity, dimension, charge current, input power level, output-stage topology, stackup, or protection topology, so the architecture and every component choice belong to the design agent. At brief detail 2/5, the correct response is to make and document those decisions from cited evidence rather than to treat any of them as pre-fixed.

> **This board has not been designed.** There is no schematic, no layout and no
> part selection here — only the brief, a reading of the brief, and the
> scaffolding a design run needs. That is the intended state of this repository,
> not a gap in it.

## What the brief fixes, and what it leaves open

The brief pins down 13 requirements and deliberately leaves
19 decisions to whoever designs the board. The `Source` column says
which is which: `brief` is quoted from [BRIEF.md](BRIEF.md), `metadata` comes
from the benchmark catalogue, and `open` means the brief does not fix it.

| Aspect | Value | Source |
|---|---|---|
| Board function | Single-cell Li-ion power bank board | brief |
| Input interface | USB-C input | brief |
| Charging | Battery charging on the board | brief |
| Battery protection | Battery protection required (location and topology unstated) | brief |
| Output rail | Regulated 5 V, capable of at least 2 A | brief |
| Indication | Fuel/status indication (form not specified) | brief |
| User control | Pushbutton-controlled output enable | brief |
| Power IC integration preference | Integrated charger/power-path/boost solution where practical (a preference, with "practical" left undefined) | brief |
| Layout constraint | Follow the selected power ICs' layout guidance; minimize high-current loop area | brief |
| Requirement authority | Stated requirements are authoritative; where the brief is open, the agent makes and documents the decision | brief |
| Toolkit relationship | Repo consumes the shared PCBA_AutoDesignAndTest toolkit; no board-specific logic added to the toolkit | brief |
| Likely layer count | 2 or 4 (stated as "likely" in both the brief header and metadata; fixed by neither) | metadata |
| Category / difficulty / brief detail | power-management; difficulty 2; detail 2 | metadata |
| Primary stressors | charger layout, power-path routing, battery safety, USB-C power | metadata |
| Parts, connectors, cell, mechanics, charge current, input power level, output-stage and protection topology | Not fixed by the brief — design agent's choice | open |

The full split, with the verbatim brief text substantiating every fixed
requirement, is in [board/requirements.md](board/requirements.md) and
machine-readably in [board/requirements.json](board/requirements.json).

**Missing details are design freedom, not permission to fabricate unstated user
requirements.** A choice the brief left open is recorded as a decision, with its
reasoning — never promoted into a requirement.

## Benchmark position

| | |
|---|---|
| Benchmark id | 7 of 32 |
| Category | power-management |
| Difficulty | 2 / 5 |
| Brief detail | 2 / 5 |
| Likely layer count | 2 or 4 |
| Primary stressors | charger layout, power-path routing, battery safety, USB-C power |

This is a difficulty-2, detail-2 power-management board whose stressors are charger layout, power-path routing, battery safety, and USB-C power. It tests whether an agent can turn a short functional brief into a defensible power chain — sizing, selecting, and laying out a charger, a power path, and a 5 V output stage — and whether it can substantiate a 2 A output claim with real datasheet, magnetics, and thermal evidence instead of asserting it. Because the brief names no parts and no mechanics, it equally tests whether the agent keeps its own choices visible as choices rather than smuggling them in as requirements.

This repository is one of thirty-two. The suite, the protocol and the results
live in [PCBA_AutoDesignAndTest_Bench](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench).

## Repository layout

| Path | Contents |
|---|---|
| `BRIEF.md` | the supplied brief — authoritative, preserved byte for byte, never edited |
| `board/requirements.md` | what the brief fixes, what it leaves open, and where decisions get recorded |
| `board/requirements.json` | the same split, machine-readable, each fixed requirement bound to brief text |
| `board/manifest.template.json` | the toolkit's minimum manifest, pre-filled for this board |
| `board/toolchain.json` | where this board's build finds KiCad and the router |
| `benchmark/metadata.json` | the supplied catalogue entry — category, difficulty, detail, stressors |
| `docs/architecture.md` | the decisions this board must make, as questions, unanswered |
| `docs/sources.md` | the classes of evidence the design will have to cite |
| `docs/status.md` | what exists, what does not, and what is deliberately absent |
| `candidates/` | disposable search output, ignored by Git |
| `.claude/skills/` | the accountability-review skill [CLAUDE.md](CLAUDE.md) requires before a push |
| `tooling/PCBA_AutoDesignAndTest` | the shared verification/routing/release toolkit, as a pinned submodule |

## Getting the repository

The toolkit is a submodule and carries KiCad Routing Tools as a submodule of its
own, so clone recursively:

```bash
git clone --recursive https://github.com/pentolope/PCBA_LiIon_PowerBank.git
```

```bash
git submodule update --init --recursive
```

## Designing the board

Generic verification, routing and release logic is **not** written here. It is
consumed from `tooling/PCBA_AutoDesignAndTest`, which is board-agnostic by
construction and must stay that way; this repository owns the board and nothing
else. Start from
[the toolkit's onboarding guide](tooling/PCBA_AutoDesignAndTest/examples/onboarding.md),
and see [CLAUDE.md](CLAUDE.md) for the rules a design run works under.

```bash
python3 tooling/PCBA_AutoDesignAndTest/run.py preflight
```

## Brief integrity

`BRIEF.md` SHA-256 `a83c2729b4cd3572342d1c0d042245c18bb77970d150b0bb1acddd78cdec8627`

Every quotation in `board/requirements.json` is bound to those exact bytes. If
the brief ever changes, the bindings are stale by construction — which is the
point of recording the digest.
