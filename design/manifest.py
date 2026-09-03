"""The board's manifest, generated from the design source rather than typed.

The manifest is what the validator reads: which files are the design, which
gates are mandatory, what the connectors carry, what the stackup is. Every
one of those is already stated somewhere in this repository - in the netlist,
in the layout, in the fabrication requirements - and a manifest typed by hand
is a second copy of all of it that can drift from the first.

So it is generated. The pin maps come from the netlist's own connector
contract, the constraint floor from the design settings the board file is
written with, and the simulation stages from the scenarios that exist.
"""
from __future__ import annotations

import json
import os
import sys

from . import build, layout, netlist, simulation

MANIFEST_PATH = os.path.join(layout.REPO_ROOT, "board", "manifest.json")

RELEASE_PROFILE_ID = "jlcpcb-2layer-assembled"

MANDATORY_GATES = (
    "ARCH.CONTENTS",
    "ARCH.PROVENANCE",
    "BOM.NATIVE_PARITY",
    "CONTRACT.CONNECTOR",
    "CONTRACT.PLACEMENT",
    "CPL.NATIVE_PARITY",
    "DRC.AUTHORITATIVE",
    "DRC.CONSTRAINT_FLOOR",
    "DRC.NO_SUPPRESSED_RULES",
    "ERC.AUTHORITATIVE",
    "NET.TOPOLOGY",
    "PROV.REPORT_FRESHNESS",
    "ROUTE.GEOMETRY_HYGIENE",
    "ROUTE.PROVENANCE",
    "ROUTE.TINY_SEGMENTS",
    "SIM.SCENARIOS",
    "SIM.STAGE_COVERAGE",
    "STACK.GERBER_PARITY",
    "STACK.NATIVE_VS_MANIFEST",
    "VIA.ANNULUS_MASK_OVERLAP",
    "VIA.IN_PAD_CONTACT",
    "VIA.MASK_CLEARANCE_TARGET",
)

REQUIRED_EVIDENCE = (
    "constraints/requirements.json",
    "evidence/index.json",
    "fab/selection.json",
    "generated/requirements.json",
    "generated/routing.json",
)


#: What each connector's own land pattern presents, counted the way the
#: contract is judged: one position per distinct pad number, so a
#: receptacle's four shell lands are the one shell terminal it is wired as,
#: and the row count is the smaller of the distinct pad x and y coordinates,
#: which puts those shell lands on a row of their own. A pad with no number
#: is a locating peg rather than a position and is not counted. These are
#: the part's numbers, not the netlist's: the receptacles carry contacts
#: this board leaves unconnected, and counting only what the netlist names
#: would let a substituted connector with fewer contacts pass.
CONNECTOR_LAND_PATTERNS = {
    "J1": {"positions": 17, "rows": 2, "pitch_mm": 0.5},
    "J2": {"positions": 17, "rows": 2, "pitch_mm": 0.5},
    "J3": {"positions": 2, "rows": 1, "pitch_mm": 3.96},
}


def _connector_id(reference):
    return {"J1": "input_receptacle", "J2": "output_receptacle",
            "J3": "cell_connector"}[reference]


def connector_contracts():
    """One contract per connector, from the netlist's own function map."""
    pin_net = netlist.pin_to_net()
    contracts = []
    for reference in sorted(netlist.CONNECTOR_FUNCTION_NETS,
                            key=lambda name: int(name[1:])):
        pins = {}
        for pin_ref, net in pin_net.items():
            owner, _, number = pin_ref.partition(".")
            if owner == reference:
                pins[number] = net
        pattern = CONNECTOR_LAND_PATTERNS[reference]
        contracts.append({
            "id": _connector_id(reference),
            "reference": reference,
            "required_positions": pattern["positions"],
            "required_rows": pattern["rows"],
            "required_pitch_mm": pattern["pitch_mm"],
            "required_side": "front",
            "population": {"dnp": False, "exclude_from_bom": False},
            "pin_map": {number: pins[number] for number in sorted(pins)},
        })
    return contracts


def placement_rules():
    """Groups the board must contain, counted rather than located.

    Each entry is a family the design source generates as a set; a board that
    lost one, or grew one, disagrees with the source that made it.
    """
    packages = netlist.PROTECTION_PACKAGES
    return [
        {"id": "RECEPTACLES", "reference_regex": r"^J[12]$", "count": 2},
        {"id": "PROTECTION_SWITCHES",
         "reference_regex": r"^Q[3-%d]$" % (2 + packages), "count": packages},
        {"id": "STATE_OF_CHARGE_INDICATORS",
         "reference_regex": r"^D[1-4]$", "count": 4},
        {"id": "INPUT_CLAMPS", "reference_regex": r"^D[6-8]$", "count": 3},
        {"id": "OUTPUT_CLAMPS", "reference_regex": r"^D(9|10|11)$",
         "count": 3},
        {"id": "PROBES", "reference_regex": r"^TP([1-9]|1[01])$",
         "count": 11},
        {"id": "MOUNTING", "reference_regex": r"^H[1-4]$", "count": 4},
    ]


