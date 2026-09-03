"""The board: outline, placement, pours and silkscreen, from the design
source.

Board coordinates run x right and y UP from the lower-left corner, which is
the frame every dimension in this module is stated in. KiCad's own y runs
down, so the mapping is applied once, here.

The arrangement follows the current. Both receptacles sit on the bottom edge
because that is the face the brief puts the user's connections on, and the
button and the indicators sit in the band immediately above them, on the same
face. The cell connector is on the opposite edge, behind a keepout the cell
and its leads occupy, so nothing the user touches is near the cell.

Between the two runs the power chain, left to right: the receptacle, the
damper, the switch the advertisement gates, the converter, and the enable
switch that feeds the output receptacle. The converter's own loop - its
switch pin, the inductor, the cell rail capacitance and its ground pad - is
the one structure placed for area rather than for order, because it is the
only loop on the board whose geometry is a requirement.
"""
from __future__ import annotations

import json
import math
import os
import sys

from . import ksym, netlist

_TOOLKIT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tooling", "PCBA_AutoDesignAndTest")
if _TOOLKIT not in sys.path:
    sys.path.insert(0, _TOOLKIT)

from pcbqa import headless  # noqa: E402

headless.suppress_blocking_ui()

import pcbnew  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_PATH = os.path.join(REPO_ROOT, netlist.PROJECT_NAME + ".kicad_pcb")
PLACEMENT_PATH = os.path.join(REPO_ROOT, "constraints", "placement.json")

FOOTPRINT_SEARCH_PATHS = (
    os.path.join(REPO_ROOT, "library"),
    "/usr/share/kicad/footprints",
)

ORIGIN_MM = (30.0, 90.0)

BOARD_W_MM = 70.0
BOARD_H_MM = 45.0

#: The receptacles' mating faces stand on the board edge, so their courtyards
#: reach exactly to y = 0 and a plug meets the board where the board ends.
RECEPTACLE_FACE_OFFSET_MM = 5.4
INPUT_RECEPTACLE_X_MM = 17.0
OUTPUT_RECEPTACLE_X_MM = 53.0

#: The region the cell and its leads occupy. Nothing is placed inside it and
#: the silkscreen marks it, because the cell is the one part of this assembly
#: the board does not carry.
CELL_KEEPOUT_MM = (61.0, 25.0, 69.5, 37.0)

EDGE_WIDTH_MM = 0.1
TRACK_WIDTH_MM = 0.25
#: Width of the generated copper that carries cell-side current. Wider than
#: the requirement asks for, because these are the conductors that carry the
#: whole cell current and there is room for them.
POWER_TRACK_WIDTH_MM = 2.0
CLEARANCE_MM = 0.15
EDGE_CLEARANCE_MM = 0.3
VIA_DIAMETER_MM = 0.6
VIA_DRILL_MM = 0.3
POWER_VIA_DIAMETER_MM = 0.8
POWER_VIA_DRILL_MM = 0.4
ZONE_INSET_MM = 0.5
#: The shortest piece of copper the board accepts away from a pad or a via.
#: A fragment below this is what a search leaves where it turns a corner,
#: not a route, and the board is judged against it as well as routed to it.
MIN_SEGMENT_MM = 0.1

#: How far a via's annulus is kept from any pad's solder-mask opening. A via
#: that touches an opening cannot be tented or plugged, and one that reaches
#: an opening a paste aperture feeds wicks the joint's solder into its
#: barrel. The board is drawn with no mask expansion, so an opening is the
#: pad's own outline and this is a distance the placement can search against.
VIA_MASK_CLEARANCE_MM = 0.15

STITCH_TRACK_WIDTH_MM = 0.4
STITCH_GAP_MM = 0.35

MOUNTING_HOLES_MM = {
    "H1": (3.5, 3.5),
    "H2": (66.5, 3.5),
    "H3": (3.5, 41.5),
    "H4": (66.5, 41.5),
}

#: The band the cell's own conductors run in, and the region the cell body
#: occupies. Nothing is placed inside it.


#: Parts a placement search may not move, and why.
#:
#: The receptacles, the cell connector, the button, the indicators and the
#: fasteners are the board's mechanical contract with the person holding it.
#: The test points are its service contract. The inductor, the converter and
#: the cell-rail capacitance are the switching loop, whose area is a
#: requirement rather than a result.
LOCKED_REFERENCES = tuple(sorted(
    ["J1", "J2", "J3", "SW1", "H1", "H2", "H3", "H4",
     "U1", "L1", "C7", "C8"]
    + ["D%d" % index for index in range(1, 6)]
    + ["TP%d" % index for index in range(1, 12)]))


