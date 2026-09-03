"""Circuit scenarios, and what each one is allowed to establish.

Seven questions the schematic can answer before any copper exists.

  * The detector has to tell a 3.0 A advertisement from a 1.5 A one across
    the whole tolerance of the source's pull-up, the board's termination and
    the supply. The requirement report bounds that arithmetic; here the
    dividers are solved, at both extremes at once.
  * With nothing driving it the input switch must be off, and with the
    detector asserting it must be on hard enough for the resistance its
    datasheet quotes to apply. Both are operating points of one gate network.
  * That gate network is also what limits inrush, so how long it takes is a
    requirement rather than an accident.
  * The output enable is a latch, and the shortest press the controller acts
    on has to be long enough to set it.
  * The filter across the button must settle well inside the window the
    controller ignores a press shorter than.
  * A cable has inductance and the board has input capacitance, so plugging a
    live source in rings. What the damper is for is keeping that ring under
    the clamp's stand-off voltage.
  * When a load steps to the rated current the output capacitance is on its
    own until the converter's loop responds; how long it can hold the output
    above the level the converter treats as an overload is the question.

The elements are resistors, capacitors, inductors and ideal sources, because
that is what the scenario contract accepts; every device that is not one of
those is a declared stand-in, and each stand-in says what it replaces.

Three questions are deliberately absent. The converter itself is a switching
regulator with an internal control loop and no vendor model, so its output
current, its efficiency and its start-up time are not simulated - they stay
in the requirement report, where the first is reported as unestablished and
the others as declarations. The cell protection's turn-off is not simulated
either: its speed depends on a gate drive current the datasheet does not
state, and a linear network cannot invent one.
"""
from __future__ import annotations

import json
import os
import sys

from . import netlist, rules

REPO_ROOT = rules.REPO_ROOT
SIM_DIR = os.path.join(REPO_ROOT, "sim")

#: How many time constants a filter is watched for, and the fraction of its
#: starting value it must have fallen to by then. A design target, not a
#: device figure.
FILTER_SETTLED_FRACTION = 0.05

#: How long the gate networks are watched for. The requirement is that the
#: switch has not yet reached the drive its conduction figure is quoted at.
GATE_WINDOW_S = netlist.SWITCH_SLEW_TARGET_S

#: The gate drive the switch's conduction resistance is tabulated at, and
#: which the requirement asks it not to have reached inside the window.
SWITCH_RATED_DRIVE_V = 2.5


def _parameters():
    return rules.load_parameters()


def _ideal(records):
    return {name: {"stands_in_for": detail,
                   "accepted_for_design_decision": True}
            for name, detail in records.items()}


def _measurement(name, kind, node, op=None, value=None, knowledge=None):
    record = {"name": name, "kind": kind, "node": node}
    if op is not None:
        record["assertion"] = {"op": op, "value": value}
    if knowledge is not None:
        record["knowledge"] = knowledge
    return record


def _pulse(v1, v2, period_s, delay_s=None, edge_s=None):
    delay = period_s / 20.0 if delay_s is None else delay_s
    edge = period_s / 1.0e6 if edge_s is None else edge_s
    return {"v1": v1, "v2": v2, "delay_s": delay,
            "rise_s": edge, "fall_s": edge,
            "width_s": period_s / 2.0, "period_s": period_s}


# ---------------------------------------------------------------------------