def net_topology_rules():
    """The routes whose topology is a requirement rather than a result.

    The converter's switch node carries the whole inductor current and swings
    at the switching frequency, so it stays on one layer and takes no via: a
    via there is a hole in the conductor the converter's loop runs through
    and a stub on the noisiest node on the board. Each protection package's
    drain is the node between its two devices, and it is one package's
    internal node rather than a route, so it stays where the package is.
    """
    return [
        {"id": "CONVERTER_SWITCH_NODE",
         "net_regex": r"^SW$",
         "source_pad_regex": r"^U1\.%s$" % netlist.IP5306_PINS["SW"],
         "load_pad_regex": r"^L1\.1$",
         "max_vias_per_net": 0,
         "permitted_layers": ["F.Cu"]},
        {"id": "PROTECTION_DRAINS",
         "net_regex": r"^PROT_D\d$",
         "source_pad_regex": r"^Q[3-5]\.%s$" % netlist.AO8810_PINS["D"][0],
         "load_pad_regex": r"^Q[3-5]\.%s$" % netlist.AO8810_PINS["D"][1],
         "max_vias_per_net": 0,
         "permitted_layers": ["F.Cu"]},
    ]


def stackup_expected():
    """What each copper layer is for.

    The front layer pours the power nets that carry the cell and output
    current; the back layer pours the one reference everything returns to.
    The gate names one net per layer, so each entry names a net the layer
    would not be that layer without.
    """
    return [{"role": "plane", "plane_net": "BAT"},
            {"role": "plane", "plane_net": netlist.SYSTEM_GROUND_NET}]


def simulation_stages():
    return {"pre_layout": ["sim/" + name for name in sorted(
        simulation.documents())]}