#: Every part's pose, as (x, y, rotation) in the board frame.
#:
#: The bands the parts fall into are the bands the power nets occupy, because
#: each of those nets is poured and two pours that overlap are two nets
#: wanting the same copper. Left to right along the board: the input and what
#: reads it, the charger input, the converter, the inductor and the cell
#: rail, the cell's own protection, and the output. The one place two power
#: nets are unavoidably adjacent is at a device's own pins, and there the
#: copper is generated as a neck rather than poured.
SEED_PLACEMENT = {
    # --- the face the user meets: the two receptacles on the edge, and the
    # button and the indicators in the gap between them ------------------
    "J1": (INPUT_RECEPTACLE_X_MM, RECEPTACLE_FACE_OFFSET_MM, 180.0),
    "J2": (OUTPUT_RECEPTACLE_X_MM, RECEPTACLE_FACE_OFFSET_MM, 180.0),
    "SW1": (28.0, 6.0, 0.0),
    "D1": (34.5, 6.0, 0.0),
    "D2": (38.0, 6.0, 0.0),
    "D3": (41.5, 6.0, 0.0),
    "D4": (45.0, 6.0, 0.0),
    "D5": (34.5, 9.5, 0.0),

    # --- what the input receptacle's own conductors meet ------------------
    "D7": (10.5, 11.0, 0.0),
    "R1": (10.5, 13.5, 0.0),
    "D8": (23.5, 11.0, 0.0),
    "R2": (23.5, 13.5, 0.0),
    "TP1": (10.5, 16.0, 0.0),
    "TP2": (7.0, 16.0, 0.0),
    "TP6": (7.0, 13.5, 0.0),

    # --- the damper, the clamp and the switch the advertisement gates -----
    "C4": (9.5, 19.5, 0.0),
    "R3": (13.5, 19.5, 0.0),
    "D6": (17.0, 19.5, 0.0),
    "Q1": (20.5, 19.5, 0.0),

    # --- the detector ----------------------------------------------------
    "U3": (9.0, 24.5, 0.0),
    "C1": (14.0, 23.0, 0.0),
    "U4": (14.0, 26.5, 0.0),
    "C2": (18.0, 26.5, 0.0),
    "R4": (18.0, 23.0, 0.0),
    "R5": (9.0, 29.5, 0.0),
    "R6": (13.0, 29.5, 0.0),
    "C3": (17.0, 29.5, 0.0),
    "R7": (5.0, 29.5, 0.0),
    "R8": (5.0, 33.0, 0.0),
    "Q2": (9.0, 33.0, 0.0),
    "R9": (13.0, 33.0, 0.0),

    # --- the charger input -----------------------------------------------
    "C5": (25.5, 20.0, 90.0),
    "C6": (25.5, 27.5, 90.0),
    "TP3": (21.0, 23.0, 0.0),

    # --- the converter, its inductor and the capacitance behind each ------
    "U1": (29.0, 24.5, 0.0),
    "L1": (41.0, 24.5, 270.0),
    "C10": (22.5, 32.0, 90.0),
    "C11": (27.0, 32.0, 90.0),
    "C12": (31.5, 32.0, 90.0),
    "C13": (36.0, 32.0, 90.0),
    "C7": (48.0, 20.0, 0.0),
    "C8": (48.0, 24.0, 0.0),
    "R10": (52.0, 20.0, 0.0),
    "C9": (52.0, 24.0, 0.0),
    "TP7": (18.5, 32.0, 0.0),
    "TP10": (52.0, 26.5, 0.0),

    # --- the push button's network ----------------------------------------
    "R11": (30.0, 13.0, 0.0),
    "C14": (33.5, 13.0, 0.0),
    "R12": (56.0, 24.0, 0.0),

    # --- the cell, its connector and its protection ----------------------
    "J3": (63.0, 31.0, 0.0),
    "TP4": (48.0, 26.5, 0.0),
    "TP5": (62.0, 41.0, 0.0),
    "R18": (56.0, 20.0, 0.0),
    "U2": (50.0, 33.0, 0.0),
    "C17": (50.0, 37.0, 0.0),
    "R19": (50.0, 41.0, 0.0),
    "Q3": (56.5, 33.0, 0.0),
    "Q4": (56.5, 37.0, 0.0),
    "Q5": (56.5, 41.0, 0.0),

    # --- the output enable latch and the output receptacle ---------------
    "D9": (53.0, 12.5, 0.0),
    "D10": (44.0, 12.5, 0.0),
    "D11": (58.0, 12.5, 0.0),
    "R20": (44.0, 15.0, 0.0),
    "R21": (58.0, 15.0, 0.0),
    "Q6": (40.5, 32.0, 0.0),
    "TP8": (37.0, 12.5, 0.0),
    "TP9": (37.0, 15.5, 0.0),
    "TP11": (66.0, 8.5, 0.0),
    "Q7": (62.0, 12.0, 0.0),
    "Q8": (60.5, 22.0, 0.0),
    "R13": (62.0, 15.5, 0.0),
    "R14": (66.0, 15.5, 0.0),
    "C15": (62.0, 19.0, 0.0),
    "R15": (66.0, 19.0, 0.0),
    "R16": (40.5, 28.5, 0.0),
    "R17": (41.5, 35.5, 0.0),
    "C16": (37.5, 35.5, 0.0),
}
for _reference, (_x, _y) in MOUNTING_HOLES_MM.items():
    SEED_PLACEMENT[_reference] = (_x, _y, 0.0)


# ---------------------------------------------------------------------------
# pours

#: The ground pour on the back layer: everything except the band the cell's
#: own negative conductor occupies, which is a separate net.
GROUND_POUR_MM = (ZONE_INSET_MM, ZONE_INSET_MM,
                  BOARD_W_MM - ZONE_INSET_MM, BOARD_H_MM - ZONE_INSET_MM)

#: Nets poured on the front layer, and the margin each pour reaches beyond
#: the pads it has to join. Each is a net whose own current is large enough
#: that a track would have to be wide, and the pour is what makes it wide
#: without anybody choosing a number. The box is derived from where the pads
#: actually are, so a pour cannot describe a placement that has changed.
FRONT_POUR_NETS = {
    "VBUS": 1.0,
    "VIN": 1.0,
    "VOUT": 1.0,
    "BAT": 1.0,
    "CELLN": 1.0,
}

#: Pads a pour must reach but must not be sized around, because they sit far
#: from the rest of the net and the pour would have to cross the board to
#: contain them. Each is instead reached by the router or by generated
#: copper, and the reason is stated with it.
POUR_EXCLUDED_PADS = {
    # the input receptacle's own supply pads, which the escape reaches
    "VBUS": ("J1.A4", "J1.A9", "J1.B4", "J1.B9", "TP1.1", "R9.1",
             "U3.8", "C1.1", "R4.1", "R5.1", "C3.2"),
    # the converter's own pins: four power nets on 1.27 mm centres, which no
    # arrangement of rectangles can hold apart. Generated necks carry them
    # out of the package and the pours pick them up there.
    "VIN": ("U1.1", "TP3.1", "Q1.3"),
    "VOUT": ("U1.8",),
    "BAT": ("U1.6", "J3.1"),
    "CELLN": ("J3.2",),
}


def to_board(x_mm, y_mm):
    return (ORIGIN_MM[0] + x_mm, ORIGIN_MM[1] - y_mm)


def _point(x_mm, y_mm):
    bx, by = to_board(x_mm, y_mm)
    return pcbnew.VECTOR2I(pcbnew.FromMM(bx), pcbnew.FromMM(by))


def accepted_placement():
    """The placement a search accepted, if one has been recorded.

    Absent, the seed below is the placement. Present, it replaces the seed
    for every part that is not locked - a locked part is locked in the board
    file and the search cannot have moved it, so accepting one from this file
    would be accepting a value that never came from a search.
    """
    if not os.path.isfile(PLACEMENT_PATH):
        return {}
    with open(PLACEMENT_PATH, encoding="utf-8") as handle:
        document = json.load(handle)
    return {reference: tuple(pose)
            for reference, pose in document["placement"].items()
            if reference not in LOCKED_REFERENCES}


def seed_placement():
    return dict(SEED_PLACEMENT)


#: How far apart two courtyards are pushed when they overlap, beyond the
#: overlap itself. Small, because the seed is meant to be close to legal and
#: this only takes up the slack.
LEGALISE_MARGIN_MM = 0.3
LEGALISE_PASSES = 400
#: Below this the two courtyards are touching at the margin rather than
#: overlapping, and pushing again would never end.
LEGALISE_EPSILON_MM = 1.0e-6


def _courtyard_offsets(part, rotation):
    """The courtyard as offsets from the part's own origin, y up.

    Not a half-extent: a receptacle's courtyard is not centred on its origin,
    and treating it as if it were puts parts inside it.
    """
    library_dir, name = _footprint_dir(part["footprint"])
    footprint = pcbnew.FootprintLoad(library_dir, name)
    footprint.SetOrientationDegrees(rotation)
    box = footprint.GetCourtyard(pcbnew.F_CrtYd).BBox()
    return (pcbnew.ToMM(box.GetLeft()), -pcbnew.ToMM(box.GetBottom()),
            pcbnew.ToMM(box.GetRight()), -pcbnew.ToMM(box.GetTop()))


