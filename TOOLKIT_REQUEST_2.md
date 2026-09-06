# Toolkit requests from 07_PCBA_LiIon_PowerBank - second pass

Checked against toolkit `c17ebb5` (Phase 3, reviewed) on 2026-09-05.
`TOOLKIT_REQUEST.md` holds the first pass, written while the board was being
designed; this file continues it and does not repeat it.

The board still builds and validates against this toolkit unchanged -
`ACCEPTED`, 30 PASS / 27 NOT_APPLICABLE / 0 FAIL, policy state
`fabrication-ready`, 49/49 board tests, `check-board` OK. Nothing here is a
regression in the board.

**Request 19 is a blocking toolkit defect** found while trying to adopt one of
the new gates: it fails a correct board, and it will fail every board on this
bench that carries a USB-C receptacle. The rest are gaps the newer toolkit
made visible.

## What the toolkit has since answered

Recorded so these do not get re-reported. Each was a numbered request in
`TOOLKIT_REQUEST.md`; the numbering below continues that file's.

- **1, 12, 14** - the post-router repair, its fixpoint and its restore-on-any-exit
  now belong to `run.py route` with declared `routing.transforms`. This board
  deleted its own ~450-line loop in `bde8e95`.
- **2** - `pcbqa.board` now publishes `endpoints()`, `unconnected()` and
  `detach`-shaped access, so the three pcbnew hazards are wrapped rather than
  rediscovered.
- **5** - `run.py route --check` and `--replay` judge a candidate through the
  current transforms without re-searching, and `check-board` answers the
  integrity questions in under a second.
- **8** - `via_mask.process.limit_from_catalog` exists, and the committed
  JLCPCB snapshot carries the facts to cite. This board adopted it, passed
  `VIA.MASK_CLEARANCE_PROCESS` on the first run, and then had to revert the
  whole declaration because the same key enables a second gate that is
  broken - see request 19.
- **9** - staging a tree with its library tables is now the toolkit's job:
  `PROV.DERIVED_DOCUMENTS` regenerates "against a staged tree with its own
  target hidden".
- **10** - `pcbqa.board.open_nets()` and `open_nets_from()` replace the regex
  over DRC JSON.

Still open from the first pass: **13** (asking one gate a question still
requires a full `build` first; `check-board` covers integrity, not gates) and
**7** (`CONTRACT.CONNECTOR` still does not state its counting rule in the
finding, though this board no longer trips it).

## 16. An omission's stated reason can be overtaken and nothing notices

`run.py claims` reports 20 stated omissions, all `[unstaged]`, under
"completed stages: none declared". Two of them read, in the board's own
words, that board copper "is not included; **it has not been laid out yet**"
- `charger_input_above_undervoltage_lockout` and
`port_voltage_above_source_minimum`.

The board has been laid out. It routed, it passed `ROUTE.*`, `DRC.*` and
`STACK.GERBER_PARITY`, and the copper those omissions excuse themselves from
now exists in the tree the same command just validated. The omission text is
false, and the closure machinery cannot say so, because closure is keyed on a
board *declaring* a completed stage and this board declares none.

A stage that has demonstrably completed - the gates that judge it all passed
against real copper - should be able to close, or at least flag, an omission
whose reason names that stage as not yet done. As it stands the honest thing
the report could say is exactly the thing it cannot.

Both omissions have now been rewritten by hand: the copper is still not in
the subtraction, so the omission stands, but it stands because no extraction
has been run over copper that exists, not because the board is unrouted. That
correction was made because a human asked the question, which is the point -
nothing in the toolkit would have raised it, and the same sentence had
survived every build, validate and release-check since the board was routed.

## 17. A decline should record the toolkit state it was made against

This board declines five Phase 3 domains (`ad9ed0a`), and the reasons are
still true: `ampacity.py` states plainly that it owns the model form and no
coefficients, so declaring `current.paths` really does mean authoring a
capacity basis with its own standard, edition and validity window.

But nothing binds the decline to that fact. If the toolkit later published a
citable basis the way it now publishes the plated barrel and the mask limits,
this board's reason - "putting an unsourced curve behind a several-amp
conductor is exactly what this toolkit refuses" - would quietly become wrong,
and no command would notice. A decline that cited the toolkit digest it was
reasoned against could be re-opened by the toolkit that invalidated it.

## 18. `ROUTE.ANGLE_STYLE` has no way to declare free-angle routing

107 of this board's 683 segments sit off the 0/45/90/135 grid, at bearings
like 2.6, 11.3 and 26.6 degrees. That is not a defect: it is what the declared
search router emits, and the copper passes every geometric gate. But
`routing.permitted_turn_degrees` takes a list of permitted angles, so the only
truthful options are to enumerate 79 observed bearings - which asserts
nothing - or to stay `NOT_APPLICABLE`, which is indistinguishable from never
having considered the question.

A style enumeration wants a `free` (or `any`) member, so a board that routes
at arbitrary angles can say so on the record.

## 19. `VIA.NATIVE_GERBER_AGREEMENT` cannot pass a connector whose shell is one numbered pad on several lands

**This is the one blocking defect found this pass, and it is in the toolkit,
not in any board.**

I adopted `via_mask.process.limit_from_catalog`, citing
`soldermask_opening_to_trace_mm` - "Keep at least 0.09 mm clearance between
soldermask openings and neighboring traces", which is exactly this board's
`annulus_to_opening_mm` metric. `VIA.MASK_CLEARANCE_PROCESS` passed on the
spot: *all 127 vias clear 0.09 mm*. But the same manifest key also enables
`VIA.NATIVE_GERBER_AGREEMENT`, and that gate failed with 59 findings, so the
opt-in had to be reverted whole. The two gates share one enabling key, and
there is no way to take the one that works.