def document():
    project = netlist.PROJECT_NAME
    classes = {entry["name"]: {key: value
                               for key, value in entry.items()
                               if key not in ("name", "nets")}
               for entry in build.NET_CLASSES}
    return {
        "schema_version": 2,
        "board_id": project,
        "constraint_version": "layout-stage-2026-09-02",
        "project_root": "..",
        "tools": {"kicad_cli": "kicad-cli"},
        "sources": {
            "schematic": project + ".kicad_sch",
            "project": project + ".kicad_pro",
            "pcb": project + ".kicad_pcb",
        },
        "board_origin_mm": [0.0, 0.0],
        "documentation_globs": ["BRIEF.md"],
        "checks": {
            "erc": {"extra_flags": []},
            "drc": {
                "extra_flags": [],
                "forbidden_severities": ["ignore"],
                "permitted_ignored_rules": [],
                "constraint_floor": {
                    "rules": dict(build.DESIGN_RULES),
                    "net_classes": classes,
                },
            },
        },
        "waivers": [],
        "geometry_profile": {
            "version": "geom-1",
            "tolerances": {
                "waiver_location_mm": {"value": 0.001, "units": "mm"},
                "polygon_chord_error_mm": {"value": 0.001, "units": "mm"},
                "contact_mm": {"value": 1e-06, "units": "mm"},
                "coordinate_match_mm": {"value": 0.002, "units": "mm"},
                "rotation_match_deg": {"value": 0.1, "units": "deg"},
                "dimension_match_mm": {"value": 0.002, "units": "mm"},
                "clearance_match_mm": {"value": 0.01, "units": "mm"},
                "layer_symmetric_difference_mm2": {"value": 0.05,
                                                   "units": "mm2"},
            },
        },
        "stackup": {"expected": stackup_expected()},
        "placement_rules": placement_rules(),
        "net_topology": {"rules": net_topology_rules()},
        "routing": {
            "min_segment_mm": layout.MIN_SEGMENT_MM,
            "short_segment_justification": {"allow_pad_or_via_entry": True},
            "hygiene": {"forbid_duplicate_geometry": True,
                        "forbid_net_crossings": True,
                        "forbid_dangling": True},
            "provenance": "generated/routing.json",
        },
        "via_mask": {
            "pad_contact": {"populated_pad_attributes": ["SMD"],
                            "require_paste": True},
            "metric": "annulus_to_opening_mm",
            "note":
                "annulus_contacts counts zero-distance tangency as contact; "
                "annulus_strict_overlaps counts positive shared area only",
            "mask_dam_rule": "contact",
            "design_target_mm": layout.VIA_MASK_CLEARANCE_MM,
        },
        "artifacts": {
            "gerber_dir": "generated/release/gerbers",
            "bom": "generated/release/bom.csv",
            "cpl": "generated/release/cpl.csv",
            "fabrication_manifest": "generated/release/fabrication.json",
            "validation_report": "generated/release/validation.json",
            "position_tolerance_mm": 0.01,
            "cpl_fields": {"designator": "Ref", "x": "PosX", "y": "PosY",
                           "side": "Side", "rotation": "Rot"},
            "cpl_origin": {"frame": "absolute page origin",
                           "offset_mm": [0.0, 0.0]},
            "gerber_export_flags": [
                "--layers",
                "F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,"
                "Edge.Cuts",
                "--no-protel-ext", "--use-drill-file-origin",
                "--subtract-soldermask"],
            "reports_dir": "generated/release/reports",
        },
        "archive": {
            "zip": "generated/release/%s-fabrication.zip" % project,
            "allow": [
                {"file_function": "Copper,L1,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Copper,L2,Bot", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Soldermask,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Soldermask,Bot", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Legend,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Legend,Bot", "require_payload": False,
                 "min_count": 1},
                {"file_function": "Paste,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Profile,NP", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Drill/plated", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Drill/nonplated", "require_payload": True,
                 "min_count": 1},
                {"file_function": "JobFile", "require_payload": True,
                 "min_count": 1},
            ],
        },
        "assembly": {
            "schematic_fields": ["LCSC", "MPN", "Manufacturer"],
            "required_part_fields": ["LCSC"],
            "bom_fields": {"designators": "Designator", "value": "Comment",
                           "footprint": "Footprint", "quantity": "Quantity",
                           "LCSC": "LCSC Part #"},
            "schematic_export": {
                "fields": ["Reference", "Value", "Footprint", "${DNP}",
                           "${EXCLUDE_FROM_BOM}", "LCSC", "MPN",
                           "Manufacturer"],
                "labels": ["Reference", "Value", "Footprint", "DNP",
                           "ExcludeFromBOM", "LCSC", "MPN", "Manufacturer"],
                "flags": [],
                "reference_label": "Reference",
                "value_label": "Value",
                "footprint_label": "Footprint",
                "dnp_label": "DNP",
                "exclude_label": "ExcludeFromBOM",
                "true_tokens": ["1", "true", "yes", "x", "dnp"],
            },
            "compared_part_fields": ["LCSC", "MPN", "Manufacturer"],
        },
        "release_generation": {
            "lock_file_globs": ["*.lck", "~*.lck", ".#*", "*-lock",
                                "*.kicad_prl-lock"],
            "erc": {"output": "erc.json"},
            "drc": {"output": "drc.json"},
            "drill": {"flags": ["--format", "excellon",
                                "--excellon-separate-th", "--drill-origin",
                                "plot"]},
            "bom": {
                "output": "bom.csv",
                "fields": ["${QUANTITY}", "Reference", "Value", "Footprint",
                           "LCSC"],
                "labels": ["Quantity", "Designator", "Comment", "Footprint",
                           "LCSC Part #"],
                "group_by": ["Value", "Footprint", "LCSC"],
                "flags": ["--exclude-dnp", "--ref-range-delimiter", ""],
                "field_map": {"designators": "Designator", "value": "Comment",
                              "footprint": "Footprint",
                              "quantity": "Quantity",
                              "LCSC": "LCSC Part #"},
            },
            "cpl": {
                "output": "cpl.csv",
                "flags": ["--format", "csv", "--units", "mm", "--side",
                          "both", "--exclude-dnp"],
                "field_map": {"designator": "Ref", "x": "PosX", "y": "PosY",
                              "side": "Side", "rotation": "Rot"},
                "origin": {"frame": "absolute page origin",
                           "offset_mm": [0.0, 0.0]},
            },
            "archive": {"zip": "%s-fabrication.zip" % project},
        },
        "reports": {
            "files": ["generated/release/reports/erc.json",
                      "generated/release/reports/drc.json"],
            "source_field": "source",
            "date_field": "date",
            "require_source_hash": True,
            "source_closure": ["*.kicad_sch", "*.kicad_pcb", "*.kicad_pro",
                               "*.kicad_dru", "constraints/*.json",
                               "sim/*.json", "fab/*.json",
                               "components/*.json", "evidence/index.json"],
            "source_hash_field": "source_sha256",
            "closure_field": "source_closure_sha256",
        },
        "fixture": {"attributes_file": ".gitattributes"},
        "release_profile": {
            "id": RELEASE_PROFILE_ID,
            "mandatory_gates": list(MANDATORY_GATES),
            "required_evidence": list(REQUIRED_EVIDENCE),
        },
        "simulation": {
            "stages": simulation_stages(),
            "required_stages": ["pre_layout"],
        },
        "connector_gender_tokens": {
            "receptacle": ["receptacle", "socket", "female"],
            "plug": ["plug", "header", "male"],
        },
        "connector_contracts": connector_contracts(),
    }


def write():
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return MANIFEST_PATH


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