def legalise(placed):
    """Push overlapping courtyards apart, holding the locked parts still.

    The seed placement states where each part belongs; this only resolves the
    overlaps that stating it by hand leaves behind, and it resolves them by
    moving the part that is free to move.
    """
    extents = {}
    for reference, (_, _, rotation) in placed.items():
        part = netlist.PARTS[reference]
        if not part["footprint"]:
            continue
        extents[reference] = _courtyard_offsets(part, rotation)
    poses = {reference: [x, y, rotation]
             for reference, (x, y, rotation) in placed.items()
             if reference in extents}
    order = sorted(poses)
    for _ in range(LEGALISE_PASSES):
        moved = False
        for index, first in enumerate(order):
            for second in order[index + 1:]:
                if first in LOCKED_REFERENCES and second in LOCKED_REFERENCES:
                    continue
                ax, ay, _ = poses[first]
                bx, by, _ = poses[second]
                ax0, ay0, ax1, ay1 = extents[first]
                bx0, by0, bx1, by1 = extents[second]
                overlap_x = min(ax + ax1, bx + bx1) \
                    - max(ax + ax0, bx + bx0) + LEGALISE_MARGIN_MM
                overlap_y = min(ay + ay1, by + by1) \
                    - max(ay + ay0, by + by0) + LEGALISE_MARGIN_MM
                if (overlap_x <= LEGALISE_EPSILON_MM
                        or overlap_y <= LEGALISE_EPSILON_MM):
                    continue
                moved = True
                if overlap_x < overlap_y:
                    axis, push = 0, overlap_x
                    direction = 1.0 if ax + (ax0 + ax1) / 2.0 \
                        >= bx + (bx0 + bx1) / 2.0 else -1.0
                else:
                    axis, push = 1, overlap_y
                    direction = 1.0 if ay + (ay0 + ay1) / 2.0 \
                        >= by + (by0 + by1) / 2.0 else -1.0
                free = [reference for reference in (first, second)
                        if reference not in LOCKED_REFERENCES]
                share = (push + LEGALISE_EPSILON_MM) / len(free)
                for reference in free:
                    sign = direction if reference == first else -direction
                    poses[reference][axis] += sign * share
        if not moved:
            break
    else:
        raise RuntimeError("courtyards could not be separated")
    return {reference: (round(pose[0], 4), round(pose[1], 4), pose[2])
            for reference, pose in poses.items()}


def fixed_placements():
    placed = seed_placement()
    for reference, pose in accepted_placement().items():
        if reference not in placed:
            raise KeyError("accepted placement names an unknown part: "
                           + reference)
        placed[reference] = pose
    missing = sorted(reference for reference, part in netlist.PARTS.items()
                     if part["footprint"] and reference not in placed)
    if missing:
        raise KeyError("no placement for " + ", ".join(missing))
    return legalise(placed)


def _footprint_dir(footprint):
    library, _, name = footprint.partition(":")
    for base in FOOTPRINT_SEARCH_PATHS:
        candidate = os.path.join(base, library + ".pretty")
        if os.path.isfile(os.path.join(candidate, name + ".kicad_mod")):
            return candidate, name
    raise FileNotFoundError(footprint)


_PIN_NAMES = {}


def _pin_name(lib_id, number):
    if lib_id not in _PIN_NAMES:
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        _PIN_NAMES[lib_id] = {
            key: pins[0].name for key, pins in library.pins(lib_id).items()}
    return _PIN_NAMES[lib_id].get(number, "")


def _floating_net(board, reference, number):
    lib_id = netlist.PARTS[reference]["lib_id"]
    name = "unconnected-(%s-%s-Pad%s)" % (
        reference, _pin_name(lib_id, number).replace("/", "{slash}"), number)
    existing = board.GetNetInfo().GetNetItem(name)
    if existing is not None and existing.GetNetCode() != 0:
        return existing
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def _load(board, reference, part, x, y, rotation, pin_net, nets):
    library_dir, name = _footprint_dir(part["footprint"])
    footprint = pcbnew.FootprintLoad(library_dir, name)
    if footprint is None:
        raise RuntimeError("could not load " + part["footprint"])
    library = part["footprint"].partition(":")[0]
    footprint.SetFPID(pcbnew.LIB_ID(library, name))
    footprint.SetPosition(_point(x, y))
    footprint.SetOrientationDegrees(rotation)
    footprint.SetReference(reference)
    footprint.SetValue(part["value"])
    footprint.Reference().SetLayer(pcbnew.F_Fab)
    footprint.Value().SetLayer(pcbnew.F_Fab)
    for key, value in (("MPN", part["mpn"]), ("LCSC", part["lcsc"]),
                       ("Manufacturer", part["manufacturer"])):
        if not value:
            continue
        footprint.SetField(key, value)
        for field in footprint.GetFields():
            if field.GetName() == key:
                field.SetLayer(pcbnew.F_Fab)
                field.SetVisible(False)
    if not part["in_bom"]:
        footprint.SetExcludedFromBOM(True)
    if reference in LOCKED_REFERENCES:
        footprint.SetLocked(True)
    for pad in footprint.Pads():
        number = pad.GetNumber()
        if not number:
            continue
        net_name = pin_net.get("%s.%s" % (reference, number))
        if net_name:
            pad.SetNet(nets[net_name])
        else:
            pad.SetNet(_floating_net(board, reference, number))
    board.Add(footprint)
    return footprint


def _nets(board):
    created = {}
    for name in sorted(netlist.NETS):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        created[name] = net
    return created


def _design_settings(board):
    board.SetCopperLayerCount(2)
    settings = board.GetDesignSettings()
    settings.m_TrackMinWidth = pcbnew.FromMM(0.15)
    settings.m_ViasMinSize = pcbnew.FromMM(0.45)
    settings.m_MinThroughDrill = pcbnew.FromMM(0.25)
    settings.m_CopperEdgeClearance = pcbnew.FromMM(EDGE_CLEARANCE_MM)
    settings.m_HoleClearance = pcbnew.FromMM(0.25)
    settings.m_HoleToHoleMin = pcbnew.FromMM(0.25)
    settings.m_ViasMinAnnularWidth = pcbnew.FromMM(0.1)
    settings.m_MinClearance = pcbnew.FromMM(CLEARANCE_MM)
    default_class = settings.m_NetSettings.GetDefaultNetclass()
    default_class.SetClearance(pcbnew.FromMM(CLEARANCE_MM))
    default_class.SetTrackWidth(pcbnew.FromMM(TRACK_WIDTH_MM))
    default_class.SetViaDiameter(pcbnew.FromMM(VIA_DIAMETER_MM))
    default_class.SetViaDrill(pcbnew.FromMM(VIA_DRILL_MM))


def _add_outline(board):
    corners = [(0.0, 0.0), (BOARD_W_MM, 0.0), (BOARD_W_MM, BOARD_H_MM),
               (0.0, BOARD_H_MM)]
    closed = corners + [corners[0]]
    for start, end in zip(closed, closed[1:]):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(_point(*start))
        shape.SetEnd(_point(*end))
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(pcbnew.FromMM(EDGE_WIDTH_MM))
        board.Add(shape)


def _rectangle_zone(board, corners, layers):
    zone = pcbnew.ZONE(board)
    layer_set = pcbnew.LSET()
    for layer in layers:
        layer_set.addLayer(layer)
    zone.SetLayerSet(layer_set)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in corners:
        bx, by = to_board(x, y)
        outline.Append(pcbnew.FromMM(bx), pcbnew.FromMM(by))
    return zone