Every one of the 59 findings is the same issue - "nearest mask opening is a
different object" - and every one names `J1.SH` (43) or `J2.SH` (16), the
USB-C receptacles' shell terminals. Nothing else disagreed: across all 127
vias there was not one finding on coordinate, drill, annulus diameter, signed
clearance, contact, positive overlap, centre inside, target class or process
class. The exported gerbers agree with the native board everywhere the gate
actually measures geometry.

The cause is in `g_export_parity._native_opening_polygon`, which builds its
lookup as `table[side][entry["label"]]`. A USB-C receptacle's shell is four
separate pad objects that all carry the number `SH`, so all four write to one
dict key and three are silently dropped. The native side is then left with a
single opening for a four-land terminal, at a fixed centroid, while the export
enumerates all four and picks the genuinely nearest one.

Two things make this unambiguous rather than a judgement call:

- all 43 `J1.SH` findings report the **same** `native_centroid`
  `(42.68, -83.55)`. They cover 38 distinct vias spread up to **32.26 mm**
  apart, and no correct nearest-opening computation can return one answer for
  all of them;
- where they differ, the export is the one that is right. For the via at
  `(42.5076, 89.3623)` the native side names an opening **5.81 mm** away
  while the export names one **1.64 mm** away (centre to centre; the gate's
  own metric is annulus-to-polygon, but the ordering is what matters here).

So the gate reports a confident FAIL against a board whose export is correct,
and it will do so for every board on this bench that carries a USB-C
receptacle. Keying that table by pad label loses the distinction the gate
depends on; it needs the pad *objects*, and the comparison needs to run
against the nearest of them rather than against whichever one survived the
dict.

### Reproduction

The defect is at `pcbqa/gates/g_export_parity.py:310`, inside
`_native_opening_polygon` (line 302):

```python
table.setdefault(side, {})[entry["label"]] = entry["mask"][side]
```

`entry["label"]` is the pad label, so the four `J1.SH` pad objects collapse to
one entry and the last one written wins. That the shell really is four
separate pad objects, not one pad with four primitives, is checkable directly:

```python
import pcbnew
board = pcbnew.LoadBoard("liion_power_bank.kicad_pcb")
j1 = next(f for f in board.Footprints() if f.GetReference() == "J1")
[(p.GetPosition().x / 1e6, p.GetPosition().y / 1e6)
 for p in j1.Pads() if p.GetNumber() == "SH"]
# [(51.32, 87.73), (51.32, 83.55), (42.68, 87.73), (42.68, 83.55)]
```

To reproduce the failure, add to `board/manifest.json` a `catalog` block
pinning `normalized_sha256` to the value already in `fab/selection.json`, and
a `via_mask.process` block carrying
`{"limit_from_catalog": {"from_catalog": "soldermask_opening_to_trace_mm"}}`,
then:

```
python run.py build  <board>/board/manifest.json
python run.py validate <board>/board/manifest.json
```

`VIA.MASK_CLEARANCE_PROCESS` passes; `VIA.NATIVE_GERBER_AGREEMENT` fails with
59 findings, of which the first two are verbatim:

```json
{"via": "via[GND]@42.5076,89.3623", "side": "front",
 "issue": "nearest mask opening is a different object",
 "native_pad": "J1.SH", "native_centroid": [42.68, -83.55],
 "export_centroid": [42.68, -87.73], "export_tie_set": [[42.68, -87.73]]}
{"via": "via[GND]@60.0,68.45", "side": "back",
 "issue": "nearest mask opening is a different object",
 "native_pad": "J1.SH", "native_centroid": [42.68, -83.55],
 "export_centroid": [51.32, -83.55], "export_tie_set": [[51.32, -83.55]]}
```

Note the second via is 27.3 mm from the first and still gets the same
`native_centroid`.

Until that is fixed this board cannot cite its process limit at all, which is
the part that stings: the citation machinery from request 8 works, and the
evidence it would have added - a digest-pinned published limit standing behind
a 0.15 mm design target - is real and is now unavailable for an unrelated
reason.

## 19a. A citation should have to say which feature it describes

Separately, and still worth fixing: the neighbouring fact
`filled_via_to_opening_mm` is **0.35 mm** and would have failed this board
outright, and nothing in the citation form would have caught it: the two facts
sit in the same `soldermask-process` category with near-identical names, and
`from_catalog` takes a bare string. What rules it out is buried in its own
`conditions` - it applies to vias *filled with soldermask* and no wider than
0.5 mm, and this board's vias are tented at 0.6 and 0.8 mm. I had to read
both entries and the board's `(tenting)` block to know which one I was
entitled to cite, and the manifest can only record that reasoning as prose in
`interpretation`, where no gate reads it.

A citation should have to state which of the board's own features it
describes, and the toolkit should check that claim against the board, or two
adjacent facts will eventually be swapped silently and the gate will report a
confident PASS against the wrong limit.

For the record, the reverted declaration is kept in this board's history so it
can be restored unchanged once request 19 is fixed; it needed a `catalog`
pin read from `fab/selection.json`, a `via_mask.process` block naming the
citation, and the two gates added to `mandatory_gates`.

## 20. `placement.edge_clearance` wants a requirement, and a board may not have one

`placement.edge_clearance` requires `min_mm` and `basis`.
Measuring this board gives 0.102 mm courtyard-to-edge at H4, but a
*measurement is not a requirement*: declaring it would freeze whatever the
placer happened to produce as though an assembler had asked for it. The gate
wants a number the board can source, and this board has none, so it stays
`NOT_APPLICABLE` - which reads identically to never having asked. A gate whose
input is a requirement the board genuinely lacks should be declinable with a
reason, the way a domain is.
