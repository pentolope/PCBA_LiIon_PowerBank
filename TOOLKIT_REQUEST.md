# Toolkit requests from 07_PCBA_LiIon_PowerBank

What the board-agnostic toolkit (`PCBA_AutoDesignAndTest`, including the
vendored `KiCadRoutingTools`) would have had to provide for this board not to
have solved the same problem in its own `design/` directory. Each entry says
what was hit, what it cost, and what the toolkit could own instead.

Maintained while the board is being designed; newest sections appended.

---

## 1. The routed-copper tidy pass belongs to the toolkit

`design/route.py` on this board carries ~450 lines of post-router copper
repair, and boards 03 and 04 carry near-identical copies. None of it is about
this board: it is about what a search-based router leaves behind.

The passes, all board-agnostic:

- snap a track end standing inside a via's annulus onto that via's centre;
- pull a track end that stopped inside a same-net pad's outline onto the
  pad's anchor;
- drop tracks a snap collapsed to a point;
- fold a fragment shorter than the fabrication floor into its single
  neighbour;
- restore a declared track width or via size the search narrowed;
- drop copper drawn twice;
- move a via off a solder-mask opening;
- carry a track end that stops inside a pour on to a pad the pour reaches;
- cut a track where another ends part way along it (or pull that end onto the
  corner when the cut would leave a sliver);
- prune vias that carry nothing and track ends that hold nothing, to a
  fixpoint, because each pass leaves work for the others.

Every one of those exists because a *toolkit gate* rejects the board
otherwise. The board should not be the place where the gate is answered.

## 2. pcbnew binding hazards the toolkit should wrap

These cost the most debugging time on this board, and none of them is
discoverable from the API surface.

- **`BOARD.GetConnectivity()` intermittently returns an unwrapped
  `SwigPyObject`** with no methods on it. It is not reproducible in a tight
  loop; it appeared after several minutes of work on one board and killed a
  nine-attempt routing run outright. A toolkit `unconnected(board)` that
  rebuilds and retries would make every caller safe.
- **`PCB_TRACK.GetStart()` / `GetEnd()` return an alias to the track's own
  corner**, while `PCB_VIA.GetPosition()` returns a copy. Code that reads an
  endpoint, moves the track, decides the move was wrong and writes the
  endpoint back silently does nothing, because the value it kept followed the
  move. This produced a clearance violation that survived three rounds of
  "the check says it should have been rejected". A toolkit `endpoints(track)`
  returning copies removes the whole class.
- **`board.Remove(item)` hands the item to Python**; letting it be collected
  leaves the board unable to answer `board.Tracks()` at all (it starts
  returning an unwrapped object, `TypeError: 'SwigPyObject' object is not
  iterable`). A toolkit `detach(board, item)` that retains the item for the
  board's lifetime would prevent it.

## 3. Connectivity has to be asked against a current fill

Every "may this copper go?" decision is a connectivity question, and
`BuildConnectivity()` answers it from the fill polygons stored in the file.
A board that arrives from a router carries the fill from *before* the router's
copper, which shows pads joined through metal the next refill removes. Pruning
against that stale fill removes real copper and leaves dangling ends and
unconnected zones that only appear at release time.

A toolkit helper that refills before answering - or simply documents that
connectivity is only as good as the stored fill - would have saved a full
diagnose-and-rerun cycle.

## 4. A clearance oracle, not just a DRC run

The repair passes above all move copper, and each one needs to answer "does
this move still meet the board's own rules?" without paying for a `kicad-cli`
DRC run per candidate. This board grew a sampled slack function (segment to
pad box, segment to segment, hole to hole) plus the rule that a move is
allowed when what it leaves has room to spare *or* is no tighter than what it
replaced - the second half matters because a sampled distance is not the
checker's own, and a legitimate route between two pads on 0.5 mm pitch reads
as tight either way.

That is a toolkit-shaped object: `slack(board, shapes, rules)`.

## 5. Let a routing candidate be judged by the gates that will judge the release

This was the single largest cost on this board.

`run.py validate` runs the gates. The routing loop can only run `kicad-cli
pcb drc`, so it accepts a candidate the gates then reject:

- `ROUTE.GEOMETRY_HYGIENE` - duplicate segments, dangling ends (KiCad's own
  DRC does not report either the way this gate does);
- `ROUTE.TINY_SEGMENTS` - 0.025-0.035 mm chamfer fragments the router emits;
- `VIA.ANNULUS_MASK_OVERLAP`, `VIA.IN_PAD_CONTACT`,
  `VIA.MASK_CLEARANCE_TARGET` - vias on solder-mask openings.

Each discovery cost a full route -> build -> validate cycle (tens of minutes),
and the fix then had to be reproduced inside the board's own tidy pass. If the
toolkit exposed those gates as a library call over a board file - something
like `gates.evaluate(board_path, manifest, only=("ROUTE.*", "VIA.*"))` - a
routing candidate could be accepted or rejected on the spot, and the whole
class of "the release rejects what routing accepted" would disappear.

## 6. Router (KiCadRoutingTools) findings

- **`--same-net-pad-clearance` is not honoured by every via the run places.**
  With `0.3` on the command line the search still placed a layer-transition
  via centred inside a same-net SMD pad (an inductor land) and another
  overlapping a capacitor's mask opening. The flag appears to reach the
  reconcile step but not the plane-finalize taps.