def _pour(board, net, corners, layers, priority=0, remove_islands=False):
    zone = _rectangle_zone(board, corners, layers)
    zone.SetNet(net)
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(pcbnew.FromMM(CLEARANCE_MM))
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    if remove_islands:
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(zone)
    return zone


def _box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


#: Points a pour must reach beyond its own pads: where a generated neck
#: ends. Without these a pour could be sized around its pads and leave the
#: copper that feeds it outside.
POUR_EXTRA_POINTS = {}
for _pad_reference, _steps in ():
    pass


def _neck_endpoints():
    """Where each generated neck ends, by the net it carries."""
    endpoints = {}
    mapping = netlist.pin_to_net()
    for pad_reference, steps in GENERATED_NECKS:
        if pad_reference.startswith("__bar_"):
            name = RECEPTACLE_SUPPLY[pad_reference[len("__bar_"):]]
        else:
            name = mapping[pad_reference]
        endpoints.setdefault(name, []).append(steps[-1][:2])
    return endpoints


def front_pour_boxes(footprints):
    """Where each front pour goes, from the pads it has to join.

    A pour is the bounding box of its net's own front-side pads, grown by
    the margin the net declares and clipped to the board. Two pours that
    overlap would be two nets competing for the same copper, so that is an
    error rather than something the fill quietly resolves.
    """
    boxes = {}
    for name, margin in sorted(FRONT_POUR_NETS.items()):
        excluded = set(POUR_EXCLUDED_PADS.get(name, ()))
        points = []
        for reference, footprint in footprints.items():
            for pad in footprint.Pads():
                if pad.GetNetname() != name:
                    continue
                if "%s.%s" % (reference, pad.GetNumber()) in excluded:
                    continue
                box = pad.GetBoundingBox()
                left = pcbnew.ToMM(box.GetLeft()) - ORIGIN_MM[0]
                right = pcbnew.ToMM(box.GetRight()) - ORIGIN_MM[0]
                top = ORIGIN_MM[1] - pcbnew.ToMM(box.GetTop())
                bottom = ORIGIN_MM[1] - pcbnew.ToMM(box.GetBottom())
                points.append((left, min(top, bottom)))
                points.append((right, max(top, bottom)))
        points.extend(_neck_endpoints().get(name, ()))
        if not points:
            raise KeyError("no front pads to pour " + name)
        low = ZONE_INSET_MM
        boxes[name] = (
            max(low, min(x for x, _ in points) - margin),
            max(low, min(y for _, y in points) - margin),
            min(BOARD_W_MM - low, max(x for x, _ in points) + margin),
            min(BOARD_H_MM - low, max(y for _, y in points) + margin))
    return boxes


def _overlapping_pours(boxes):
    names = sorted(boxes)
    clashing = []
    for index, first in enumerate(names):
        ax0, ay0, ax1, ay1 = boxes[first]
        for second in names[index + 1:]:
            bx0, by0, bx1, by1 = boxes[second]
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                clashing.append((first, second))
    return clashing


def _add_pours(board, nets, footprints):
    _pour(board, nets["GND"], _box(*GROUND_POUR_MM), (pcbnew.B_Cu,))
    boxes = front_pour_boxes(footprints)
    clashing = _overlapping_pours(boxes)
    if clashing:
        raise ValueError(
            "front pours overlap, so two nets want the same copper: "
            + ", ".join("%s/%s" % pair for pair in clashing))
    for name, box in sorted(boxes.items()):
        _pour(board, nets[name], _box(*box), (pcbnew.F_Cu,), priority=1,
              remove_islands=True)


def _add_track(board, start, end, layer, net, width_mm):
    # Two pads of a receptacle can share one land, so two links the design
    # states separately can describe the same piece of copper. Drawing it
    # twice leaves the board carrying a segment on top of a segment, which
    # is a fragment to anything reading the copper back rather than the one
    # conductor it looks like, so the second is not drawn.
    for existing in board.GetTracks():
        if existing.Type() == pcbnew.PCB_VIA_T:
            continue
        if existing.GetLayer() != layer or existing.GetNet() != net:
            continue
        ends = {(existing.GetStart().x, existing.GetStart().y),
                (existing.GetEnd().x, existing.GetEnd().y)}
        if ends == {(start.x, start.y), (end.x, end.y)}:
            return existing
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start)
    track.SetEnd(end)
    track.SetLayer(layer)
    track.SetNet(net)
    track.SetWidth(pcbnew.FromMM(width_mm))
    board.Add(track)
    return track


def _add_via(board, position, net, diameter=VIA_DIAMETER_MM,
             drill=VIA_DRILL_MM):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(position)
    via.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(diameter))
    via.SetDrill(pcbnew.FromMM(drill))
    via.SetNet(net)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    return via


def _obstacles(board):
    """What a stitch has to clear: every pad and via, with its own hole.

    Each entry is a centre, the radius of its copper, the radius of its hole
    and its net. A hole is kept apart from another hole and from copper by
    its own rule, so both radii travel with the obstacle rather than being
    collapsed into one.
    """
    found = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            box = pad.GetBoundingBox()
            drill = pad.GetDrillSize()
            found.append(((box.GetLeft(), box.GetTop(),
                           box.GetRight(), box.GetBottom()),
                          pad.GetPosition(),
                          max(drill.x, drill.y) / 2.0,
                          pad.GetNetCode()))
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            centre = item.GetPosition()
            radius = item.GetWidth(pcbnew.F_Cu) / 2.0
            found.append(((centre.x - radius, centre.y - radius,
                           centre.x + radius, centre.y + radius),
                          centre, item.GetDrill() / 2.0, item.GetNetCode()))
    return found


def _mask_openings(board):
    """Every pad's solder-mask opening, as a box.

    The board is drawn with no mask expansion, so an opening is the pad's
    own outline. A via whose annulus reaches one cannot be tented or
    plugged, and one that reaches an opening a paste aperture feeds wicks
    the joint's solder into its barrel, so a via keeps clear of every
    opening rather than only of the pads it is not on the net of.
    """
    boxes = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            box = pad.GetBoundingBox()
            boxes.append((box.GetLeft(), box.GetTop(),
                          box.GetRight(), box.GetBottom()))
    return boxes


def _box_distance(point, box):
    left, top, right, bottom = box
    dx = max(left - point.x, 0.0, point.x - right)
    dy = max(top - point.y, 0.0, point.y - bottom)
    return math.hypot(dx, dy)


def _segment_box_distance(start, end, box, samples=12):
    best = None
    for index in range(samples + 1):
        share = index / float(samples)
        point = pcbnew.VECTOR2I(
            int(start.x + share * (end.x - start.x)),
            int(start.y + share * (end.y - start.y)))
        distance = _box_distance(point, box)
        if best is None or distance < best:
            best = distance
    return best


