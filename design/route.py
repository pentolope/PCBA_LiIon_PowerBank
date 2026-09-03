"""Routing: the search draws ordinary connectivity, nothing else.

Several nets are withheld from it. The reference is a pour with a via at
every surface pad, and which pad reaches it is a property of the net rather
than of a search. The converter's switch node and each protection package's
own drain are generated copper whose shape is a requirement. What is left is
signal connectivity and the probe stubs, and that is what the router is for.

A candidate is judged, not trusted: it is adopted, the board is measured, and
if it does not come back clean the placed board is restored so no failing
copper stays in the tree.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys

import pcbnew

from . import build, layout, netlist

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tooling", "PCBA_AutoDesignAndTest"))

from pcbqa import routing_record  # noqa: E402

REPO_ROOT = layout.REPO_ROOT
CANDIDATE_ROOT = os.path.join(REPO_ROOT, "candidates")
CANDIDATE_NAME = "route-current"
PROVENANCE_PATH = os.path.join(REPO_ROOT, "generated", "routing.json")

#: Nets the search may not draw, and the copper that already carries them.
#: The reference is a pour every surface pad is stitched to; the switch node
#: and each protection package's drain are generated copper whose shape the
#: design states rather than searches for.
RESERVED_NETS = (netlist.SYSTEM_GROUND_NET, "SW") + tuple(
    "PROT_D%d" % index
    for index in range(3, 3 + netlist.PROTECTION_PACKAGES))


def _open_nets(placed_pcb):
    """The nets the placed board still leaves unconnected.

    A net whose copper the placement already completed - poured, or carried
    by generated track - has nothing for the router to add. Asking for it
    anyway invites a second path beside copper that is already joined, and
    the router cannot see that it is already joined because it does not
    model a zone fill. The set is read back from the placed board rather
    than declared, so it cannot describe a placement that has changed.
    """
    report = os.path.join(CANDIDATE_ROOT, "placed-drc.json")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    completed = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--output", report, "--format", "json",
         "--severity-error", placed_pcb],
        capture_output=True, text=True)
    if completed.returncode != 0 and not os.path.isfile(report):
        raise RuntimeError("DRC did not run over the placed board: "
                           + completed.stderr[-2000:])
    with open(report, encoding="utf-8") as handle:
        document = json.load(handle)
    names = set()
    for entry in document.get("unconnected_items") or []:
        for item in entry.get("items") or []:
            found = re.search(r"\[([^\]]+)\]", item.get("description", ""))
            if found is not None:
                names.add(found.group(1))
    return names


def routed_nets(placed_pcb):
    """The nets the search is asked for.

    Every net the placed board still leaves unconnected, and every net the
    placement poured. A poured net is offered even when the placement
    already joined it, because the search repairs a pour its own copper cut
    in two - and it only does that for a pour whose net is in scope.
    """
    wanted = _open_nets(placed_pcb) | set(layout.FRONT_POUR_NETS)
    return tuple(sorted(name for name in netlist.NETS
                        if name not in RESERVED_NETS and name in wanted))


#: The router is given a wider clearance than the rule the board is judged by.
#: It takes the figure from the project's Default net class, and its diagonal
#: segments then land short of it, so the candidate is routed against a
#: project carrying this margin and judged against the authoritative one,
#: which `_adopt` restores.
ROUTER_CLEARANCE_MM = 0.30

#: How far the search keeps a via it places from a pad of its own net. Its
#: ordinary clearance already holds a via off the pads of every other net,
#: so without this it will drop one on a pad of the net it is routing -
#: inside a mask opening the assembly's paste feeds, which wicks the joint
#: into the barrel. The figure is the board's own via-to-opening distance,
#: which is measured the same way: annulus edge to opening edge.
ROUTER_SAME_NET_PAD_CLEARANCE_MM = layout.VIA_MASK_CLEARANCE_MM

ROUTER_OPTIONS = (
    "--track-width", str(layout.TRACK_WIDTH_MM),
    "--clearance", str(ROUTER_CLEARANCE_MM),
    "--via-size", str(layout.VIA_DIAMETER_MM),
    "--via-drill", str(layout.VIA_DRILL_MM),
    "--board-edge-clearance", "0.45",
    "--hole-to-hole-clearance", "0.3",
    "--same-net-pad-clearance", str(ROUTER_SAME_NET_PAD_CLEARANCE_MM),
    "--no-power-tap-neckdown",
)

# The router is deterministic for a fixed input, so a bare retry explores
# nothing. Each attempt varies the net-ordering strategy instead, which is
# what actually produces a different candidate.
#: The search is repeated over the same orderings because the router is not
#: deterministic: the same board and the same ordering can come back with a
#: different set of vias, and a candidate carrying one sub-clearance item is
#: rejected rather than patched. Each repeat is a distinct candidate, and
#: every one of them is recorded whether it was accepted or not.
ATTEMPT_ORDERINGS = ("inside_out", "original", "mps") * 3
MAX_ATTEMPTS = len(ATTEMPT_ORDERINGS)

#: A track end is pulled onto a via's centre only when it already stands on
#: that via's own copper. A larger reach would move copper the clearance
#: check has already accepted; this one cannot, because the destination is
#: inside the annulus the end is already touching.
SNAP_WITHIN_VIA = True
#: The shortest track fragment the board accepts away from a pad or a via.
#: A router turning a diagonal lands it as a staircase of pieces far below
#: this; each one is a manufacturing risk rather than a connection, so the
#: pieces are collapsed into their neighbours.
MIN_SEGMENT_MM = layout.MIN_SEGMENT_MM
TOUCH_TOLERANCE_MM = 0.01


def _krt():
    from pcbqa import krt
    return krt


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _summary(text):
    for line in text.splitlines():
        if line.strip().startswith("JSON_SUMMARY_MIN:"):
            return json.loads(line.split("JSON_SUMMARY_MIN:", 1)[1])
    return {}


def _write_routing_project(path):
    """The project the router sees: the design's, with the clearance margin."""
    document = build.project_document(
        str(build.schematic._uuid("sheet", netlist.PROJECT_NAME)))
    document["board"]["design_settings"]["rules"]["min_clearance"] = \
        ROUTER_CLEARANCE_MM
    for entry in document["net_settings"]["classes"]:
        if entry["name"] == "Default":
            entry["clearance"] = ROUTER_CLEARANCE_MM
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    return path


