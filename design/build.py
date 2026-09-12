from __future__ import annotations

import json
import os
import sys

from . import netlist, schematic

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def schematic_path():
    return os.path.join(REPO_ROOT, netlist.PROJECT_NAME + ".kicad_sch")


def project_path():
    return os.path.join(REPO_ROOT, netlist.PROJECT_NAME + ".kicad_pro")


def generate_schematic_text():
    netlist.pin_to_net()
    tree = schematic.build(
        netlist.PARTS, netlist.NETS, set(netlist.NO_CONNECT),
        netlist.PROJECT_NAME)
    return schematic.render(tree)


DESIGN_RULES = {
    "min_clearance": 0.15,
    "min_track_width": 0.15,
    "min_via_diameter": 0.45,
    "min_via_annular_width": 0.1,
    "min_through_hole_diameter": 0.25,
    "min_hole_clearance": 0.25,
    "min_hole_to_hole": 0.25,
    "min_copper_edge_clearance": 0.3,
}


#: Two classes. Every net on this board shares one clearance requirement -
#: the highest potential anywhere is the input rail and there is no isolation
#: barrier - but the conductors that carry cell-side current are given a
#: wider default width, because a router that draws them at the signal width
#: would produce copper the temperature-rise check then rejects.
NET_CLASSES = [
    {
        "name": "Default",
        "clearance": 0.15,
        "track_width": 0.25,
        "via_diameter": 0.6,
        "via_drill": 0.3,
    },
    {
        "name": "Power",
        "clearance": 0.15,
        "track_width": 1.5,
        "via_diameter": 0.8,
        "via_drill": 0.4,
    },
]

#: Which nets belong to the wide class. Everything the cell-side or output
#: current runs through; the rest is signal.
POWER_CLASS_NETS = tuple(sorted(set(
    netlist.CELL_CURRENT_NETS + netlist.OUTPUT_CURRENT_NETS
    + ("VBUS", "VIN"))))


def project_document(root_sheet_uuid):
    # Membership belongs in `netclass_assignments`, never in a `nets`
    # list inside the class entry: the KiCad 6 shape is not read by
    # `kicad-cli pcb drc`, which is the DRC path every verdict on this
    # board runs, so a class declaring it reaches no net and judges
    # nothing. Measured on KiCad 10.0.6 against this board's own copper:
    # raising Power's clearance to 0.9 mm produces 499 clearance
    # violations through the assignments channel and not one through the
    # in-class list. Assignments rather than patterns because this list
    # is exact - a net renamed out from under it becomes a finding,
    # where a pattern would quietly go on matching nothing.
    net_settings = {
        "classes": [dict(entry) for entry in NET_CLASSES],
        "netclass_assignments": {net: ["Power"]
                                 for net in POWER_CLASS_NETS},
    }
    return {
        "board": {
            "design_settings": {
                "rule_severities": {
                    "missing_courtyard": "warning",
                    "track_not_centered_on_via": "warning",
                    "tuning_profile_track_geometries": "warning",
                    "footprint_filters_mismatch": "warning",
                    "footprint_type_mismatch": "warning",
                },
                "rules": dict(DESIGN_RULES),
            },
            "drc_exclusions": [],
            "layer_presets": [],
            "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {
            "erc_exclusions": [],
            "meta": {"version": 0},
            "pin_map": [],
            "rule_severities": {
                "single_global_label": "warning",
                "four_way_junction": "warning",
                "simulation_model_issue": "warning",
                "footprint_filter": "warning",
            },
        },
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": netlist.PROJECT_NAME + ".kicad_pro",
                 "version": 3},
        "net_settings": net_settings,
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[root_sheet_uuid, "Root"]],
        "text_variables": {},
    }


def generate_project_text():
    """The project file's bytes, so a test can compare without writing.

    The schematic has had `generate_schematic_text` since the start and
    the committed file is held against it; the project had no such seam,
    and a generator and a committed file that nothing compares is how
    board/manifest.json drifted away from design/manifest.py.
    """
    root_uuid = str(schematic._uuid("sheet", netlist.PROJECT_NAME))
    return json.dumps(project_document(root_uuid), indent=2) + "\n"


def write_project():
    with open(project_path(), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(generate_project_text())
    return (project_path(),)


def write():
    text = generate_schematic_text()
    with open(schematic_path(), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return (schematic_path(),) + write_project()


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