def _front_segments(board):
    """Every front-layer track already drawn, as a segment and a half-width.

    A stitch has to clear the copper this module generated as well as the
    pads: a via that lands on a neck is a short, and the neck is drawn first.
    """
    found = []
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            continue
        if item.GetLayer() != pcbnew.F_Cu:
            continue
        found.append((item.GetStart(), item.GetEnd(),
                      item.GetWidth() / 2.0, item.GetNetCode()))
    return found


def _segment_distance(point, start, end):
    dx = float(end.x - start.x)
    dy = float(end.y - start.y)
    length = dx * dx + dy * dy
    if length <= 0.0:
        return math.hypot(point.x - start.x, point.y - start.y)
    along = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length
    along = max(0.0, min(1.0, along))
    return math.hypot(point.x - (start.x + along * dx),
                      point.y - (start.y + along * dy))


#: The receptacle escape, as offsets from the receptacle's own origin. The
#: supply pads cannot leave sideways - the reference pads and the locating
#: pegs are there - and cannot leave downwards, because the board ends. So
#: each one steps inboard past its peg on a narrow neck and the two meet on a
#: bar above the shell, which is the first place the conductor can be as wide
#: as the current wants.
#:
#: The neck's width is the receptacle's own land geometry rather than a
#: choice: the corridor between the peg's hole clearance and the adjacent
#: configuration pad is what it is. What carries the current there is the
#: receptacle's contact, which its drawing rates well above what this board
#: draws.
ESCAPE_NECK_WIDTH_MM = 0.25
ESCAPE_BAR_WIDTH_MM = 1.5
SUPPLY_PAD_DX_MM = 2.45
ESCAPE_STEPS_MM = ((2.30, -3.60), (2.15, -3.05), (2.15, -1.20))
ESCAPE_BAR_DY_MM = -1.20

#: Which net each receptacle's supply pads carry, and where that net is
#: taken from the bar.
RECEPTACLE_SUPPLY = {"J1": "VBUS", "J2": "VOUT_SW"}


def _generated_necks(board, footprints, nets):
    """Draw the copper whose shape is a requirement rather than a result.

    A path named `__bar_<reference>` starts at that receptacle's escape bar
    rather than at a pad, because the bar is the first place the receptacle's
    supply is one conductor.
    """
    placed = fixed_placements()
    for pad_reference, steps in GENERATED_NECKS:
        reference, _, number = pad_reference.partition(".")
        if pad_reference.startswith("__bar_"):
            reference = pad_reference[len("__bar_"):]
            x0, y0, _ = placed[reference]
            position = _point(x0, y0 + ESCAPE_BAR_DY_MM)
            net = nets[RECEPTACLE_SUPPLY[reference]]
        else:
            pad = next(p for p in footprints[reference].Pads()
                       if p.GetNumber() == number)
            net = nets[pad.GetNetname()]
            position = pad.GetPosition()
        layer = pcbnew.F_Cu
        for step in steps:
            x, y, width = step[:3]
            want = _LAYER_NAMES[step[3]] if len(step) > 3 else pcbnew.F_Cu
            if want != layer:
                _layer_change(board, position, net, layer, want)
                layer = want
            end = _point(x, y)
            _add_track(board, position, end, layer, net, width)
            position = end


_LAYER_NAMES = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}

#: How far apart the two vias of a side change stand, and what they are.
LAYER_CHANGE_SPACING_MM = 1.2


def _layer_change(board, position, net, previous, following):
    """Carry a conductor to the other side on two vias rather than one."""
    for sign in (-1.0, 1.0):
        centre = pcbnew.VECTOR2I(
            int(position.x + pcbnew.FromMM(
                sign * LAYER_CHANGE_SPACING_MM / 2.0)),
            position.y)
        _add_via(board, centre, net, POWER_VIA_DIAMETER_MM,
                 POWER_VIA_DRILL_MM)
        for layer in (previous, following):
            _add_track(board, position, centre, layer, net,
                       POWER_VIA_DIAMETER_MM)


def _generated_pad_links(board, footprints, nets):
    """Join two pads of one package over the top of it.

    The pads are the same node inside the package, so the link is short and
    its direction is decided by where the package's other pads are, not by a
    search: it steps outside the pad row, crosses, and steps back.
    """
    for first, second in GENERATED_PAD_LINKS:
        pads = []
        for reference in (first, second):
            owner, _, number = reference.partition(".")
            pads.append(next(p for p in footprints[owner].Pads()
                             if p.GetNumber() == number))
        net = nets[pads[0].GetNetname()]
        start, end = pads[0].GetPosition(), pads[1].GetPosition()
        # step away from the package's centre, which is where the other pads
        # are
        centre = footprints[first.partition(".")[0]].GetPosition()
        offset = pcbnew.FromMM(PAD_LINK_STANDOFF_MM)
        sign = -1 if start.y < centre.y else 1
        above = [pcbnew.VECTOR2I(start.x, start.y + sign * offset),
                 pcbnew.VECTOR2I(end.x, end.y + sign * offset)]
        path = [start] + above + [end]
        for one, other in zip(path, path[1:]):
            _add_track(board, one, other, pcbnew.F_Cu, net,
                       PAD_LINK_WIDTH_MM)


def _receptacle_escapes(board, footprints, nets):
    """Take each receptacle's supply and reference pads off the connector.

    The reference pads reach the shell posts, which are plated through and
    therefore already on the pour. The supply pads climb their own necks to
    a bar, and generated copper carries the bar to the one part on that net
    that has to see the whole current.
    """
    placed = fixed_placements()
    for reference, net_name in sorted(RECEPTACLE_SUPPLY.items()):
        footprint = footprints[reference]
        if round(footprint.GetOrientationDegrees()) % 360 != 180:
            raise ValueError(
                "%s is not in the orientation the escape is drawn for"
                % reference)
        x0, y0, _ = placed[reference]
        net = nets[net_name]
        for sign in (-1.0, 1.0):
            points = [_point(x0 + sign * dx, y0 + dy)
                      for dx, dy in ESCAPE_STEPS_MM]
            pad = _pad_nearest(footprint, net_name,
                               x0 + sign * SUPPLY_PAD_DX_MM, y0 - 4.045)
            path = [pad.GetPosition()] + points
            for first, second in zip(path, path[1:]):
                _add_track(board, first, second, pcbnew.F_Cu, net,
                           ESCAPE_NECK_WIDTH_MM)
        _add_track(board,
                   _point(x0 - ESCAPE_STEPS_MM[-1][0], y0 + ESCAPE_BAR_DY_MM),
                   _point(x0 + ESCAPE_STEPS_MM[-1][0], y0 + ESCAPE_BAR_DY_MM),
                   pcbnew.F_Cu, net, ESCAPE_BAR_WIDTH_MM)
        _link_reference_pads(board, footprint, nets)


def _pad_nearest(footprint, net_name, x_mm, y_mm):
    target = _point(x_mm, y_mm)
    candidates = [pad for pad in footprint.Pads()
                  if pad.GetNetname() == net_name]
    if not candidates:
        raise KeyError("%s has no pad on %s"
                       % (footprint.GetReference(), net_name))
    return min(candidates,
               key=lambda pad: math.hypot(pad.GetPosition().x - target.x,
                                          pad.GetPosition().y - target.y))