def advertisement_scenario(parameters):
    """Both advertisements the detector has to separate, at their extremes.

    Two independent networks in one deck: a 1.5 A source at every tolerance
    that raises what this board reads, and a 3.0 A source at every tolerance
    that lowers it. The reference the two are compared against is the third
    network.
    """
    termination_high = rules._resistor_max(parameters, "R1")
    termination_low = rules._resistor_min(parameters, "R1")
    weak = netlist.CC_PULL_UP_FORMS["1.5A"]
    strong = netlist.CC_PULL_UP_FORMS["3.0A"]
    reference = rules._by_mpn(parameters, "TLV431AIDBZR")["reference"]
    comparator = rules._by_mpn(parameters, "LM393DR2G")["comparator"]
    offset = comparator["offset_voltage_over_temperature_max_v"]["value"]
    return {
        "name": "advertisement_thresholds_at_both_extremes",
        "description": "what this board's termination reads from a 1.5 A "
                       "advertisement at every tolerance that raises the "
                       "reading, and from a 3.0 A advertisement at every "
                       "tolerance that lowers it, against the reference "
                       "they are compared with",
        "elements": [
            {"kind": "vsource_dc", "name": "VHIGH", "nodes": ["hi", "0"],
             "value": netlist.INPUT_SUPPLY["max_v"]},
            {"kind": "resistor", "name": "RPWEAK", "nodes": ["hi", "ccweak"],
             "value": weak["ohm"] * (1.0 - weak["tolerance"])},
            {"kind": "resistor", "name": "RDWEAK",
             "nodes": ["ccweak", "0"], "value": termination_high},
            {"kind": "vsource_dc", "name": "VLOW", "nodes": ["lo", "0"],
             "value": netlist.INPUT_SUPPLY["min_v"]},
            {"kind": "resistor", "name": "RPSTRONG",
             "nodes": ["lo", "ccstrong"],
             "value": strong["ohm"] * (1.0 + strong["tolerance"])},
            {"kind": "resistor", "name": "RDSTRONG",
             "nodes": ["ccstrong", "0"], "value": termination_low},
            {"kind": "vsource_dc", "name": "VSHUNT", "nodes": ["ref", "0"],
             "value": reference["voltage_min_v"]["value"]},
        ],
        "analyses": [{"kind": "op"}],
        "measurements": [
            _measurement("weak_advertisement_below_reference", "op_voltage",
                         "ccweak", "<=",
                         reference["voltage_min_v"]["value"] - offset),
            _measurement("strong_advertisement_above_reference", "op_voltage",
                         "ccstrong", ">=",
                         reference["voltage_max_v"]["value"] + offset),
            _measurement("reference_level", "op_voltage", "ref"),
        ],
        "assumptions": _ideal({
            "VHIGH": "a source at the top of the range the specification "
                     "permits a resistor pull-up to be referenced to",
            "RPWEAK": "a 1.5 A advertisement as the specification's own "
                      "resistor value at the low end of its tolerance, which "
                      "is the value that raises what a sink reads",
            "RDWEAK": "this board's termination at the high end of its "
                      "tolerance, which raises the reading again",
            "VLOW": "a source at the bottom of that range",
            "RPSTRONG": "a 3.0 A advertisement at the high end of its "
                        "tolerance, which lowers what a sink reads",
            "RDSTRONG": "this board's termination at the low end of its "
                        "tolerance, which lowers the reading again",
            "VSHUNT": "the shunt reference as an ideal source at the lowest "
                      "voltage its datasheet permits over temperature; the "
                      "assertions carry the comparator's own offset",
        }),
    }