#: The router carries its own fab-capability floor and is free to escalate
#: below the nominal clearance to fit tight geometry, recording the tighter
#: value so the board is graded against it. This board is graded against its
#: own declared constraints instead, so the router is given those constraints
#: as its floor: copper it emits is then legal by the same rule the checker
#: applies, rather than legal only against a floor the router lowered.
def _write_fab_floor(path):
    floors = (("clearance", build.DESIGN_RULES["min_clearance"]),
              ("track_width", build.DESIGN_RULES["min_track_width"]),
              ("via_diameter", layout.VIA_DIAMETER_MM),
              ("via_drill", layout.VIA_DRILL_MM),
              ("hole_to_hole", build.DESIGN_RULES["min_hole_to_hole"]),
              ("board_edge", build.DESIGN_RULES["min_copper_edge_clearance"]))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# generated from the board's declared constraints\n")
        for key, value in floors:
            handle.write("%s = %s\n" % (key, value))
    return path


def _route_once(resolved, candidate, attempt, placed_pcb):
    stage_dir = os.path.join(candidate, "attempt-%02d" % attempt)
    os.makedirs(stage_dir, exist_ok=True)
    source_pcb = os.path.join(stage_dir, "source.kicad_pcb")
    shutil.copy(placed_pcb, source_pcb)
    _write_routing_project(os.path.join(stage_dir, "source.kicad_pro"))
    routed_pcb = os.path.join(stage_dir, "routed.kicad_pcb")
    floor = _write_fab_floor(os.path.join(stage_dir, "fab-floor.txt"))
    command = [sys.executable,
               os.path.join(resolved["path"], "py_router", "route.py"),
               source_pcb, "--output", routed_pcb, "--nets"] \
        + list(routed_nets(placed_pcb)) + list(ROUTER_OPTIONS) \
        + ["--fab-overrides", floor,
           "--ordering", ATTEMPT_ORDERINGS[attempt - 1]]
    completed = subprocess.run(command, capture_output=True, text=True)
    summary = _summary(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError("routing failed: rc=%s summary=%s stderr=%s"
                           % (completed.returncode, summary,
                              completed.stderr[-2000:]))
    tidied_pcb = os.path.join(stage_dir, "tidied.kicad_pcb")
    shutil.copy(routed_pcb, tidied_pcb)
    transform = tidy(tidied_pcb, _existing_vias(source_pcb))
    return {
        "attempt": attempt,
        "source_sha256": digest(source_pcb),
        "accepted": False,
        "stages": [
            {"stage": "routed", "produced_by": "router",
             "sha256": digest(routed_pcb)},
            {"stage": "tidied", "produced_by": "transform",
             "sha256": digest(tidied_pcb),
             "transform": "refill the pours so every judgement below is made "
                          "against the copper that will be fabricated rather "
                          "than the fill the search inherited; "
                          "snap a track end standing on a same-net via onto that via's centre; "
                          "pull a track end that stopped inside a same-net "
                          "pad's outline onto that pad's anchor, and only "
                          "where the track still stands clear afterwards; "
                          "drop tracks the snap collapsed to a point; "
                          "fold a fragment shorter than the floor into the "
                          "single neighbour it meets away from a pad or a "
                          "via, and only where the neighbour that follows "
                          "the fold still stands clear of everything else; "
                          "restore the declared width on any track and the "
                          "declared size on any via the search narrowed "
                          "below them; drop copper drawn twice, keeping the "
                          "wider of the pair; move a via that stands on a "
                          "solder-mask opening to the nearest position that "
                          "clears every opening, carrying the ends that met "
                          "it; carry an end that stops inside a pour on to a "
                          "pad the pour's own copper reaches; cut a track "
                          "where another ends part way along it, so the "
                          "junction is an end on both, or pull that end "
                          "onto the corner where the cut would leave a "
                          "sliver; drop any via the search left that "
                          "carries nothing, and prune dangling track ends, "
                          "keeping any removal only while connectivity is "
                          "unchanged and repeating all three until none "
                          "finds anything, because each leaves work for the "
                          "others; refill the zones so the pours are "
                          "knocked out around the copper the router added",
             "effects": transform,
             "parameters": {"snap_within_via_annulus": SNAP_WITHIN_VIA,
                            "touch_tolerance_mm": TOUCH_TOLERANCE_MM}},
        ],
        "context": {"router_summary": summary,
                    "ordering": ATTEMPT_ORDERINGS[attempt - 1]},
        "board": tidied_pcb,
    }


def _vias_on_openings(path):
    """How many vias stand on a pad's solder-mask opening."""
    board = pcbnew.LoadBoard(path)
    openings = layout._mask_openings(board)
    keep_out = pcbnew.FromMM(layout.VIA_MASK_CLEARANCE_MM)
    found = 0
    for item in board.GetTracks():
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        centre = item.GetPosition()
        radius = item.GetWidth(pcbnew.F_Cu) / 2.0
        if any(layout._box_distance(centre, box) - radius < keep_out
               for box in openings):
            found += 1
    return found


def measure(path):
    """What the board says about itself: violations, and what is still open."""
    report = os.path.join(CANDIDATE_ROOT, CANDIDATE_NAME, "adopted-drc.json")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    completed = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--output", report, "--format", "json",
         "--severity-error", "--severity-warning", path],
        capture_output=True, text=True)
    if completed.returncode != 0 and not os.path.isfile(report):
        raise RuntimeError("DRC did not run: " + completed.stderr[-2000:])
    with open(report, encoding="utf-8") as handle:
        document = json.load(handle)
    counted = document.get("violations") or []
    return {
        "errors": sum(1 for entry in counted
                      if entry.get("severity") == "error"),
        "warnings": sum(1 for entry in counted
                        if entry.get("severity") != "error"),
        "unconnected": len(document.get("unconnected_items") or []),
        "schematic_parity": len(document.get("schematic_parity") or []),
        "vias_on_mask_openings": _vias_on_openings(path),
    }