def _link_reference_pads(board, footprint, nets):
    """Each surface reference pad to the plated shell post beside it."""
    net_name = netlist.SYSTEM_GROUND_NET
    surface, plated = [], []
    for pad in footprint.Pads():
        if pad.GetNetname() != net_name:
            continue
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            surface.append(pad)
        else:
            plated.append(pad)
    for pad in surface:
        nearest = min(plated, key=lambda other: math.hypot(
            other.GetPosition().x - pad.GetPosition().x,
            other.GetPosition().y - pad.GetPosition().y))
        _add_track(board, pad.GetPosition(), nearest.GetPosition(),
                   pcbnew.F_Cu, nets[net_name], STITCH_TRACK_WIDTH_MM)


def _stitch(board, footprint, pad, net):
    """Drop a via just outside a surface pad and bond it to its pour.

    The direction is searched rather than assumed: on a board where a passive
    row steps by little more than its own courtyard, the obvious direction is
    often occupied, and a via that lands on a neighbour's mask opening is a
    bridge, not a connection.
    """
    position = pad.GetPosition()
    size = pad.GetSize()
    angle = math.radians(footprint.GetOrientationDegrees())
    along = (math.cos(angle), math.sin(angle))
    across = (-math.sin(angle), math.cos(angle))
    half_along = pcbnew.ToMM(size.x) / 2.0
    half_across = pcbnew.ToMM(size.y) / 2.0
    obstacles = _obstacles(board)
    openings = _mask_openings(board)
    mask_clearance = pcbnew.FromMM(VIA_MASK_CLEARANCE_MM)
    segments = _front_segments(board)
    stitch_half = pcbnew.FromMM(STITCH_TRACK_WIDTH_MM / 2.0)
    clearance = pcbnew.FromMM(CLEARANCE_MM)
    via_radius = pcbnew.FromMM(VIA_DIAMETER_MM / 2.0)
    via_hole = pcbnew.FromMM(VIA_DRILL_MM / 2.0)
    hole_clearance = pcbnew.FromMM(0.25)
    # A radial search rather than a list of directions: on a board where a
    # passive row steps by little more than its own courtyard, the obvious
    # direction is often occupied, and a via that lands on a neighbour's mask
    # opening is a bridge, not a connection.
    del along, across
    reach = math.hypot(half_along, half_across) + VIA_DIAMETER_MM / 2.0 \
        + STITCH_GAP_MM
    candidates = []
    steps = 48
    for index in range(24):
        radius = reach + 0.2 * index
        for step in range(steps):
            theta = 2.0 * math.pi * step / steps
            candidates.append((radius * math.cos(theta),
                               radius * math.sin(theta)))
    for dx, dy in candidates:
        centre = pcbnew.VECTOR2I(int(position.x + pcbnew.FromMM(dx)),
                                 int(position.y + pcbnew.FromMM(dy)))
        x_mm = pcbnew.ToMM(centre.x) - ORIGIN_MM[0]
        y_mm = ORIGIN_MM[1] - pcbnew.ToMM(centre.y)
        margin = VIA_DIAMETER_MM / 2.0 + EDGE_CLEARANCE_MM
        if not margin <= x_mm <= BOARD_W_MM - margin:
            continue
        if not margin <= y_mm <= BOARD_H_MM - margin:
            continue
        clear = True
        for box in openings:
            if _box_distance(centre, box) < via_radius + mask_clearance:
                clear = False
                break
        if not clear:
            continue
        for box, point, hole, net_code in obstacles:
            hole_gap = math.hypot(centre.x - point.x, centre.y - point.y)
            if hole > 0 and hole_gap < hole + via_hole + hole_clearance:
                clear = False
                break
            if net_code == net.GetNetCode():
                continue
            if _box_distance(centre, box) < via_radius + clearance:
                clear = False
                break
            if hole > 0 and hole_gap < hole + hole_clearance + via_radius:
                clear = False
                break
            # the track that bonds the pad to the via has to clear it too
            if _segment_box_distance(position, centre, box) < \
                    clearance + stitch_half:
                clear = False
                break
        if not clear:
            continue
        for start, end, half, net_code in segments:
            if net_code == net.GetNetCode():
                continue
            reach = half + clearance
            if _segment_distance(centre, start, end) < \
                    reach + pcbnew.FromMM(VIA_DIAMETER_MM / 2.0):
                clear = False
                break
            if min(_segment_distance(position, start, end),
                   _segment_distance(centre, start, end)) < \
                    reach + stitch_half:
                clear = False
                break
        if not clear:
            continue
        _add_via(board, centre, net)
        _add_track(board, position, centre, pcbnew.F_Cu, net,
                   STITCH_TRACK_WIDTH_MM)
        return centre
    raise RuntimeError(
        "no clear stitch position for %s pad %s at (%.2f, %.2f)"
        % (footprint.GetReference(), pad.GetNumber(),
           pcbnew.ToMM(position.x) - ORIGIN_MM[0],
           ORIGIN_MM[1] - pcbnew.ToMM(position.y)))


#: Reference pads this pass leaves alone, and why. The converter's thermal
#: pad already has its own ring of vias, placed for heat rather than for the
#: shortest return, so stitching it again would only add holes.
STITCH_EXEMPT_PADS = {
    "U1.%s" % netlist.IP5306_PINS["GND"]:
        "the converter's thermal pad, which carries its own vias",
}


def _stitch_grounds(board, footprints, nets):
    """Every surface pad on the reference reaches its pour through its own
    via.

    The reference is a pour on the back layer, so a pad that exists only on
    the front is not on it until something takes it there. Doing it here
    rather than leaving it to the router keeps the return path a property of
    the pad's net rather than of a search.
    """
    for reference, footprint in sorted(footprints.items()):
        for pad in footprint.Pads():
            if pad.GetNetname() != netlist.SYSTEM_GROUND_NET:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            if "%s.%s" % (reference, pad.GetNumber()) in STITCH_EXEMPT_PADS:
                continue
            _stitch(board, footprint, pad, nets[netlist.SYSTEM_GROUND_NET])