def input_switch_scenario(parameters):
    """The input switch in both of the states its gate network can hold.

    With the detector not asserting, nothing pulls the gate down and the
    switch must be off. With it asserting, the gate has to reach a drive the
    switch's conduction figure is quoted at.
    """
    supply = netlist.INPUT_SUPPLY["min_v"]
    comparator = rules._by_mpn(parameters, "LM393DR2G")["comparator"]
    switch = rules._by_mpn(parameters, "AO3415A")["fet"]
    saturation = comparator["output_low_max_v"]["value"]
    sink = 0.004
    return {
        "name": "input_switch_gate_in_both_detector_states",
        "description": "the input switch's gate with the detector open and "
                       "with it asserting, at the lowest input the board "
                       "accepts",
        "elements": [
            {"kind": "vsource_dc", "name": "VBUS", "nodes": ["bus", "0"],
             "value": supply},
            {"kind": "resistor", "name": "RUPOFF", "nodes": ["bus", "goff"],
             "value": rules._resistor_max(parameters, "R5")},
            {"kind": "resistor", "name": "RSEROFF", "nodes": ["goff", "open"],
             "value": rules._resistor_max(parameters, "R6")},
            {"kind": "resistor", "name": "RLEAKOFF", "nodes": ["open", "0"],
             "value": supply / comparator[
                 "input_bias_current_over_temperature_max_a"]["value"]},
            {"kind": "resistor", "name": "RUPON", "nodes": ["bus", "gon"],
             "value": rules._resistor_min(parameters, "R5")},
            {"kind": "resistor", "name": "RSERON", "nodes": ["gon", "sat"],
             "value": rules._resistor_min(parameters, "R6")},
            {"kind": "resistor", "name": "RSAT", "nodes": ["sat", "0"],
             "value": saturation / sink},
        ],
        "analyses": [{"kind": "op"}],
        "measurements": [
            _measurement("gate_with_detector_open", "op_voltage", "goff",
                         ">=", supply - switch["vgs_threshold_max_v"]["value"]),
            _measurement("gate_with_detector_asserting", "op_voltage", "gon",
                         "<=", supply - SWITCH_RATED_DRIVE_V),
        ],
        "assumptions": _ideal({
            "VBUS": "the source at the bottom of the Type-C range, as an "
                    "ideal source with no output impedance of its own",
            "RUPOFF": "the gate pull-up at the high end of its tolerance",
            "RSEROFF": "the series element at the high end of its tolerance",
            "RLEAKOFF": "the comparator's open output as the resistance that "
                        "carries its highest stated input current from the "
                        "supply; the datasheet's output leakage is smaller "
                        "still, so this overstates what the open output can "
                        "pull down",
            "RUPON": "the gate pull-up at the low end of its tolerance, "
                     "which is the value that holds the gate highest when "
                     "the detector is pulling it down",
            "RSERON": "the series element at the low end of its tolerance",
            "RSAT": "the comparator's asserting output as the resistance "
                    "that produces its highest stated saturation voltage at "
                    "the current the datasheet states that voltage for; the "
                    "gate network draws far less, so the real output sits "
                    "lower",
        }),
    }


def gate_slew_scenario(parameters):
    """How long the input switch's gate takes to reach a conducting drive.

    The gate network is what limits inrush when a source is accepted, so the
    requirement is that it is slow, not that it is fast.
    """
    supply = netlist.INPUT_SUPPLY["max_v"]
    comparator = rules._by_mpn(parameters, "LM393DR2G")["comparator"]
    saturation = comparator["output_low_max_v"]["value"]
    return {
        "name": "input_switch_gate_slew_on_acceptance",
        "description": "the input switch's gate from the instant the "
                       "detector asserts, watched for the time the design "
                       "requires the switch to take",
        "elements": [
            {"kind": "vsource_dc", "name": "VBUS", "nodes": ["bus", "0"],
             "value": supply},
            {"kind": "resistor", "name": "RUP", "nodes": ["bus", "gate"],
             "value": rules._resistor_min(parameters, "R5")},
            {"kind": "capacitor", "name": "CGATE", "nodes": ["bus", "gate"],
             "value": rules._capacitance_low(parameters, "C3")},
            {"kind": "resistor", "name": "RSER", "nodes": ["gate", "out"],
             "value": rules._resistor_min(parameters, "R6")},
            {"kind": "vsource_pulse", "name": "ASSERT", "nodes": ["out", "0"],
             "pulse": _pulse(supply, saturation, 4.0 * GATE_WINDOW_S,
                             delay_s=GATE_WINDOW_S / 100.0,
                             edge_s=GATE_WINDOW_S / 1000.0)},
        ],
        "analyses": [{"kind": "tran", "step_s": GATE_WINDOW_S / 2000.0,
                      "stop_s": GATE_WINDOW_S}],
        "measurements": [
            _measurement("gate_at_the_slew_target", "tran_final_voltage",
                         "gate", ">=", supply - SWITCH_RATED_DRIVE_V),
            _measurement("gate_lowest_inside_the_window", "tran_min_voltage",
                         "gate"),
        ],
        "assumptions": _ideal({
            "VBUS": "the source at the top of the Type-C range, which is the "
                    "case that moves the gate furthest and so fastest",
            "RUP": "the gate pull-up at the low end of its tolerance",
            "CGATE": "the gate capacitor at the low end of its tolerance and "
                     "retaining only the declared fraction of that under "
                     "bias, which is the case that slews fastest",
            "RSER": "the series element at the low end of its tolerance",
            "ASSERT": "the comparator's output going from open to its "
                      "highest stated saturation voltage in a step; the real "
                      "output takes a finite time, which only lengthens this",
        }),
    }


