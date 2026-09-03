from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

import pcbnew

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from design import (build, cost, evidence, ksym, layout,  # noqa: E402
                    libraries, manifest, netlist, requirements, route, rules,
                    simulation)

TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa.sim import model_registry, ngspice  # noqa: E402
from pcbqa.sim import scenario as sim_scenario  # noqa: E402


class DesignSource(unittest.TestCase):
    def test_pin_assignment_is_unique(self):
        mapping = netlist.pin_to_net()
        self.assertEqual(len(mapping),
                         sum(len(pins) for pins in netlist.NETS.values()))

    def test_every_symbol_pin_is_connected_or_declared_no_connect(self):
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        mapping = netlist.pin_to_net()
        declared = set(netlist.NO_CONNECT)
        unresolved = []
        for reference, part in netlist.PARTS.items():
            for number in library.pins(part["lib_id"]):
                pin_ref = "%s.%s" % (reference, number)
                if pin_ref not in mapping and pin_ref not in declared:
                    unresolved.append(pin_ref)
        self.assertEqual(unresolved, [])

    def test_declared_pins_exist_on_the_symbol(self):
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        missing = []
        for pin_ref in list(netlist.pin_to_net()) + list(netlist.NO_CONNECT):
            reference, _, number = pin_ref.partition(".")
            lib_id = netlist.PARTS[reference]["lib_id"]
            if number not in library.pins(lib_id):
                missing.append(pin_ref)
        self.assertEqual(missing, [])

    def test_the_library_holds_nothing_the_design_source_does_not_write(self):
        produced = set(libraries.artifacts())
        present = set()
        for root, _, names in os.walk(libraries.FOOTPRINT_DIR):
            for name in names:
                present.add(os.path.join(root, name))
        present.add(libraries.SYMBOL_LIB_PATH)
        self.assertEqual(sorted(present - produced), [])

    def test_the_committed_design_files_are_the_generated_ones(self):
        with open(build.schematic_path(), "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), build.generate_schematic_text())
        for path, text in libraries.artifacts().items():
            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), text, path)


class PowerTopology(unittest.TestCase):
    def setUp(self):
        self.mapping = netlist.pin_to_net()

    def test_the_cell_negative_reaches_the_reference_only_by_the_switch(self):
        both = {netlist.CELL_NEGATIVE_NET, netlist.SYSTEM_GROUND_NET}
        for reference in netlist.PARTS:
            nets = {net for pin, net in self.mapping.items()
                    if pin.split(".")[0] == reference}
            if both <= nets:
                self.assertIn(reference, netlist.PROTECTION_REFERENCES,
                              reference)

    def test_every_protection_package_bridges_the_two_negatives(self):
        for reference in netlist.PROTECTION_REFERENCES:
            sources = {
                self.mapping["%s.%s" % (reference, pin)]
                for group in ("S1", "S2")
                for pin in netlist.AO8810_PINS[group]}
            self.assertEqual(
                sources,
                {netlist.CELL_NEGATIVE_NET, netlist.SYSTEM_GROUND_NET},
                reference)

    def test_the_protection_gates_are_driven_by_the_protection_device(self):
        for reference in netlist.PROTECTION_REFERENCES:
            self.assertEqual(
                self.mapping["%s.%s" % (reference,
                                        netlist.AO8810_PINS["G1"])],
                "PROT_OD")
            self.assertEqual(
                self.mapping["%s.%s" % (reference,
                                        netlist.AO8810_PINS["G2"])],
                "PROT_OC")

    def test_the_converter_switch_node_reaches_only_the_inductor(self):
        pins = [pin for pin, net in self.mapping.items() if net == "SW"]
        self.assertEqual(sorted(pins),
                         ["L1.1", "U1.%s" % netlist.IP5306_PINS["SW"]])

    def test_the_output_port_is_fed_only_through_the_enable_switch(self):
        bridging = {pin.split(".")[0] for pin, net in self.mapping.items()
                    if net == "VOUT"} & {
            pin.split(".")[0] for pin, net in self.mapping.items()
            if net == "VOUT_SW"}
        self.assertEqual(bridging, {"Q6"})

    def test_the_charger_input_is_fed_only_through_the_gated_switch(self):
        bridging = {pin.split(".")[0] for pin, net in self.mapping.items()
                    if net == "VBUS"} & {
            pin.split(".")[0] for pin, net in self.mapping.items()
            if net == "VIN"}
        self.assertEqual(bridging, {"Q1"})

    def test_both_configuration_conductors_are_terminated(self):
        for net, reference in (("CC1", "R1"), ("CC2", "R2")):
            self.assertEqual(self.mapping["%s.1" % reference], net)
            self.assertEqual(self.mapping["%s.2" % reference],
                             netlist.SYSTEM_GROUND_NET)

    def test_the_output_port_presents_a_source_pull_up_on_both(self):
        for net, reference in (("OUT_CC1", "R20"), ("OUT_CC2", "R21")):
            self.assertEqual(self.mapping["%s.2" % reference], net)
            self.assertEqual(self.mapping["%s.1" % reference], "VOUT_SW")

    def test_the_indicators_are_two_antiparallel_pairs(self):
        pairs = (("D1", "D2", "LED1"), ("D3", "D4", "LED2"))
        for first, second, driver in pairs:
            self.assertEqual(self.mapping["%s.2" % first], driver)
            self.assertEqual(self.mapping["%s.1" % first], "LED3")
            self.assertEqual(self.mapping["%s.1" % second], driver)
            self.assertEqual(self.mapping["%s.2" % second], "LED3")