def _accepts(metrics):
    """What a candidate has to be before it replaces the board in the tree.

    Everything the board's own severities call a finding, because the gate
    that judges the routed board counts warnings too: a candidate that leaves
    one is a candidate the release would reject.
    """
    return (metrics["errors"] == 0 and metrics["warnings"] == 0
            and metrics["unconnected"] == 0
            and metrics["schematic_parity"] == 0
            and metrics["vias_on_mask_openings"] == 0)


def _write_record(placed_pcb, attempts, accepted, krt, resolved):
    record = {
        "kind": routing_record.KIND,
        "source_sha256": digest(placed_pcb),
        "attempts": attempts,
        "accepted_attempt": accepted["attempt"] if accepted else None,
        "adopted_sha256": (digest(layout.BOARD_PATH) if accepted else None),
        "context": {
            "router": krt.provenance(resolved["path"], sys.executable),
            "resolution": resolved,
            "routed_nets": list(routed_nets(placed_pcb)),
            "reserved_nets": list(RESERVED_NETS),
            "net_selection": "the search is given the nets the placed board "
                             "still reports unconnected and the nets the "
                             "placement poured, less the reserved ones; a "
                             "pour is repaired only by a run whose scope "
                             "covers its net, and a net that is neither open "
                             "nor poured has nothing for the search to add",
            "options": list(ROUTER_OPTIONS),
            "acceptance": "a candidate is adopted only when a fresh DRC over "
                          "the adopted board reports no violation, nothing "
                          "unconnected and no disagreement with the "
                          "schematic, and no via on the board stands within "
                          "%.2f mm of a pad's solder-mask opening"
                          % layout.VIA_MASK_CLEARANCE_MM,
            "reproducibility": "the router is not bit-reproducible; "
                               "candidates are generated until one is "
                               "accepted and every attempt is recorded here",
        },
    }
    routing_record.validate(record)
    os.makedirs(os.path.dirname(PROVENANCE_PATH), exist_ok=True)
    with open(PROVENANCE_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return record


def _adopt(candidate_board):
    """Install a candidate, then rewrite everything derived from the board.

    The router writes its own project file beside the candidate - loosening a
    track width, pinning an edge clearance, silencing severities - so the
    authoritative project is regenerated from the design source rather than
    inherited from whatever the search left behind.
    """
    shutil.copy(candidate_board, layout.BOARD_PATH)
    build.write_project()


def run():
    krt = _krt()
    resolved = krt.resolve()
    candidate = os.path.join(CANDIDATE_ROOT, CANDIDATE_NAME)
    shutil.rmtree(candidate, ignore_errors=True)
    os.makedirs(candidate, exist_ok=True)
    layout.write()
    placed_pcb = os.path.join(candidate, "placed.kicad_pcb")
    shutil.copy(layout.BOARD_PATH, placed_pcb)

    attempts = []
    accepted = None
    # A candidate is installed to be measured, so the tree carries failing
    # copper for as long as the measurement takes. Whatever ends the loop -
    # a rejection, or the search itself failing - the placed board goes back
    # unless a candidate earned its place.
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = _route_once(resolved, candidate, attempt, placed_pcb)
            entry = {key: value
                     for key, value in result.items() if key != "board"}
            _adopt(result["board"])
            metrics = measure(layout.BOARD_PATH)
            entry["context"]["adopted_metrics"] = metrics
            entry["accepted"] = _accepts(metrics)
            _write_record(placed_pcb, attempts + [entry],
                          entry if entry["accepted"] else None, krt, resolved)
            attempts.append(entry)
            if entry["accepted"]:
                accepted = entry
                break
    finally:
        if accepted is None:
            _adopt(placed_pcb)

    if accepted is None:
        _write_record(placed_pcb, attempts, None, krt, resolved)
        raise RuntimeError(
            "no routing candidate was accepted in %d attempts; the placed, "
            "unrouted board has been restored so no failing copper stays in "
            "the tree" % MAX_ATTEMPTS)
    return layout.BOARD_PATH, PROVENANCE_PATH


def _endpoints(track):
    """Where a track begins and ends, as points of their own.

    The bindings hand back the track's own corner rather than a copy of it,
    so a point read here and kept across a move would follow the move and
    could not be moved back. These do not.
    """
    return (pcbnew.VECTOR2I(track.GetStart().x, track.GetStart().y),
            pcbnew.VECTOR2I(track.GetEnd().x, track.GetEnd().y))


def _supported(point, track, board, vias, tracks, epsilon):
    """True when something the connectivity anchors to holds the point up.

    A via, a pad, or another track's own end. Standing inside another
    track's copper is not enough: the checker asks whether a connected item
    has an anchor at the point, so an end that stops part way along another
    track, or overshoots the end of one, reads as bare however much copper
    it is sitting in.
    """
    for via in vias:
        if via.GetNetCode() != track.GetNetCode():
            continue
        if not via.IsOnLayer(track.GetLayer()):
            continue
        centre = via.GetPosition()
        if math.hypot(point.x - centre.x, point.y - centre.y) <= epsilon:
            return True
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetCode() != track.GetNetCode():
                continue
            # A pad only holds a track end up on a layer it is actually on:
            # an SMD pad on the far side is not a connection, and treating it
            # as one used to leave the end dangling for the checker to find.
            if not pad.IsOnLayer(track.GetLayer()):
                continue
            if pad.HitTest(point, 0):
                return True
    for other in tracks:
        if other.m_Uuid.AsString() == track.m_Uuid.AsString():
            continue
        if other.GetNetCode() != track.GetNetCode():
            continue
        if other.Type() == pcbnew.PCB_VIA_T:
            continue
        if other.GetLayer() != track.GetLayer():
            continue
        for anchor in _endpoints(other):
            if math.hypot(point.x - anchor.x, point.y - anchor.y) <= epsilon:
                return True
    return False


def _on_body(point, segment, epsilon):
    """Where along a straight track the point falls, or None.

    The distance is measured to the centre line rather than to the copper,
    because the split this answers for has to land on the line the two
    halves will share. Ends do not count: a point already at one is a
    junction, not a place to cut.
    """
    start, end = segment.GetStart(), segment.GetEnd()
    dx, dy = float(end.x - start.x), float(end.y - start.y)
    length = math.hypot(dx, dy)
    if length <= epsilon:
        return None
    along = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length
    if along <= epsilon or along >= length - epsilon:
        return None
    across = abs((point.x - start.x) * dy - (point.y - start.y) * dx) / length
    return along if across <= epsilon else None


def _segment_gap(first_start, first_end, second_start, second_end):
    """The closest approach of two segments, sampled from both ends.

    Exact where neither crosses the other, which is the only case that has
    to be told apart: a crossing is a short and is caught by the check that
    reads the board back, not by a distance.
    """
    return min(
        layout._segment_distance(first_start, second_start, second_end),
        layout._segment_distance(first_end, second_start, second_end),
        layout._segment_distance(second_start, first_start, first_end),
        layout._segment_distance(second_end, first_start, first_end))


def _foreign_copper(board, net_code, ignored):
    """Everything on another net that the board's own rules keep copper off.

    Each entry is what it is, where it is and how wide, so a distance can be
    taken from it without asking the board again for every candidate.
    """
    pads, segments, vias = [], [], []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetCode() == net_code:
                continue
            box = pad.GetBoundingBox()
            drill = pad.GetDrillSize()
            pads.append(((box.GetLeft(), box.GetTop(),
                          box.GetRight(), box.GetBottom()),
                         pad.GetPosition(),
                         max(drill.x, drill.y) / 2.0,
                         pad.GetLayerSet()))
    for item in board.GetTracks():
        if item.m_Uuid.AsString() in ignored:
            continue
        if item.Type() == pcbnew.PCB_VIA_T:
            vias.append((item.GetPosition(),
                         item.GetWidth(pcbnew.F_Cu) / 2.0,
                         item.GetDrill() / 2.0,
                         item.GetNetCode()))
            continue
        if item.GetNetCode() == net_code:
            continue
        segments.append((item.GetStart(), item.GetEnd(),
                         item.GetWidth() / 2.0, item.GetLayer()))
    return pads, segments, vias


def _slack(shapes, copper, net_code, clearance, hole_clearance,
           hole_to_hole):
    """How much room the shapes have to spare, at their tightest point.

    A shape is a via - a centre, its annulus and its hole, on every layer -
    or a piece of track on one layer. Vias of the shape's own net still
    count for hole to hole, because two holes that near each other are one
    hole to the drill however they are wired. The figure is a distance
    sampled along each shape rather than the exact one the checker takes,
    so it is used to compare a move against where it started rather than
    to declare a board clear.
    """
    pads, segments, vias = copper
    worst = None

    def note(value):
        return value if worst is None else min(worst, value)

    for shape in shapes:
        kind, layer, start, end, half, hole = shape
        for box, centre, pad_hole, layers in pads:
            if kind == "track" and not layers.Contains(layer):
                continue
            worst = note(layout._segment_box_distance(start, end, box)
                         - half - clearance)
            if pad_hole > 0:
                gap = layout._segment_distance(centre, start, end)
                worst = note(gap - half - hole_clearance)
                if hole > 0:
                    worst = note(gap - hole - pad_hole - hole_to_hole)
        for other_start, other_end, other_half, other_layer in segments:
            if kind == "track" and other_layer != layer:
                continue
            worst = note(_segment_gap(start, end, other_start, other_end)
                         - half - other_half - clearance)
        for centre, radius, other_hole, other_net in vias:
            gap = layout._segment_distance(centre, start, end)
            if other_net != net_code:
                worst = note(gap - half - radius - clearance)
            if hole > 0:
                worst = note(gap - hole - other_hole - hole_to_hole)
    return 0.0 if worst is None else worst


def _stands_clear(shapes, copper, net_code, clearance, hole_clearance,
                  hole_to_hole):
    """True when every shape keeps the board's own distances from copper."""
    return _slack(shapes, copper, net_code, clearance, hole_clearance,
                  hole_to_hole) >= 0


def _track_slack(board, track, ignored=()):
    """How much room the track has to spare where it now is."""
    return _slack(
        [("track", track.GetLayer(), track.GetStart(), track.GetEnd(),
          track.GetWidth() / 2.0, 0.0)],
        _foreign_copper(board, track.GetNetCode(),
                        set(ignored) | {track.m_Uuid.AsString()}),
        track.GetNetCode(),
        pcbnew.FromMM(build.DESIGN_RULES["min_clearance"]),
        pcbnew.FromMM(build.DESIGN_RULES["min_hole_clearance"]),
        pcbnew.FromMM(build.DESIGN_RULES["min_hole_to_hole"]))


def _no_worse(before, after):
    """Whether a move may stand.

    A move is allowed when what it leaves has room to spare, and where the
    copper was already tight - the sampled distance is not the checker's
    own, and a route between two pads on half-millimetre pitch reads as
    tight either way - when it is no tighter than it was. That way the
    measure never blocks a move that improves nothing and breaks nothing.
    """
    return after >= 0 or after >= before


def _covered(point, pours, pad, layer, margin):
    """True when a disc of the given radius at the point is on the pour.

    The pad counts as well: a pour connected through thermal spokes leaves
    the metal right at the pad to the pad itself, and the copper being
    carried has to be allowed to arrive.
    """
    offsets = ((0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin))
    for dx, dy in offsets:
        probe = pcbnew.VECTOR2I(int(point.x + dx), int(point.y + dy))
        if pad is not None and pad.HitTest(probe, 0):
            continue
        if any(pour.GetFilledPolysList(layer).Contains(probe)
               for pour in pours):
            continue
        return False
    return True


def _carry(board, track, point, pours, width, step, epsilon, validate):
    """A segment from a bare end to the nearest pad the pour already reaches.

    Nearest first, and only where every point along the way - and the width
    the segment is drawn at - stands on copper the pour is already filling,
    so the segment adds no metal anywhere the pour was not.
    """
    layer = track.GetLayer()
    candidates = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetCode() != track.GetNetCode():
                continue
            if not pad.IsOnLayer(layer):
                continue
            anchor = pad.GetPosition()
            distance = math.hypot(anchor.x - point.x, anchor.y - point.y)
            if distance <= epsilon:
                continue
            candidates.append((distance, anchor.x, anchor.y, pad))
    margin = width / 2
    for distance, x, y, pad in sorted(candidates,
                                      key=lambda entry: entry[:3]):
        anchor = pcbnew.VECTOR2I(int(x), int(y))
        steps = max(int(distance / step), 1)
        walk = [pcbnew.VECTOR2I(
            int(point.x + (anchor.x - point.x) * index / steps),
            int(point.y + (anchor.y - point.y) * index / steps))
            for index in range(steps + 1)]
        if not all(_covered(place, pours, pad, layer, margin)
                   for place in walk):
            continue
        if not validate(layer, pcbnew.VECTOR2I(int(point.x), int(point.y)),
                        anchor, width / 2):
            continue
        segment = pcbnew.PCB_TRACK(board)
        segment.SetStart(pcbnew.VECTOR2I(int(point.x), int(point.y)))
        segment.SetEnd(anchor)
        segment.SetWidth(int(width))
        segment.SetLayer(layer)
        segment.SetNetCode(track.GetNetCode())
        return segment
    return None


def _entry_geometry(track, board, vias):
    """True when an end of the track sits on a via or in a pad: copper that
    short is how a route enters one, not a route in its own right."""
    for point in _endpoints(track):
        for via in vias:
            centre = via.GetPosition()
            if math.hypot(point.x - centre.x, point.y - centre.y) \
                    <= via.GetWidth(pcbnew.F_Cu) / 2:
                return True
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.IsOnLayer(track.GetLayer()) and pad.HitTest(point, 0):
                    return True
    return False


def _absorption(fragment, board, vias, tracks, epsilon):
    """The one neighbour a fragment can be folded into, or None.

    A fold is only offered where exactly one same-net track on the same layer
    meets the fragment at that end and no via or pad stands there, so a
    junction and a terminal are both left alone."""
    start, finish = _endpoints(fragment)
    for point, other in ((start, finish), (finish, start)):
        for via in vias:
            centre = via.GetPosition()
            if math.hypot(point.x - centre.x, point.y - centre.y) <= epsilon:
                break
        else:
            touching = []
            for candidate in tracks:
                if candidate.m_Uuid.AsString() == fragment.m_Uuid.AsString():
                    continue
                if candidate.GetNetCode() != fragment.GetNetCode():
                    continue
                if candidate.GetLayer() != fragment.GetLayer():
                    continue
                for get, set_ in ((candidate.GetStart, candidate.SetStart),
                                  (candidate.GetEnd, candidate.SetEnd)):
                    end = pcbnew.VECTOR2I(get().x, get().y)
                    if math.hypot(end.x - point.x, end.y - point.y) <= epsilon:
                        touching.append((candidate, set_, end))
            if len(touching) == 1:
                candidate, set_, end = touching[0]
                return (fragment, candidate, set_, end, other)
    return None


def _existing_vias(path):
    """Where the placed board already had vias.

    The stitching that bonds every surface reference pad to its pour is drawn
    before routing, so those vias are the design's rather than the search's,
    and the pruning below must not consider them.
    """
    board = pcbnew.LoadBoard(path)
    return {(item.GetPosition().x, item.GetPosition().y)
            for item in board.GetTracks()
            if item.Type() == pcbnew.PCB_VIA_T}


def _unconnected(board):
    """How much of the board is still unjoined.

    The bindings return the connectivity through a shared pointer they do
    not always resolve to its own class, and an unresolved one carries no
    methods. Rebuilding produces a fresh pointer, so that is what is tried
    rather than reading a number off an object that cannot answer.
    """
    for _ in range(4):
        connectivity = board.GetConnectivity()
        if hasattr(connectivity, "GetUnconnectedCount"):
            return connectivity.GetUnconnectedCount(True)
        board.BuildConnectivity()
    raise RuntimeError("the connectivity the bindings returned is not a "
                       "CONNECTIVITY_DATA and rebuilding did not resolve it")


def tidy(path, protected_vias=()):
    board = pcbnew.LoadBoard(path)
    protected_vias = set(protected_vias)
    epsilon = pcbnew.FromMM(TOUCH_TOLERANCE_MM)
    # Detaching a track hands it to Python, and letting Python destroy it
    # while the board is still standing leaves the board unable to answer
    # what copper it holds. Everything taken off the board is kept here for
    # as long as the board is open, so nothing is destroyed under it.
    retired = []
    # Every judgement below asks whether removing a piece of copper would
    # leave something unjoined, and the answer is only as good as the fill
    # the question is asked against. The board arrives carrying the fill the
    # pours had before the search put copper through them, which shows pads
    # joined by copper the refill is about to take away, so the fill is
    # brought up to date first. Removing copper afterwards can only let a
    # pour grow back, so a removal this fill calls harmless stays harmless
    # once the pours are filled again at the end.
    layout.fill_zones(board)
    snapped = 0
    for _ in range(4):
        vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        moved = 0
        for track in board.GetTracks():
            if track.Type() == pcbnew.PCB_VIA_T:
                continue
            for get, set_ in ((track.GetStart, track.SetStart),
                              (track.GetEnd, track.SetEnd)):
                point = pcbnew.VECTOR2I(get().x, get().y)
                for via in vias:
                    if via.GetNetCode() != track.GetNetCode():
                        continue
                    centre = via.GetPosition()
                    distance = math.hypot(point.x - centre.x,
                                          point.y - centre.y)
                    if epsilon < distance <= via.GetWidth(pcbnew.F_Cu) / 2:
                        before = _track_slack(board, track)
                        set_(centre)
                        if not _no_worse(before, _track_slack(board, track)):
                            set_(point)
                            continue
                        moved += 1
                        break
        snapped += moved
        if not moved:
            break

    # A track end that stops inside a pad's outline but outside the shape the
    # pad actually presents - the cut corner of a rounded rectangle - reads as
    # connected to the board's connectivity and as a bare end to anything that
    # asks what copper touches it. It is pulled to the pad anchor, which is
    # the one point on a pad every reader agrees is on it.
    pad_snapped = 0
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        tracks = [t for t in board.GetTracks()
                  if t.Type() != pcbnew.PCB_VIA_T]
        for get, set_ in ((track.GetStart, track.SetStart),
                          (track.GetEnd, track.SetEnd)):
            point = pcbnew.VECTOR2I(get().x, get().y)
            if _supported(point, track, board, vias, tracks, epsilon):
                continue
            for footprint in board.GetFootprints():
                for pad in footprint.Pads():
                    if pad.GetNetCode() != track.GetNetCode():
                        continue
                    if not pad.IsOnLayer(track.GetLayer()):
                        continue
                    if not pad.GetBoundingBox().Contains(point):
                        continue
                    before = _track_slack(board, track)
                    set_(pad.GetPosition())
                    # The end can be far enough into the pad that following
                    # it takes the track - as wide as it was drawn - across
                    # ground it never covered, so a snap that would leave it
                    # tighter than it was is not made.
                    if not _no_worse(before, _track_slack(board, track)):
                        set_(point)
                        continue
                    pad_snapped += 1
                    break
                else:
                    continue
                break

    # Snapping can leave a track whose two ends became the same point. It
    # connects nothing, and DRC reports it crossing whatever it lies on, so
    # it goes before anything else is judged - and before the pruning pass,
    # which can decide to keep a track and then never look at it again.
    collapsed = 0
    while True:
        degenerate = next((track for track in board.GetTracks()
                           if track.Type() != pcbnew.PCB_VIA_T
                           and track.GetLength() == 0), None)
        if degenerate is None:
            break
        board.Remove(degenerate)
        retired.append(degenerate)
        collapsed += 1

    # The router cuts a corner with a chamfer a few tens of microns long.
    # Copper that short is below anything the fab resolves and reads as a
    # fragment rather than as a route, so each one is folded into the
    # neighbour it meets - and only where a single neighbour meets it away
    # from any pad or via, so a junction is never collapsed, and only while
    # connectivity is unchanged.
    def _absorb_fragments():
        folded = 0
        # A fragment refused once is refused for this pass only: the pass runs
        # again after the others have moved copper, and what could not be
        # folded into a chain of six pieces can often be folded once the
        # chain is two.
        keep_short = set()
        while True:
            board.BuildConnectivity()
            baseline = _unconnected(board)
            vias = [t for t in board.GetTracks()
                    if t.Type() == pcbnew.PCB_VIA_T]
            tracks = [t for t in board.GetTracks()
                      if t.Type() != pcbnew.PCB_VIA_T]
            move = None
            for track in tracks:
                if track.m_Uuid.AsString() in keep_short:
                    continue
                if track.GetLength() >= pcbnew.FromMM(MIN_SEGMENT_MM):
                    continue
                if _entry_geometry(track, board, vias):
                    continue
                move = _absorption(track, board, vias, tracks, epsilon)
                if move is not None:
                    break
                keep_short.add(track.m_Uuid.AsString())
            if move is None:
                return folded
            fragment, neighbour, setter, previous, target = move
            before = _track_slack(board, neighbour,
                                  {fragment.m_Uuid.AsString()})
            setter(target)
            board.Remove(fragment)
            retired.append(fragment)
            board.BuildConnectivity()
            # The fold moves an end, and the neighbour that follows it is as
            # wide as it was: on a conductor drawn wide for its current that
            # sweeps copper across ground the fragment never covered, so a
            # fold that would leave the neighbour tighter than it was is
            # undone.
            widened_ok = _no_worse(before, _track_slack(board, neighbour))
            if _unconnected(board) > baseline or not widened_ok:
                setter(previous)
                board.Add(fragment)
                board.BuildConnectivity()
                keep_short.add(fragment.m_Uuid.AsString())
                continue
            folded += 1

    absorbed = _absorb_fragments()

    # The search falls back to a 5 mil track where it cannot fit the width it
    # was given. That is below the floor this board declares, so it is
    # brought up to the floor - not to the net class's width, which is a
    # preference rather than a limit, and widening to it would move copper
    # the clearance check has already accepted.
    floor = pcbnew.FromMM(build.DESIGN_RULES["min_track_width"])
    widened = 0
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        if track.GetWidth() >= floor:
            continue
        track.SetWidth(floor)
        widened += 1

    # Every via the search added is the board's own via. The router narrows
    # one where it cannot fit the declared size, which produces a hole the
    # board's declared fabrication process does not offer; the declared size
    # is restored, and if that no longer fits, the clearance check that runs
    # next is what says so.
    resized = 0
    for item in board.GetTracks():
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        if item.GetWidth(pcbnew.F_Cu) >= pcbnew.FromMM(layout.VIA_DIAMETER_MM) \
                and item.GetDrill() >= pcbnew.FromMM(layout.VIA_DRILL_MM):
            continue
        item.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(layout.VIA_DIAMETER_MM))
        item.SetDrill(pcbnew.FromMM(layout.VIA_DRILL_MM))
        resized += 1

    # A via the search left with copper on only one side connects nothing and
    # is a hole the board would be drilled for anyway, so it goes - and only
    # while connectivity is unchanged, which is what tells a stub from a
    # transition the pour completes.
    def _prune_vias():
        pruned = 0
        keep_vias = set()
        while True:
            board.BuildConnectivity()
            baseline = _unconnected(board)
            victim = None
            for item in board.GetTracks():
                if item.Type() != pcbnew.PCB_VIA_T:
                    continue
                if item.m_Uuid.AsString() in keep_vias:
                    continue
                position = item.GetPosition()
                if (position.x, position.y) in protected_vias:
                    continue
                victim = item
                break
            if victim is None:
                return pruned
            uuid = victim.m_Uuid.AsString()
            board.Remove(victim)
            retired.append(victim)
            board.BuildConnectivity()
            if _unconnected(board) > baseline:
                board.Add(victim)
                board.BuildConnectivity()
                keep_vias.add(uuid)
                continue
            pruned += 1

    # Prune what the router left unattached. A track whose removal would
    # break the net is kept and skipped rather than ending the pass, because
    # one such track used to hide every dangling end behind it.
    def _prune_tracks():
        pruned = 0
        keep = set()
        while True:
            board.BuildConnectivity()
            baseline = _unconnected(board)
            vias = [t for t in board.GetTracks()
                    if t.Type() == pcbnew.PCB_VIA_T]
            tracks = [t for t in board.GetTracks()
                      if t.Type() != pcbnew.PCB_VIA_T]
            victim = None
            for track in tracks:
                if track.m_Uuid.AsString() in keep:
                    continue
                if all(_supported(point, track, board, vias, tracks, epsilon)
                       for point in _endpoints(track)):
                    continue
                victim = track
                break
            if victim is None:
                return pruned
            uuid = victim.m_Uuid.AsString()
            board.Remove(victim)
            retired.append(victim)
            board.BuildConnectivity()
            if _unconnected(board) > baseline:
                board.Add(victim)
                board.BuildConnectivity()
                keep.add(uuid)
                continue
            pruned += 1

    # Copper drawn twice is one conductor to look at and two fragments to
    # anything reading the board back, and the narrower of the pair also
    # states a width the wider one contradicts. The search draws over the
    # generated copper it was given, so the duplicate goes and the wider is
    # what stays.
    duplicates = 0
    while True:
        segments = [item for item in board.GetTracks()
                    if item.Type() != pcbnew.PCB_VIA_T]
        victim = None
        for index, first in enumerate(segments):
            ends = {(first.GetStart().x, first.GetStart().y),
                    (first.GetEnd().x, first.GetEnd().y)}
            for second in segments[index + 1:]:
                if second.GetNetCode() != first.GetNetCode():
                    continue
                if second.GetLayer() != first.GetLayer():
                    continue
                if {(second.GetStart().x, second.GetStart().y),
                        (second.GetEnd().x, second.GetEnd().y)} != ends:
                    continue
                victim = (first if first.GetWidth() <= second.GetWidth()
                          else second)
                break
            if victim is not None:
                break
        if victim is None:
            break
        board.Remove(victim)
        retired.append(victim)
        duplicates += 1

    # A track that stops inside a pour is held up by copper the connectivity
    # reaches through the fill and no reader anchors to, so the board
    # reports a bare end where there is metal on every side. The end is
    # carried on to a pad of its own net that the pour's own copper reaches
    # in a straight line, which adds no copper the pour was not already
    # filling and gives the end something to hold on to.
    def _carry_into_pours():
        carried = 0
        width = pcbnew.FromMM(build.DESIGN_RULES["min_track_width"])
        clearance = pcbnew.FromMM(build.DESIGN_RULES["min_clearance"])
        hole_clearance = pcbnew.FromMM(
            build.DESIGN_RULES["min_hole_clearance"])
        hole_to_hole = pcbnew.FromMM(build.DESIGN_RULES["min_hole_to_hole"])
        step = pcbnew.FromMM(0.05)
        while True:
            segments = [item for item in board.GetTracks()
                        if item.Type() != pcbnew.PCB_VIA_T]
            vias = [item for item in board.GetTracks()
                    if item.Type() == pcbnew.PCB_VIA_T]
            made = None
            for track in segments:
                for point in _endpoints(track):
                    if _supported(point, track, board, vias, segments,
                                  epsilon):
                        continue
                    pours = [zone for zone in board.Zones()
                             if zone.GetNetCode() == track.GetNetCode()
                             and zone.IsOnLayer(track.GetLayer())
                             and zone.GetFilledPolysList(
                                 track.GetLayer()).Contains(point)]
                    if not pours:
                        continue
                    def _fits(layer, start, end, half, track=track):
                        return _stands_clear(
                            [("track", layer, start, end, half, 0.0)],
                            _foreign_copper(board, track.GetNetCode(),
                                            set()),
                            track.GetNetCode(), clearance, hole_clearance,
                            hole_to_hole)

                    made = _carry(board, track, point, pours, width, step,
                                  epsilon, _fits)
                    if made is not None:
                        break
                if made is not None:
                    break
            if made is None:
                return carried
            board.Add(made)
            carried += 1

    # A via the search dropped inside a pad's solder-mask opening cannot be
    # tented, and where the opening is one a paste aperture feeds it wicks
    # the joint's solder into the barrel. The search will place one on a pad
    # of the net it is routing, so each is moved to the nearest position
    # that clears every opening, carrying the ends of whatever met it.
    stuck = set()

    def _lift_vias_off_openings():
        lifted = 0
        openings = layout._mask_openings(board)
        keep_out = pcbnew.FromMM(layout.VIA_MASK_CLEARANCE_MM)
        clearance = pcbnew.FromMM(build.DESIGN_RULES["min_clearance"])
        hole_clearance = pcbnew.FromMM(
            build.DESIGN_RULES["min_hole_clearance"])
        hole_to_hole = pcbnew.FromMM(build.DESIGN_RULES["min_hole_to_hole"])
        step = pcbnew.FromMM(0.05)
        while True:
            board.BuildConnectivity()
            baseline = _unconnected(board)
            move = None
            for item in board.GetTracks():
                if item.Type() != pcbnew.PCB_VIA_T:
                    continue
                centre = item.GetPosition()
                if (centre.x, centre.y) in protected_vias:
                    continue
                if item.m_Uuid.AsString() in stuck:
                    continue
                radius = item.GetWidth(pcbnew.F_Cu) / 2.0
                if all(layout._box_distance(centre, box) - radius >= keep_out
                       for box in openings):
                    continue
                move = (item, centre, radius)
                break
            if move is None:
                return lifted
            item, centre, radius = move
            attached = [(track, index)
                        for track in board.GetTracks()
                        if track.Type() != pcbnew.PCB_VIA_T
                        for index, end in enumerate(_endpoints(track))
                        if math.hypot(end.x - centre.x,
                                      end.y - centre.y) <= epsilon]
            ignored = {item.m_Uuid.AsString()} \
                | {track.m_Uuid.AsString() for track, _ in attached}
            copper = _foreign_copper(board, item.GetNetCode(), ignored)
            hole = item.GetDrill() / 2.0
            standing = [("via", None, centre, centre, radius, hole)]
            for track, _index in attached:
                start, finish = _endpoints(track)
                standing.append(("track", track.GetLayer(), start, finish,
                                 track.GetWidth() / 2.0, 0.0))
            before = _slack(standing, copper, item.GetNetCode(), clearance,
                            hole_clearance, hole_to_hole)
            placed = False
            for reach in range(1, 31):
                for turn in range(32):
                    theta = 2.0 * math.pi * turn / 32
                    target = pcbnew.VECTOR2I(
                        int(centre.x + reach * step * math.cos(theta)),
                        int(centre.y + reach * step * math.sin(theta)))
                    if not all(layout._box_distance(target, box) - radius
                               >= keep_out for box in openings):
                        continue
                    shapes = [("via", None, target, target, radius, hole)]
                    for track, index in attached:
                        ends = list(_endpoints(track))
                        ends[index] = target
                        shapes.append(("track", track.GetLayer(),
                                       ends[0], ends[1],
                                       track.GetWidth() / 2.0, 0.0))
                    if not _no_worse(before,
                                     _slack(shapes, copper,
                                            item.GetNetCode(), clearance,
                                            hole_clearance, hole_to_hole)):
                        continue
                    item.SetPosition(target)
                    for track, index in attached:
                        (track.SetStart if index == 0
                         else track.SetEnd)(target)
                    board.BuildConnectivity()
                    if _unconnected(board) <= baseline:
                        placed = True
                        break
                    item.SetPosition(centre)
                    for track, index in attached:
                        (track.SetStart if index == 0
                         else track.SetEnd)(centre)
                if placed:
                    break
            if not placed:
                # Nowhere near it clears an opening. The via stays where the
                # search put it and the candidate carries the finding: what
                # measures the adopted board refuses it, and the next
                # attempt routes from a different order.
                stuck.add(item.m_Uuid.AsString())
                continue
            board.BuildConnectivity()
            lifted += 1

    # A route that joins another part way along it leaves an end the copper
    # covers and the connectivity does not anchor, which the board reports
    # as a bare end. The track being joined is cut at the junction so both
    # halves end there, which leaves the same copper and gives the junction
    # the anchor it was missing.
    refused = set()

    def _split_tees():
        split = 0
        floor = pcbnew.FromMM(MIN_SEGMENT_MM)
        while True:
            tracks = [item for item in board.GetTracks()
                      if item.Type() == pcbnew.PCB_TRACE_T]
            vias = [item for item in board.GetTracks()
                    if item.Type() == pcbnew.PCB_VIA_T]
            action = None
            for track in tracks:
                for index, point in enumerate(_endpoints(track)):
                    if (track.m_Uuid.AsString(), index) in refused:
                        continue
                    if _supported(point, track, board, vias, tracks, epsilon):
                        continue
                    for host in tracks:
                        if host.m_Uuid.AsString() == track.m_Uuid.AsString():
                            continue
                        if host.GetNetCode() != track.GetNetCode():
                            continue
                        if host.GetLayer() != track.GetLayer():
                            continue
                        along = _on_body(point, host, epsilon)
                        if along is None:
                            continue
                        # Cutting within a fragment's length of the host's
                        # own end would leave a piece too short to be
                        # copper; that near, the end belongs on the corner
                        # rather than beside it.
                        length = math.hypot(
                            float(host.GetEnd().x - host.GetStart().x),
                            float(host.GetEnd().y - host.GetStart().y))
                        if along < floor:
                            action = ("snap", track, index,
                                      _endpoints(host)[0])
                        elif length - along < floor:
                            action = ("snap", track, index,
                                      _endpoints(host)[1])
                        else:
                            action = ("cut", host,
                                      pcbnew.VECTOR2I(point.x, point.y))
                        break
                    if action is not None:
                        break
                if action is not None:
                    break
            if action is None:
                return split
            if action[0] == "snap":
                _kind, track, index, corner = action
                setter = track.SetStart if index == 0 else track.SetEnd
                start, finish = _endpoints(track)
                before = _track_slack(board, track)
                setter(corner)
                if not _no_worse(before, _track_slack(board, track)):
                    setter(start if index == 0 else finish)
                    refused.add((track.m_Uuid.AsString(), index))
                    continue
                split += 1
                continue
            _kind, host, point = action
            piece = pcbnew.PCB_TRACK(board)
            piece.SetStart(point)
            piece.SetEnd(host.GetEnd())
            piece.SetWidth(host.GetWidth())
            piece.SetLayer(host.GetLayer())
            piece.SetNetCode(host.GetNetCode())
            board.Add(piece)
            host.SetEnd(point)
            split += 1

    # Each pass leaves work for the others: a via is load-bearing while it
    # holds a stub up, a track is left hanging by the via it ended on, and
    # what is left of a pruned route can end on another track's body. Asking
    # each once leaves whichever ran first with copper it would now take
    # away, so all three are asked until none finds anything.
    vias_removed = 0
    removed = 0
    tees_split = 0
    carried = 0
    lifted = 0
    # Bounded because a fold and a cut can hand each other work: a fold moves
    # an end onto a track's body and a cut makes an end of it, and there is
    # no proof the pair settles. What the board is judged on is what the
    # rounds leave, not that they ran to exhaustion.
    for _round in range(12):
        refused.clear()
        folded = _absorb_fragments()
        raised = _lift_vias_off_openings()
        split = _split_tees()
        joined = _carry_into_pours()
        pruned_vias = _prune_vias()
        pruned_tracks = _prune_tracks()
        absorbed += folded
        lifted += raised
        tees_split += split
        carried += joined
        vias_removed += pruned_vias
        removed += pruned_tracks
        if not folded and not raised and not split and not joined \
                and not pruned_vias and not pruned_tracks:
            break

    # The router adds copper the pours were not knocked out around, so the
    # fill is recomputed here rather than left describing earlier copper.
    layout.fill_zones(board)
    pcbnew.SaveBoard(path, board)
    return {"endpoints_snapped": snapped,
            "fragments_absorbed": absorbed,
            "endpoints_snapped_to_pads": pad_snapped,
            "collapsed_tracks_removed": collapsed,
            "narrow_tracks_widened": widened,
            "undersized_vias_restored": resized,
            "dangling_tracks_removed": removed,
            "junctions_resolved": tees_split,
            "duplicate_segments_removed": duplicates,
            "vias_lifted_off_mask_openings": lifted,
            "vias_left_on_mask_openings": len(stuck),
            "ends_carried_into_pours": carried,
            "unneeded_vias_removed": vias_removed,
            "zones_refilled": len(list(board.Zones()))}


if __name__ == "__main__":
    for path in run():
        sys.stdout.write(path + "\n")