def latch_set_scenario(parameters):
    """The shortest press the controller acts on, setting the enable latch.

    A press shorter than the controller's own window is ignored, so the
    latch has to be set by one no longer than that.
    """
    latch = rules._by_mpn(parameters, "AO3400A")["fet"]
    threshold = latch["vgs_threshold_max_v"]["value"]
    cell = netlist.CELL["board_floor_v"]
    setter = rules._by_mpn(parameters, "AO3401A")["fet"]
    window = netlist.KEY_IGNORE_BELOW_S
    return {
        "name": "enable_latch_set_by_the_shortest_recognised_press",
        "description": "the enable latch's gate over one press of the "
                       "shortest duration the controller does not ignore, "
                       "at the lowest cell voltage",
        "elements": [
            {"kind": "vsource_pulse", "name": "PRESS", "nodes": ["src", "0"],
             "pulse": _pulse(0.0, cell, 4.0 * window,
                             delay_s=window / 100.0,
                             edge_s=window / 1000.0)},
            {"kind": "resistor", "name": "RSETFET", "nodes": ["src", "drain"],
             "value": setter["rds_on_ohm"]["2.5"]["value"]},
            {"kind": "resistor", "name": "RSET", "nodes": ["drain", "set"],
             "value": rules._resistor_max(parameters, "R13")},
            {"kind": "resistor", "name": "RHOLD", "nodes": ["set", "0"],
             "value": rules._resistor_min(parameters, "R14")},
            {"kind": "capacitor", "name": "CHOLD", "nodes": ["set", "0"],
             "value": rules._capacitance_low(parameters, "C15")},
        ],
        "analyses": [{"kind": "tran", "step_s": window / 4000.0,
                      "stop_s": window}],
        "measurements": [
            _measurement("latch_gate_at_the_end_of_the_press",
                         "tran_final_voltage", "set", ">=", threshold),
            _measurement("latch_gate_peak", "tran_max_voltage", "set"),
        ],
        "assumptions": _ideal({
            "PRESS": "the button and the device it drives as an ideal switch "
                     "onto the cell rail at the lowest voltage the converter "
                     "operates from",
            "RSETFET": "that device as its conduction resistance at the "
                       "weakest gate drive its datasheet tabulates",
            "RSET": "the latch's series element at the high end of its "
                    "tolerance",
            "RHOLD": "the latch's hold resistor at the low end of its "
                     "tolerance, which is the value that charges the node "
                     "to the lowest level",
            "CHOLD": "the hold capacitor at the low end of its tolerance and "
                     "retaining only the declared fraction of that under "
                     "bias; less capacitance charges faster, so this is the "
                     "optimistic direction for this measurement and the "
                     "pessimistic one for the hold time, which is claimed "
                     "analytically instead",
        }),
    }


def button_filter_scenario(parameters):
    """The filter across the button, against the window it must fit inside."""
    cell = netlist.CELL["protection_ceiling_v"]
    window = netlist.KEY_IGNORE_BELOW_S
    return {
        "name": "button_filter_settles_inside_the_ignore_window",
        "description": "the controller's button node when the button "
                       "closes, watched for the window the controller "
                       "ignores a press shorter than",
        "elements": [
            {"kind": "vsource_pulse", "name": "BUTTON", "nodes": ["btn", "0"],
             "pulse": _pulse(cell, 0.0, 4.0 * window,
                             delay_s=window / 100.0,
                             edge_s=window / 1000.0)},
            {"kind": "resistor", "name": "RSERIES", "nodes": ["btn", "key"],
             "value": rules._resistor_max(parameters, "R11")},
            {"kind": "capacitor", "name": "CFILTER", "nodes": ["key", "0"],
             "value": rules._capacitance_farads(parameters, "C14")},
        ],
        "analyses": [{"kind": "tran", "step_s": window / 4000.0,
                      "stop_s": window}],
        "measurements": [
            _measurement("button_node_at_the_ignore_window",
                         "tran_final_voltage", "key", "<=",
                         FILTER_SETTLED_FRACTION * cell),
        ],
        "assumptions": _ideal({
            "BUTTON": "the button as an ideal switch, and the node it pulls "
                      "down as starting at the top of the cell rail",
            "RSERIES": "the series element at the high end of its tolerance",
            "CFILTER": "the filter capacitor at its nominal value with no "
                       "derating, which is the largest it can be and so the "
                       "slowest this settles",
        }),
    }