class Evidence(unittest.TestCase):
    def test_the_frozen_documents_are_intact_and_all_referenced(self):
        self.assertEqual(evidence.verify(), [])

    def test_the_committed_index_is_the_computed_one(self):
        self.assertEqual(evidence.load_index(), evidence.compute_index())

    def test_every_parameter_names_a_frozen_document(self):
        known = set(evidence.load_index()["documents"])
        unknown = set()

        def walk(node):
            if isinstance(node, dict):
                document = node.get("document")
                if isinstance(document, str) and document not in known:
                    unknown.add(document)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(rules.load_parameters()["parts"])
        self.assertEqual(sorted(unknown), [])

    def test_every_bom_part_has_frozen_parameters_and_a_catalogue_entry(self):
        parameters = rules.load_parameters()["parts"]
        catalog = rules.load_catalog()["parts"]
        for reference, part in netlist.PARTS.items():
            if not part["in_bom"]:
                continue
            self.assertIn(part["mpn"], parameters, reference)
            self.assertIn(part["lcsc"], catalog, reference)

    def test_the_catalogue_holds_no_part_the_board_does_not_use(self):
        used = {part["lcsc"] for part in netlist.PARTS.values()
                if part["in_bom"]}
        self.assertEqual(sorted(set(rules.load_catalog()["parts"]) - used), [])


class Requirements(unittest.TestCase):
    def setUp(self):
        self.results = rules.evaluate_all()

    def test_no_board_rule_fails(self):
        failed = sorted(result["id"] for result in self.results
                        if result["verdict"]["result"] == "FAIL")
        self.assertEqual(failed, [])

    def test_the_only_unresolved_claim_is_the_one_the_datasheet_cannot_bound(
            self):
        unknown = sorted({result["id"] for result in self.results
                          if result["verdict"]["result"] == "UNKNOWN"})
        self.assertEqual(unknown, ["rated_output_current_supported"])

    def test_the_committed_requirement_evidence_is_current(self):
        with open(rules.REPORT_PATH, "r", encoding="utf-8") as handle:
            committed = json.load(handle)
        rules.write_report()
        with open(rules.REPORT_PATH, "r", encoding="utf-8") as handle:
            self.assertEqual(committed, json.load(handle))

    def test_every_requirement_is_registered_and_every_register_entry_used(
            self):
        judged = {result["claim"]["requirement"]["name"]
                  for result in self.results}
        judged |= set(simulation.MEASUREMENT_REQUIREMENTS.values())
        self.assertEqual(sorted(judged - set(requirements.REGISTER)), [])
        self.assertEqual(sorted(set(requirements.REGISTER) - judged), [])

    def test_every_simulated_assertion_answers_a_registered_requirement(self):
        mapped = set(simulation.MEASUREMENT_REQUIREMENTS)
        self.assertEqual(sorted(simulation.asserted_measurements() - mapped),
                         [])

    def test_the_register_is_well_formed_and_its_sources_resolve(self):
        self.assertTrue(requirements.check())

    def test_the_committed_register_is_the_generated_one(self):
        with open(requirements.REGISTER_PATH, "r", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), requirements.document())

    def test_every_probe_required_net_exists(self):
        for net in netlist.PROBE_REQUIRED_NETS:
            self.assertIn(net, netlist.NETS)

    def test_every_entering_conductor_is_clamped_or_exempt(self):
        parameters = rules.load_parameters()
        for result in rules.evaluate_esd_coverage(parameters):
            self.assertEqual(result["claim"]["quantity"]["value"], 0.0)