- **A pour is only repaired when its net is in `--nets`.** Routing signals
  with the plane nets withheld leaves the plane cut into islands and the
  board reports the zone against itself as unconnected. This is stated in a
  docstring in the middle of `route.py`; it should be enforced by the wrapper
  (zone-owning nets always in scope) rather than left to each caller.
- **The search emits fragments far below any fabrication floor** - chamfer
  pieces of 0.025 mm on a board whose declared floor is 0.1 mm. The floor is
  already passed to the router as a fab override; it should apply to what the
  router emits, not only to what it checks.
- **The router writes its own project file beside the candidate**, so a DRC
  run over the raw router output is judged against rules the design never
  declared (538 violations against the router's project, 0 against the
  design's). Any tooling that reads router output has to know to bring its own
  project; that is worth a helper.

## 7. Gate measurements should say how they count

`CONTRACT.CONNECTOR` compares `required_positions` and `required_rows`
against, respectively, the number of **distinct pad numbers** on the
footprint and `min(distinct x, distinct y)` over one representative pad per
number. For a USB-C receptacle that makes "positions" 17 (16 contacts plus one
shell terminal, whose four lands share a number) and "rows" 2 (the contact row
and the shell row). Neither number is on any datasheet, and the failure
message - `expected 11, measured 17` - does not say what was counted, so the
first attempt at the contract used the netlist's pin map and failed.

Either the gate's finding should state the counting rule, or the manifest
schema should carry it beside the field.

## 8. The fab catalogue already knows the process limits the via gates want

`VIA.MASK_CLEARANCE_PROCESS` and `VIA.NATIVE_GERBER_AGREEMENT` sit at
`NOT_APPLICABLE` unless the manifest declares `via_mask.process.limit_mm`.
The toolkit selected the process (`fab/selection.json`) and holds the
capability document, so it is in a better position than the board to state
that limit. As it stands both gates are off on every board I can see, which
is the opposite of what the evidence discipline wants.

## 9. Checking a board outside its project tree is unreliable

Copying a candidate `.kicad_pcb` to a scratch directory and running
`kicad-cli pcb drc` on it produces nine spurious `lib_footprint_issues`
warnings, because `fp-lib-table` is not beside it. Working out which findings
were real cost time on every iteration. A toolkit helper that stages a board
with its library tables and project file - `staged(board_path) -> path` -
would make candidate checking trustworthy.

## 10. "Which nets are still unconnected?" needs an API

Deciding what to hand the router requires knowing which nets the placed board
still leaves open. The only route to that is `kicad-cli pcb drc --format json`
followed by a regex over `unconnected_items[].items[].description` for
`[NET_NAME]`. The obvious pcbnew paths are closed:
`CONNECTIVITY_DATA.GetRatsnestForNet()` returns an unwrapped object, and
`RunOnUnconnectedEdges` has no Python director, so a callback is a
`TypeError`. A toolkit `open_nets(board_path) -> set[str]` would be small and
would be used by every board that routes.

---

## 11. `min_segment_mm` is stated twice and only checked once

The fabrication floor for a piece of copper lives in the manifest
(`routing.min_segment_mm`) where the gate reads it, and again in whatever the
board uses to clean up after the router. On this board they are now one
declaration, but nothing in the toolkit makes that true: a board can pass the
router a floor of 0.1 mm, clean up to 0.05 mm, and only find out at release.
The floor should reach the router and the repair pass from the manifest.

## 12. The repair passes need each other, and the toolkit knows that better than a board does

Running each repair pass once is wrong in a way that is only visible on a
real board: folding a fragment moves an end onto another track's body, which
needs a cut; a cut can leave a piece below the floor, which needs a fold;
pruning a stub leaves the via that held it carrying nothing. This board ended
up running six passes to a bounded fixpoint, and each of the three rounds of
"one finding left" cost a full route -> build -> validate cycle to discover.

A toolkit that owns the passes owns the fixpoint too, including the decision
that it is bounded rather than proven to settle.

## 13. `run.py validate` is the only way to ask a gate a question

There is no way to ask "would this board pass `ROUTE.TINY_SEGMENTS`?" without
running `build` and then `validate` over the whole tree - which regenerates
gerbers, drill files, BOM, CPL and the archive first. On this board that is
several minutes per question, and the answer to each one changed a single
line of a repair pass. `--only=` narrows which gates *report*, but the build
still has to have happened.

A read-only `validate --no-build --only=ROUTE.*` (or the library call in
section 5) would turn a multi-minute cycle into a second.

## 14. A routing loop must put the board back on *any* exit, not just a clean one

The loop installs each candidate to measure it, so the tree holds failing
copper for as long as the measurement takes, and restores the placed board
when no candidate is accepted. When a binding fault (section 2) raised out of
the sixth attempt, that restore never ran and the tree was left carrying a
rejected candidate - which then silently became the input to the next thing
that read the board. The restore belongs in a `finally`, and the loop belongs
to the toolkit rather than to each board.

## 15. Small things that would have saved a step each

- `MIN_SEGMENT_MM`, `VIA_MASK_CLEARANCE_MM` and the router's own floors are
  three different statements of the same kind of fact. The manifest is the
  natural home; the board should read them from it, not restate them.
- `run.py build` prints `source closure: <digest>` but nothing says what the
  digest covers, so it cannot be used to tell "the board changed" from "the
  evidence changed".
- The gerber/drill export flags live in the manifest as an opaque list
  (`artifacts.gerber_export_flags`). A board that gets one wrong finds out
  from a fabricator, not from a gate.