def hot_plug_scenario(parameters):
    """Plugging a live source in, and what the damper does about the ring.

    A cable has inductance and the board has capacitance; the two ring when
    the source is connected. The clamp on that conductor is the part that
    decides how much ring is acceptable.
    """
    supply = netlist.INPUT_SUPPLY["max_v"]
    clamp = rules._by_mpn(parameters, "TPD1E10B06DPYR")["clamp"]
    window = 40.0e-6
    detector = 1.0 / (1.0 / rules._resistor_min(parameters, "R4")
                      + 1.0 / (rules._resistor_min(parameters, "R5")
                               + rules._resistor_min(parameters, "R6")))
    return {
        "name": "hot_plug_ring_at_the_input_receptacle",
        "description": "a live source connected through a cable's "
                       "inductance to the board's input capacitance, with "
                       "the damper the design carries",
        "elements": [
            {"kind": "vsource_pulse", "name": "SOURCE", "nodes": ["src", "0"],
             "pulse": _pulse(0.0, supply, 4.0 * window,
                             delay_s=window / 20.0, edge_s=window / 4000.0)},
            {"kind": "inductor", "name": "LCABLE", "nodes": ["src", "bus"],
             "value": netlist.CABLE_INDUCTANCE_H},
            {"kind": "capacitor", "name": "CBUS", "nodes": ["bus", "0"],
             "value": rules._capacitance_low(parameters, "C1")},
            {"kind": "resistor", "name": "RDAMP", "nodes": ["bus", "damp"],
             "value": rules._resistor_max(parameters, "R3")},
            {"kind": "capacitor", "name": "CDAMP", "nodes": ["damp", "0"],
             "value": rules._capacitance_low(parameters, "C4")},
            {"kind": "resistor", "name": "RDETECT", "nodes": ["bus", "0"],
             "value": detector},
        ],
        "analyses": [{"kind": "tran", "step_s": window / 20000.0,
                      "stop_s": window}],
        "measurements": [
            _measurement("input_peak", "tran_max_voltage", "bus", "<=",
                         clamp["breakdown_min_v"]["value"]),
            _measurement("input_settled", "tran_final_voltage", "bus"),
        ],
        "assumptions": _ideal({
            "SOURCE": "the source as an ideal step to the top of the Type-C "
                      "range, which is the largest step a compliant source "
                      "can present",
            "LCABLE": "the cable and the connector as one inductance, a "
                      "declared budget rather than a measurement",
            "CBUS": "the input capacitance at the low end of its tolerance "
                    "and retaining only the declared fraction of that under "
                    "bias, which is the case that rings highest",
            "CDAMP": "the damper's capacitance on the same basis",
            "RDAMP": "the damper's resistance at the high end of its "
                     "tolerance",
            "RDETECT": "everything the detector draws from the input, as one "
                       "resistance; the switch is open at this instant so "
                       "the charger is not connected",
        }),
    }