class Supply(unittest.TestCase):
    def test_stock_covers_the_planned_build(self):
        limits = cost.stock_limited_boards()
        self.assertGreaterEqual(min(limits.values()),
                                netlist.PLANNED_BUILD_QUANTITY)

    def test_every_bom_line_prices(self):
        report = cost.bom_cost(netlist.PLANNED_BUILD_QUANTITY)
        self.assertGreater(report["per_board_usd"], 0.0)
        self.assertEqual(len(report["lines"]), len(cost.line_items()))


class Scenarios(unittest.TestCase):
    def setUp(self):
        self.documents = simulation.documents()

    def test_every_scenario_validates(self):
        for name, document in self.documents.items():
            sim_scenario.validate_scenario(document)
            del name

    def test_the_committed_scenarios_are_the_generated_ones(self):
        present = sorted(os.listdir(simulation.SIM_DIR))
        self.assertEqual(present, sorted(self.documents))
        for name, document in self.documents.items():
            with open(os.path.join(simulation.SIM_DIR, name), "r",
                      encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), document, name)

    def test_every_scenario_runs_and_every_assertion_holds(self):
        backend = ngspice.backend_identity()
        if not backend["available"]:
            self.skipTest("no ngspice backend: " + backend["detail"])
        registry = model_registry.ModelRegistry([])
        work = os.path.join(REPO_ROOT, "out", "sim")
        for name, document in sorted(self.documents.items()):
            result = ngspice.run_scenario(
                registry, document, os.path.join(work, document["name"]))
            self.assertEqual(result["status"], "ran", name)
            self.assertTrue(result["converged"], name)
            for measurement, record in result["measurements"].items():
                verdict = record["verdict"]
                if verdict is None:
                    continue
                self.assertEqual(verdict["result"], "PASS",
                                 "%s: %s" % (name, measurement))

    def test_the_simulated_detector_threshold_agrees_with_the_requirement(
            self):
        backend = ngspice.backend_identity()
        if not backend["available"]:
            self.skipTest("no ngspice backend: " + backend["detail"])
        registry = model_registry.ModelRegistry([])
        document = self.documents["pre_layout_advertisement.json"]
        result = ngspice.run_scenario(
            registry, document,
            os.path.join(REPO_ROOT, "out", "sim", document["name"]))
        simulated = result["measurements"][
            "weak_advertisement_below_reference"]["claim"]["quantity"]["value"]
        parameters = rules.load_parameters()
        stated = max(
            entry["measured"] for entry in
            rules.evaluate_advertisement_detection(parameters)
            if entry["id"] == "threshold_above_1_5A_advertisement")
        self.assertLessEqual(simulated, stated)


class Manifest(unittest.TestCase):
    def setUp(self):
        self.document = manifest.document()

    def test_the_committed_manifest_is_the_generated_one(self):
        with open(manifest.MANIFEST_PATH, "r", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), self.document)

    def test_every_connector_contract_matches_the_netlist(self):
        mapping = netlist.pin_to_net()
        for contract in self.document["connector_contracts"]:
            reference = contract["reference"]
            for number, net in contract["pin_map"].items():
                self.assertEqual(mapping["%s.%s" % (reference, number)], net)

    def test_every_connector_land_pattern_is_the_footprints_own(self):
        """The declared land pattern is what the library footprint presents.

        The contract exists to catch a connector that was swapped for one
        that does not mate the same way, so the numbers it is judged against
        are read back from the footprint the board carries rather than taken
        on trust.
        """
        board = pcbnew.LoadBoard(layout.BOARD_PATH)
        for reference, pattern in manifest.CONNECTOR_LAND_PATTERNS.items():
            footprint = board.FindFootprintByReference(reference)
            self.assertIsNotNone(footprint, reference)
            numbered = [pad for pad in footprint.Pads() if pad.GetNumber()]
            positions = {pad.GetNumber(): pad for pad in numbered}
            self.assertEqual(len(positions), pattern["positions"], reference)
            places = [(round(pcbnew.ToMM(pad.GetPosition().x), 3),
                       round(pcbnew.ToMM(pad.GetPosition().y), 3))
                      for pad in positions.values()]
            xs = sorted({place[0] for place in places})
            ys = sorted({place[1] for place in places})
            self.assertEqual(min(len(xs), len(ys)), pattern["rows"], reference)
            spacing = [round(second - first, 3)
                       for axis in (xs, ys)
                       for first, second in zip(axis, axis[1:])
                       if second - first > 1e-6]
            self.assertEqual(min(spacing), pattern["pitch_mm"], reference)

    def test_the_constraint_floor_is_what_the_project_is_written_with(self):
        floor = self.document["checks"]["drc"]["constraint_floor"]
        self.assertEqual(floor["rules"], build.DESIGN_RULES)
        for entry in build.NET_CLASSES:
            self.assertIn(entry["name"], floor["net_classes"])

    def test_every_declared_scenario_file_exists(self):
        for stage, names in self.document["simulation"]["stages"].items():
            for name in names:
                self.assertTrue(
                    os.path.isfile(os.path.join(REPO_ROOT, name)),
                    "%s: %s" % (stage, name))
        for stage in self.document["simulation"]["required_stages"]:
            self.assertIn(stage, self.document["simulation"]["stages"])

    def test_every_placement_rule_counts_what_the_netlist_holds(self):
        for rule in self.document["placement_rules"]:
            pattern = re.compile(rule["reference_regex"])
            found = [reference for reference in netlist.PARTS
                     if pattern.match(reference)]
            self.assertEqual(len(found), rule["count"], rule["id"])

    def test_every_topology_rule_names_pads_the_netlist_holds(self):
        mapping = netlist.pin_to_net()
        for rule in self.document["net_topology"]["rules"]:
            net = re.compile(rule["net_regex"])
            self.assertTrue([name for name in netlist.NETS
                             if net.match(name)], rule["id"])
            for key in ("source_pad_regex", "load_pad_regex"):
                pattern = re.compile(rule[key])
                self.assertTrue([pin for pin in mapping
                                 if pattern.match(pin)],
                                "%s: %s" % (rule["id"], key))