#: The converter's ground pad, taken to the reference by its own ring of
#: vias. They stand outside the pad rather than inside it: a via in a pad
#: that receives solder is a via the paste drains into, and the board's own
#: check forbids it.
#: Copper this module draws itself, because the pads it joins belong to
#: different power nets and sit closer together than any two pours can.
#:
#: Each entry names a pad, then a path of (x, y, width) steps in the board
#: frame, or (x, y, width, layer) where the segment changes side. The first
#: steps leave the package at a width the neighbouring pins permit; the rest
#: are as wide as the current wants. A search has no freedom inside any of
#: them: the shape is the requirement.
#:
#: Where a path changes side it is because the conductor it has to cross is
#: a pour that spans the board, and a pair of vias carries it under rather
#: than around: two, because one via's barrel is not enough for this current.
GENERATED_NECKS = (
    # the converter's charger input, out to the left
    ("U1.1", ((25.0, 26.405, 1.0), (24.0, 26.0, 1.0))),
    # the input switch's drain, across to the charger's own bulk
    ("Q1.3", ((22.5, 19.5, 1.0), (23.5, 19.8, 1.0))),
    # its output, straight up to the capacitance that answers a load step
    ("U1.8", ((31.475, 28.0, 1.0), (31.475, 30.6, 1.6))),
    # its switch pin, right and up to the inductor
    ("U1.7", ((34.0, 25.135, 1.0), (34.0, 26.4, 1.0),
              (34.0, 27.5, 1.6), (37.6, 27.5, 1.6))),
    # its cell-rail pin, right and down to the other end of the inductor
    ("U1.6", ((35.5, 23.865, 1.0), (35.5, 22.6, 1.0),
              (35.5, 21.5, 1.6), (37.6, 21.5, 1.6))),
    # the cell connector's two terminals, which the protection keeps apart.
    # The positive runs on to the cell-rail probe rather than stopping in
    # the pour: the current it carries is the cell's own, and a conductor
    # that wide should be drawn where it goes rather than left to the fill
    # to spread.
    ("J3.1", ((63.0, 27.5, 2.0), (60.0, 26.5, 2.0), (52.0, 26.5, 2.0))),
    ("J3.2", ((66.96, 38.5, 2.0), (61.5, 38.5, 2.0))),
    # the input receptacle's supply, from the escape bar up to the damper
    ("__bar_J1", ((17.0, 12.0, 1.6), (17.0, 18.0, 1.6))),
    # the output receptacle's supply, from the enable switch down to its bar
    # the output receptacle's supply, from its escape bar across to the
    # corridor and up the back of the board, under the cell rail
    ("__bar_J2", ((53.0, 9.0, 1.6), (47.0, 9.0, 1.6),
                  (47.0, 13.0, 1.6, "B.Cu"), (47.0, 29.4, 1.6, "B.Cu"),
                  (47.0, 30.5, 1.6, "F.Cu"))),
    # the enable switch's own drain, out to that corridor
    ("Q6.3", ((44.0, 32.0, 1.0), (47.0, 30.5, 1.5))),
)

#: Pads joined to each other over the top of their own package, and how far
#: outside the pad row the link stands. Each protection package's two drain
#: pins are one node inside it, so the copper between them is not a route:
#: it is the package's own node, made visible to the connectivity check.
GENERATED_PAD_LINKS = tuple(
    ("Q%d.%s" % (index, netlist.AO8810_PINS["D"][0]),
     "Q%d.%s" % (index, netlist.AO8810_PINS["D"][1]))
    for index in range(3, 3 + netlist.PROTECTION_PACKAGES))
PAD_LINK_STANDOFF_MM = 1.0
PAD_LINK_WIDTH_MM = 0.5



#: The vias sit above and below the exposed pad, in the corridor between
#: the two lead rows, because those are the only directions in which nothing
#: of another net stands.
CONVERTER_VIA_OFFSETS_MM = tuple(
    (x, y) for y in (-2.95, 2.95) for x in (-1.0, 0.0, 1.0))


def _converter_thermal_vias(board, footprints, nets):
    footprint = footprints["U1"]
    pad = next(p for p in footprint.Pads()
               if p.GetNumber() == netlist.IP5306_PINS["GND"])
    centre = pad.GetPosition()
    for dx, dy in CONVERTER_VIA_OFFSETS_MM:
        position = pcbnew.VECTOR2I(int(centre.x + pcbnew.FromMM(dx)),
                                   int(centre.y + pcbnew.FromMM(dy)))
        _add_via(board, position, nets[netlist.SYSTEM_GROUND_NET],
                 POWER_VIA_DIAMETER_MM, POWER_VIA_DRILL_MM)
        _add_track(board, centre, position, pcbnew.F_Cu,
                   nets[netlist.SYSTEM_GROUND_NET], STITCH_TRACK_WIDTH_MM)


def fill_zones(board):
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    return board


def build(with_copper=True):
    """The board.

    `with_copper=False` produces the same placement with no pours: a
    placement search refuses a board that already carries copper, because
    moving a footprint would leave its copper behind. Everything conductive
    is generated from the accepted poses afterwards, so the two forms cannot
    disagree about where a part is.
    """
    board = pcbnew.CreateEmptyBoard()
    _design_settings(board)
    nets = _nets(board)
    pin_net = netlist.pin_to_net()

    footprints = {}
    placed = fixed_placements()
    for reference, (x, y, rotation) in sorted(placed.items()):
        part = netlist.PARTS[reference]
        if not part["footprint"]:
            continue
        footprints[reference] = _load(
            board, reference, part, x, y, rotation, pin_net, nets)

    _add_outline(board)
    if with_copper:
        _receptacle_escapes(board, footprints, nets)
        _generated_necks(board, footprints, nets)
        _generated_pad_links(board, footprints, nets)
        _add_pours(board, nets, footprints)
        _converter_thermal_vias(board, footprints, nets)
        _stitch_grounds(board, footprints, nets)
        _check_via_mask_clearance(board)
    _add_silkscreen(board, footprints)
    return board, footprints


def _check_via_mask_clearance(board):
    """Refuse a board whose own via reaches a solder-mask opening.

    The stitch searches for a position that clears every opening; the vias
    the design states outright - a side change, the converter's thermal
    ring - are placed rather than searched, so this is what says when one of
    those has been placed somewhere it cannot be tented.
    """
    openings = _mask_openings(board)
    clearance = pcbnew.FromMM(VIA_MASK_CLEARANCE_MM)
    close = []
    for item in board.GetTracks():
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        centre = item.GetPosition()
        radius = item.GetWidth(pcbnew.F_Cu) / 2.0
        for box in openings:
            gap = _box_distance(centre, box) - radius
            if gap < clearance:
                close.append("%s at (%.2f, %.2f) is %.3f mm from an opening"
                             % (item.GetNetname(),
                                pcbnew.ToMM(centre.x) - ORIGIN_MM[0],
                                ORIGIN_MM[1] - pcbnew.ToMM(centre.y),
                                pcbnew.ToMM(gap)))
                break
    if close:
        raise ValueError("a via stands on a solder-mask opening: "
                         + "; ".join(sorted(close)))


# ---------------------------------------------------------------------------
# silkscreen

SILK_LAYER = pcbnew.F_SilkS
#: The smallest text this board's silkscreen carries. Below the height the
#: design rules require, a legend is not a legend.
SILK_MIN_TEXT_MM = 0.9
SILK_TEXT_MM = 1.2
SILK_THICKNESS_MM = 0.15
RATING_Y_MM = 2.2


def _text(board, value, x, y, size_mm=SILK_TEXT_MM, layer=None):
    if size_mm < SILK_MIN_TEXT_MM:
        raise ValueError("silkscreen text below the height the rules require")
    item = pcbnew.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(_point(x, y))
    item.SetLayer(SILK_LAYER if layer is None else layer)
    item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size_mm),
                                     pcbnew.FromMM(size_mm)))
    item.SetTextThickness(pcbnew.FromMM(SILK_THICKNESS_MM))
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(item)
    return item