def output_hold_scenario(parameters):
    """A load step to the rated current, with the converter contributing
    nothing.

    The converter has no vendor model and its datasheet states no loop
    response time, so the question this asks is the one that does not need
    one: how long the output capacitance alone holds the port above the
    level the converter treats as an overload.
    """
    controller = rules._by_mpn(parameters, "IP5306")
    floor = netlist.CONVERTER_OVERLOAD_FLOOR_V
    capacitance = sum(rules._capacitance_low(parameters, reference)
                      for reference in ("C10", "C11", "C12", "C13"))
    start = controller["boost"]["output_voltage_typ_v"]["value"]
    window = netlist.CONVERTER_RESPONSE_BUDGET_S
    load = start / netlist.RATED_OUTPUT_A
    return {
        "name": "output_holds_through_the_converter_response_budget",
        "description": "the output capacitance alone carrying a step to the "
                       "rated current for the time this design allows the "
                       "converter's loop to respond in",
        "elements": [
            {"kind": "vsource_dc", "name": "VSTART", "nodes": ["src", "0"],
             "value": start},
            {"kind": "resistor", "name": "RCHARGE", "nodes": ["src", "out"],
             "value": 10.0},
            {"kind": "capacitor", "name": "COUT", "nodes": ["out", "0"],
             "value": capacitance},
            {"kind": "resistor", "name": "RLOAD", "nodes": ["out", "step"],
             "value": load},
            {"kind": "vsource_pulse", "name": "STEP", "nodes": ["step", "0"],
             "pulse": _pulse(start, 0.0, 2000.0 * window,
                             delay_s=300.0 * window,
                             edge_s=window / 1000.0)},
        ],
        "analyses": [{"kind": "tran", "step_s": window / 200.0,
                      "stop_s": 301.0 * window}],
        "measurements": [
            _measurement("output_minimum", "tran_min_voltage", "out", ">=",
                         floor),
            _measurement("output_at_the_response_budget",
                         "tran_final_voltage", "out"),
        ],
        "assumptions": _ideal({
            "VSTART": "the converter's regulated output as an ideal source "
                      "at its typical value, which is all the datasheet "
                      "states",
            "RCHARGE": "the path that brings the capacitance up to the "
                       "regulated value before the step. During the step it "
                       "supplies under four percent of the load, so the "
                       "capacitance answers the step essentially alone, "
                       "which is the point",
            "COUT": "the output capacitance at the low end of its tolerance "
                    "and retaining only the declared fraction of that under "
                    "bias",
            "RLOAD": "the load as a resistance drawing the rated current at "
                     "the regulated output",
            "STEP": "the load appearing in a step, as an ideal switch",
        }),
    }


#: Which registered requirement each asserted measurement establishes.
#: The requirement register is joined to the claim set and to this mapping
#: together, so a requirement whose only verification is a simulation is
#: still registered, and a simulated assertion that answers no registered
#: requirement is an error.
MEASUREMENT_REQUIREMENTS = {
    "weak_advertisement_below_reference":
        "threshold_above_1_5A_advertisement",
    "strong_advertisement_above_reference":
        "threshold_below_3_0A_advertisement",
    "gate_with_detector_open": "output_off_until_a_press",
    "gate_with_detector_asserting":
        "charger_input_above_undervoltage_lockout",
    "gate_at_the_slew_target": "switch_gate_slew_above_target",
    "latch_gate_at_the_end_of_the_press":
        "latch_set_level_above_threshold",
    "button_node_at_the_ignore_window":
        "button_filter_below_ignore_window",
    "input_peak": "input_ring_below_clamp_breakdown",
    "output_minimum": "output_holds_through_response_budget",
}


def asserted_measurements():
    """Every measurement in every scenario that carries an assertion."""
    found = set()
    for document in documents().values():
        for measurement in document["measurements"]:
            if "assertion" in measurement:
                found.add(measurement["name"])
    return found


SCENARIOS = (
    ("pre_layout_advertisement.json", advertisement_scenario),
    ("pre_layout_input_switch.json", input_switch_scenario),
    ("pre_layout_gate_slew.json", gate_slew_scenario),
    ("pre_layout_latch_set.json", latch_set_scenario),
    ("pre_layout_button_filter.json", button_filter_scenario),
    ("pre_layout_hot_plug.json", hot_plug_scenario),
    ("pre_layout_output_hold.json", output_hold_scenario),
)


def documents():
    parameters = _parameters()
    return {name: builder(parameters) for name, builder in SCENARIOS}


def _write(path, document):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def write():
    return [_write(os.path.join(SIM_DIR, name), document)
            for name, document in sorted(documents().items())]


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