class Board(unittest.TestCase):
    def test_the_board_in_the_tree_is_the_routed_one(self):
        """The tree carries the board the routing run accepted.

        Everything downstream - the gerbers, the position file, the gates -
        is generated from the file in the tree, so a placement rebuilt after
        routing would ship a board nothing ever routed.
        """
        with open(route.PROVENANCE_PATH, "r", encoding="utf-8") as handle:
            record = json.load(handle)
        self.assertIsNotNone(record["accepted_attempt"])
        self.assertEqual(record["adopted_sha256"],
                         route.digest(layout.BOARD_PATH))

    def test_no_via_stands_on_a_solder_mask_opening(self):
        """A via on an opening cannot be tented, and on a pasted one it
        wicks the joint into its barrel."""
        self.assertEqual(route._vias_on_openings(layout.BOARD_PATH), 0)

    def test_every_part_with_a_footprint_has_a_seed_pose(self):
        placed = layout.seed_placement()
        missing = sorted(reference for reference, part in netlist.PARTS.items()
                         if part["footprint"] and reference not in placed)
        self.assertEqual(missing, [])

    def test_the_locked_set_is_the_board_s_own_contract(self):
        for reference in layout.LOCKED_REFERENCES:
            self.assertIn(reference, netlist.PARTS, reference)

    def test_nothing_stands_in_the_cell_s_own_region(self):
        self.assertEqual(layout.parts_inside_keepout(), [])

    def test_no_two_front_pours_want_the_same_copper(self):
        board, footprints = layout.build(with_copper=False)
        boxes = layout.front_pour_boxes(footprints)
        self.assertEqual(layout._overlapping_pours(boxes), [])
        del board

    def test_every_generated_neck_names_a_pad_the_netlist_holds(self):
        mapping = netlist.pin_to_net()
        for pad_reference, _ in layout.GENERATED_NECKS:
            if pad_reference.startswith("__bar_"):
                self.assertIn(pad_reference[len("__bar_"):],
                              layout.RECEPTACLE_SUPPLY)
                continue
            self.assertIn(pad_reference, mapping, pad_reference)
        for first, second in layout.GENERATED_PAD_LINKS:
            self.assertEqual(mapping[first], mapping[second])


class StaticVerification(unittest.TestCase):
    def test_the_schematic_passes_erc(self):
        report = os.path.join(REPO_ROOT, "out", "erc_test.json")
        os.makedirs(os.path.dirname(report), exist_ok=True)
        completed = subprocess.run(
            ["kicad-cli", "sch", "erc", "--output", report, "--format",
             "json", "--severity-error", "--severity-warning",
             "--exit-code-violations", build.schematic_path()],
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        with open(report, "r", encoding="utf-8") as handle:
            document = json.load(handle)
        violations = [violation for sheet in document.get("sheets", [])
                      for violation in sheet.get("violations", [])]
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