#: Where a label may be nudged to, in order, when the place it belongs
#: overlaps something. Silkscreen that lands on a pad is not printed, and
#: silkscreen that lands on another part's outline is not readable, so the
#: position is searched rather than asserted.
SILK_NUDGES_MM = tuple(
    (dx, dy)
    for step in (0.0, 0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.4, 5.2,
                 6.0, 7.0, 8.0)
    for dx, dy in ((0.0, -step), (0.0, step), (-step, 0.0), (step, 0.0),
                   (-step, -step), (step, -step), (-step, step),
                   (step, step)))


def _silk_obstacles(board):
    """Every pad and every footprint outline a label has to stay off."""
    boxes = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            box = pad.GetBoundingBox()
            boxes.append((pcbnew.ToMM(box.GetLeft()),
                          pcbnew.ToMM(box.GetTop()),
                          pcbnew.ToMM(box.GetRight()),
                          pcbnew.ToMM(box.GetBottom())))
        for item in footprint.GraphicalItems():
            if item.GetLayer() != SILK_LAYER:
                continue
            box = item.GetBoundingBox()
            boxes.append((pcbnew.ToMM(box.GetLeft()),
                          pcbnew.ToMM(box.GetTop()),
                          pcbnew.ToMM(box.GetRight()),
                          pcbnew.ToMM(box.GetBottom())))
    for item in board.GetDrawings():
        if item.GetLayer() not in (SILK_LAYER, pcbnew.Edge_Cuts):
            continue
        box = item.GetBoundingBox()
        boxes.append((pcbnew.ToMM(box.GetLeft()) - 0.3,
                      pcbnew.ToMM(box.GetTop()) - 0.3,
                      pcbnew.ToMM(box.GetRight()) + 0.3,
                      pcbnew.ToMM(box.GetBottom()) + 0.3))
    return boxes


def _label(board, obstacles, value, x, y, size_mm=SILK_TEXT_MM):
    """One label, nudged until it clears every pad and outline near it."""
    half_w = 0.42 * size_mm * max(len(value), 1) + 0.2
    half_h = 0.75 * size_mm + 0.2
    for dx, dy in SILK_NUDGES_MM:
        bx, by = to_board(x + dx, y + dy)
        left, right = bx - half_w, bx + half_w
        top, bottom = by - half_h, by + half_h
        if any(left < ox1 and ox0 < right and top < oy1 and oy0 < bottom
               for ox0, oy0, ox1, oy1 in obstacles):
            continue
        item = _text(board, value, x + dx, y + dy, size_mm=size_mm)
        box = item.GetBoundingBox()
        obstacles.append((pcbnew.ToMM(box.GetLeft()),
                          pcbnew.ToMM(box.GetTop()),
                          pcbnew.ToMM(box.GetRight()),
                          pcbnew.ToMM(box.GetBottom())))
        return item
    raise RuntimeError("no clear silkscreen position for %r near (%.1f, %.1f)"
                       % (value, x, y))


def rating_text():
    """What the board is marked with, from what it claims, not from taste."""
    return "IN 5V %.0fA REQ  OUT %.0fV %.0fA" % (
        netlist.REQUIRED_ADVERTISEMENT_A, netlist.RATED_OUTPUT_V,
        netlist.RATED_OUTPUT_A)


def probe_labels():
    """Which probe carries which net, from the netlist rather than a list."""
    pin_net = netlist.pin_to_net()
    return {reference: pin_net["%s.1" % reference]
            for reference in netlist.PARTS if reference.startswith("TP")}


#: Parts the cell keepout is drawn around rather than kept clear of: the
#: connector the cell mates with, and the probes that measure it.
KEEPOUT_PERMITTED = ("J3",) + tuple(
    "TP%d" % index for index in range(1, 12))


def _keepout_outline(board):
    """The region the cell and its leads occupy, on a documentation layer.

    Not on the silkscreen: the outline would cross the connector that stands
    inside it, and a legend that crosses a part is not a legend. What the
    board is marked with is the word, which is beside the connector.
    """
    x0, y0, x1, y1 = CELL_KEEPOUT_MM
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for start, end in zip(corners, corners[1:]):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(_point(*start))
        shape.SetEnd(_point(*end))
        shape.SetLayer(pcbnew.Dwgs_User)
        shape.SetWidth(pcbnew.FromMM(0.15))
        board.Add(shape)


def parts_inside_keepout(placed=None):
    """Every part whose courtyard reaches into the cell's own region."""
    placed = fixed_placements() if placed is None else placed
    x0, y0, x1, y1 = CELL_KEEPOUT_MM
    inside = []
    for reference, (x, y, rotation) in sorted(placed.items()):
        if reference in KEEPOUT_PERMITTED:
            continue
        part = netlist.PARTS[reference]
        if not part["footprint"]:
            continue
        dx0, dy0, dx1, dy1 = _courtyard_offsets(part, rotation)
        if (x + dx0 < x1 and x0 < x + dx1
                and y + dy0 < y1 and y0 < y + dy1):
            inside.append(reference)
    return inside


def _add_silkscreen(board, footprints):
    _keepout_outline(board)
    obstacles = _silk_obstacles(board)
    placed = fixed_placements()
    _label(board, obstacles, rating_text(), BOARD_W_MM / 2.0, RATING_Y_MM,
           size_mm=1.2)
    _label(board, obstacles, "IN", INPUT_RECEPTACLE_X_MM, 10.8, size_mm=1.2)
    _label(board, obstacles, "OUT", OUTPUT_RECEPTACLE_X_MM, 10.8, size_mm=1.2)
    _label(board, obstacles, "CELL", CELL_KEEPOUT_MM[2] - 3.0,
           CELL_KEEPOUT_MM[3] - 1.6, size_mm=1.2)
    for index, reference in enumerate(("D1", "D2", "D3", "D4")):
        x, y, _ = placed[reference]
        _label(board, obstacles, "%d" % (25 * (index + 1)), x, y - 1.8,
               size_mm=SILK_MIN_TEXT_MM)
    x, y, _ = placed["D5"]
    _label(board, obstacles, "SRC", x, y - 1.8, size_mm=SILK_MIN_TEXT_MM)
    x, y, _ = placed["SW1"]
    _label(board, obstacles, "ON", x, y + 3.8, size_mm=1.0)
    for reference, net in sorted(probe_labels().items()):
        x, y, _ = placed[reference]
        _label(board, obstacles, net, x, y - 1.6, size_mm=SILK_MIN_TEXT_MM)
    del footprints


def write(path=None):
    """Write the board, then rewrite the project it belongs to.

    Saving a board rewrites the project file beside it with KiCad's own
    defaults, which is how the rule severities this board declares as
    warnings would become ignores. The project is therefore regenerated from
    the design source afterwards, every time, rather than left as whatever
    the save left behind.
    """
    from . import build as _build
    board, _ = build()
    fill_zones(board)
    target = BOARD_PATH if path is None else path
    pcbnew.SaveBoard(target, board)
    if path is None:
        _build.write_project()
    return target


def write_placement_board(path):
    board, _ = build(with_copper=False)
    pcbnew.SaveBoard(path, board)
    return path


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
