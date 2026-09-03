"""What kind of statement each requirement is, and how it is established.

A claim carries a number, an evidence class and a verdict. What it does not
carry is where the requirement it is judged against came from, and that is a
distinction worth keeping: a board can fail because the brief asked for the
wrong thing, because this design derived the wrong requirement from it,
because a threshold was a choice nobody wrote down, or because the
implementation is simply wrong. Collapsing all four into one source string
makes those failures look identical.

So every requirement name a claim uses is registered here with:

  * its kind - stated by the brief, derived by this design, chosen by this
    design, or assumed pending evidence;
  * what it was derived from, for the derived ones;
  * why, for the ones a reader would otherwise have to guess at;
  * the alternatives, for the ones that were a choice;
  * the verification methods that establish it, and whether a physical test
    is still required.

The register is joined to the claim set by requirement name, and the join is
total in both directions: a claim judged against an unregistered requirement,
and a registered requirement nothing is judged against, are both errors.
"""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PATH = os.path.join(REPO_ROOT, "constraints", "requirements.json")

BRIEF = "BRIEF.md"

# ---------------------------------------------------------------------------
# statement kinds

USER = "user_requirement"
DERIVED = "derived_requirement"
ASSUMPTION = "assumption"
DECISION = "design_decision"
KINDS = (USER, DERIVED, ASSUMPTION, DECISION)

# ---------------------------------------------------------------------------
# verification methods

STATIC = "STATIC"
GEOMETRY = "GEOMETRY"
ANALYTIC = "ANALYTIC"
CIRCUIT_SIM = "CIRCUIT_SIM"
EXTRACTED = "EXTRACTED"
THERMAL_SIM = "THERMAL_SIM"
MANUFACTURING_CHECK = "MANUFACTURING_CHECK"
PHYSICAL_TEST = "PHYSICAL_TEST"
DOCUMENTATION = "DOCUMENTATION"

METHODS = (STATIC, GEOMETRY, ANALYTIC, CIRCUIT_SIM, EXTRACTED, THERMAL_SIM,
           MANUFACTURING_CHECK, PHYSICAL_TEST, DOCUMENTATION)

#: Brief clauses, as anchors a reader can follow.
FUNCTION = BRIEF + "#functional-requirements"
POWER = BRIEF + "#power-and-rails"
CHARGING = BRIEF + "#charging-and-battery-protection"
INTERFACE = BRIEF + "#interfaces-indication-and-control"
LAYOUT = BRIEF + "#layout-thermal-and-mechanical"
BRING_UP = BRIEF + "#test-and-bring-up"
OPEN = BRIEF + "#open-choices"


def _user(statement, clause, verified_by, physical_test=False):
    return {"kind": USER, "statement": statement, "derived_from": (clause,),
            "origin": clause, "verified_by": verified_by,
            "physical_test_still_required": physical_test}


def _derived(statement, clause, origin, rationale, verified_by,
             physical_test=False):
    return {"kind": DERIVED, "statement": statement,
            "derived_from": (clause,) if isinstance(clause, str)
            else tuple(clause),
            "origin": origin, "rationale": rationale,
            "verified_by": verified_by,
            "physical_test_still_required": physical_test}


def _decision(statement, rationale, alternatives, verified_by,
              physical_test=False):
    return {"kind": DECISION, "statement": statement, "rationale": rationale,
            "alternatives_considered": tuple(alternatives),
            "verified_by": verified_by,
            "physical_test_still_required": physical_test}


def _assumption(statement, reason, invalidated_by, verified_by,
                physical_test=False):
    return {"kind": ASSUMPTION, "statement": statement, "reason": reason,
            "revisable": True, "invalidated_by": invalidated_by,
            "verified_by": verified_by,
            "physical_test_still_required": physical_test}


# ---------------------------------------------------------------------------
# the requirements every claim is judged against

REGISTER = {

    # --- the input port ----------------------------------------------------

    "sink_termination_within_specification": _derived(
        "each CC conductor of the input port is terminated by a resistance "
        "inside the tolerance the Type-C specification allows a sink that "
        "reads the source's current advertisement",
        INTERFACE, "usb_type_c",
        "the brief says the input 'presents the sink CC terminations Type-C "
        "requires'. Which termination that is depends on whether the sink "
        "reads the advertisement: this one does, and the specification's "
        "table permits +/-10% for that case and +/-20% for a sink that does "
        "not",
        (STATIC, ANALYTIC)),

    "both_orientations_terminated": _user(
        "the input works with the plug either way round",
        INTERFACE, (STATIC,)),

    "threshold_above_1_5A_advertisement": _derived(
        "the detector's threshold sits above every CC voltage a source "
        "advertising 1.5 A can produce at this sink",
        [INTERFACE, CHARGING], "usb_type_c",
        "the board takes more current than a 1.5 A source offers, so it must "
        "not mistake that advertisement for the 3.0 A one. The specification "
        "tabulates the sink-side voltage bands directly, and the bands - not "
        "the pull-up tolerances - are what a threshold has to clear",
        (STATIC, ANALYTIC, CIRCUIT_SIM)),

    "threshold_below_3_0A_advertisement": _derived(
        "the detector's threshold sits below every CC voltage a source "
        "advertising 3.0 A can produce at this sink",
        [INTERFACE, CHARGING], "usb_type_c",
        "a threshold above the 3.0 A band would reject every source and the "
        "board would never charge; the band's lower edge is what it has to "
        "stay under",
        (STATIC, ANALYTIC, CIRCUIT_SIM)),

    "reference_bias_above_regulation_minimum": _derived(
        "the shunt reference carries at least the cathode current it needs "
        "to regulate, at the lowest input the board accepts",
        INTERFACE, "tlv431_ti",
        "the threshold is only as good as the reference behind it, and a "
        "shunt reference below its minimum cathode current is not "
        "regulating at all",
        (ANALYTIC, CIRCUIT_SIM)),

    "reference_bias_below_maximum": _derived(
        "the shunt reference's cathode current stays inside its rating at "
        "the highest input the board accepts",
        INTERFACE, "tlv431_ti", "the same bias resistor sets both ends",
        (ANALYTIC,)),

    "reference_load_capacitance_within_stable_range": _derived(
        "the capacitance across the reference is inside the range the "
        "datasheet states the device is stable into",
        INTERFACE, "tlv431_ti",
        "a shunt reference is a feedback loop; the datasheet's stability "
        "boundary is stated for the cathode-tied-to-reference connection "
        "this board uses, so it is a figure rather than a judgement",
        (STATIC, DOCUMENTATION)),

    "comparator_input_within_common_mode_range": _derived(
        "the highest CC voltage the detector must resolve stays inside the "
        "comparator's input common-mode range at the lowest supply",
        INTERFACE, "lm393_onsemi",
        "outside the common-mode range a comparator's output is not defined "
        "by its inputs, so the threshold claim would rest on nothing",
        (ANALYTIC,)),

    "input_current_below_advertisement": _user(
        "the board draws no more from the source than the source advertises",
        POWER, (ANALYTIC, STATIC), physical_test=True),

    "rejected_source_current_below_default": _derived(
        "with the advertisement below what the board requires, the current "
        "it takes from the source stays under the smallest advertisement a "
        "Type-C source can make",
        POWER, "usb_type_c",
        "the board answers a weak source by not charging, but the detector "
        "itself runs from the source; what it draws has to be inside the "
        "default advertisement or the refusal is not a refusal",
        (ANALYTIC, CIRCUIT_SIM)),

    "charger_input_above_undervoltage_lockout": _derived(
        "the charger's input stays above the controller's undervoltage "
        "lockout with the input switch conducting its worst-case current at "
        "the bottom of the declared source range",
        POWER, "ip5306_injoinic",
        "the brief requires operation over the whole vSafe5V range; a series "
        "switch drops voltage, and below the lockout the charger stops",
        (ANALYTIC, CIRCUIT_SIM)),

    # --- the cell and its protection ---------------------------------------

    "protection_does_not_trip_at_rated_output": _derived(
        "the cell protection's lowest over-current trip current is above the "
        "highest instantaneous cell current the rated output produces",
        [POWER, CHARGING], "dw01a_puolop",
        "the brief makes cell-side current at rated output and minimum cell "
        "voltage the figure that sets over-current margin. The protection "
        "senses a voltage across the switch, so its trip current is set by "
        "the switch's resistance, and a trip during normal operation is a "
        "functional failure rather than a safety action",
        (ANALYTIC,)),

    "protection_overcharge_above_charge_target": _derived(
        "the protection's lowest over-charge threshold is above the voltage "
        "the charger terminates at",
        CHARGING, "dw01a_puolop",
        "the two devices are independent, so the protection must sit outside "
        "the charger's own regulation or it will cut a normal charge short",
        (ANALYTIC,)),

    "protection_overdischarge_below_operating_floor": _derived(
        "the protection's highest over-discharge threshold is below the "
        "lowest cell voltage the converter operates at",
        CHARGING, ["dw01a_puolop", "ip5306_injoinic"],
        "the protection is a backstop for a fault, not the working cut-off; "
        "if it tripped first the pack would need a charger to recover from "
        "an ordinary discharge",
        (ANALYTIC,)),

    "cell_rail_parts_rated_above_protection_ceiling": _derived(
        "every part on the cell rail is rated above the highest voltage the "
        "protection device permits the cell to reach",
        POWER, "dw01a_puolop",
        "the brief requires parts on the battery rail to be rated above its "
        "maximum. That maximum is not the charger's target: it is the "
        "highest voltage that can stand on the rail before something "
        "intervenes, which is the protection's own over-charge threshold at "
        "the top of its tolerance",
        (STATIC, ANALYTIC)),

    "protection_switch_within_current_rating": _derived(
        "each protection switch package carries less than its rated "
        "continuous drain current at the worst-case cell current",
        POWER, "ao8810_aos",
        "the packages share the cell current; the share, not the total, is "
        "what each package is rated against",
        (ANALYTIC,)),

    "protection_switch_junction_below_maximum": _derived(
        "the protection switch's junction stays below its rated maximum at "
        "the worst-case cell current and the declared maximum ambient",
        [POWER, LAYOUT], "ao8810_aos",
        "conduction loss in the switch is the largest dissipation on the "
        "cell rail and the package is small",
        (ANALYTIC, THERMAL_SIM), physical_test=True),

    # --- the converter and the output --------------------------------------

    "inductor_peak_below_saturation": _derived(
        "the peak inductor current at the rated output and the lowest cell "
        "voltage stays below the inductor's saturation current",
        [POWER, LAYOUT], "swpa8040_sunlord",
        "the brief makes cell-side current the figure that sizes magnetics. "
        "For an inductor that figure is the peak, not the average: ripple at "
        "the declared switching frequency is a large fraction of the average "
        "at this inductance",
        (ANALYTIC,)),

    "inductor_rms_below_heat_rating": _derived(
        "the RMS inductor current at the rated output stays below the "
        "inductor's heat rating current",
        [POWER, LAYOUT], "swpa8040_sunlord",
        "saturation and self-heating are separate limits and the smaller one "
        "decides",
        (ANALYTIC,)),

    "output_switch_junction_below_maximum": _derived(
        "the output enable switch's junction stays below its rated maximum "
        "at the rated output and the declared maximum ambient",
        LAYOUT, "ao3415a_aos",
        "the enable switch carries the whole output current in a small "
        "package",
        (ANALYTIC, THERMAL_SIM), physical_test=True),

    "input_switch_junction_below_maximum": _derived(
        "the input switch's junction stays below its rated maximum at the "
        "highest input current the controller is specified for and the "
        "declared maximum ambient",
        LAYOUT, "ao3415a_aos",
        "the input switch carries the whole charge current in a small "
        "package",
        (ANALYTIC, THERMAL_SIM), physical_test=True),

    "port_voltage_above_source_minimum": _derived(
        "the voltage at the output port at the rated current stays above the "
        "lowest a Type-C source may present",
        [FUNCTION, INTERFACE], "usb_type_c",
        "the board is a source at that port; the specification's pull-up "
        "table is stated for a supply of 4.75 V to 5.5 V, so an output that "
        "sagged below 4.75 V would invalidate the advertisement as well as "
        "the rating",
        (ANALYTIC,), physical_test=True),

    "output_advertisement_lands_in_3_0A_band": _derived(
        "a sink attached to the output port reads a CC voltage inside the "
        "band the specification defines for a 3.0 A advertisement",
        INTERFACE, "usb_type_c",
        "the output port advertises by presenting a pull-up, and what a sink "
        "reads is the divider between that pull-up and the sink's own "
        "termination; the advertisement is only made if the result lands in "
        "the band",
        (ANALYTIC,)),

    "input_ring_below_clamp_breakdown": _derived(
        "connecting a live source through a cable's inductance does not ring "
        "the input above the clamp's breakdown voltage",
        [INTERFACE, LAYOUT], "tpd1e10b06_ti",
        "a step through a series inductance into a capacitance overshoots, "
        "and plugging a charger in is that step. The clamp on that conductor "
        "is there for electrostatic discharge, not for an event that happens "
        "every time the board is used, so the ring has to stay below the "
        "voltage at which the clamp starts to conduct",
        (CIRCUIT_SIM,), physical_test=True),

    "output_holds_through_response_budget": _derived(
        "the output capacitance alone holds the port above the level the "
        "converter treats as an overload, for as long as this design allows "
        "the converter's loop to take to answer a step to the rated current",
        [FUNCTION, POWER], "ip5306_injoinic",
        "the converter has no vendor model and its datasheet states no loop "
        "response time, so the output capacitance is sized against a "
        "declared budget instead. The level the dip has to stay above is not "
        "declared: it is the one the converter's own load-overcurrent "
        "detector uses",
        (ANALYTIC, CIRCUIT_SIM), physical_test=True),

    "rated_output_current_supported": _user(
        "the board delivers at least the rated current at 5 V across the "
        "whole usable cell voltage range",
        FUNCTION, (ANALYTIC,), physical_test=True),

    "converter_junction_below_thermal_shutdown": _derived(
        "the converter's junction stays below its thermal shutdown "
        "threshold delivering the rated output in still air at room ambient",
        LAYOUT, "ip5306_injoinic",
        "the brief requires the rated output sustained in still air with no "
        "thermal foldback; foldback for this device is its own thermal "
        "shutdown, so the requirement is a junction temperature below that "
        "threshold rather than a generic derating",
        (ANALYTIC, THERMAL_SIM), physical_test=True),

    # --- the output enable -------------------------------------------------

    "output_off_until_a_press": _user(
        "the output is off when a cell is attached and after a protection "
        "event, and only a button press enables it",
        FUNCTION, (STATIC, ANALYTIC, CIRCUIT_SIM), physical_test=True),

    "latch_set_level_above_threshold": _derived(
        "a held button drives the latch's gate above the switching device's "
        "highest gate threshold, at the lowest cell voltage",
        FUNCTION, "ao3400a_aos",
        "the enable is a latch and the press is what sets it; below the gate "
        "threshold the press does nothing",
        (ANALYTIC, CIRCUIT_SIM)),

    "latch_hold_level_above_threshold": _derived(
        "the latch's own feedback holds its gate above the switching "
        "device's highest gate threshold once the output is up",
        FUNCTION, "ao3400a_aos",
        "without the feedback the latch would release the moment the button "
        "did",
        (ANALYTIC, CIRCUIT_SIM)),

    "latch_hold_time_above_target": _derived(
        "the latch holds its set state for longer than the declared "
        "converter start-up allowance with no feedback",
        FUNCTION, "ip5306_injoinic",
        "the feedback comes from the output, and at the instant of the press "
        "the output is not up yet. The controller's datasheet states no "
        "start-up time, so the latch has to bridge an interval this design "
        "declares rather than one a document gives",
        (ANALYTIC, CIRCUIT_SIM)),

    "switch_gate_within_rating": _derived(
        "neither switch's gate-source voltage exceeds its rating in any "
        "state the board can reach",
        POWER, ["ao3415a_aos", "ao3400a_aos", "ao3401a_aos"],
        "both switches are driven between a rail and ground rather than "
        "through a clamp, so the rail's own maximum is the gate stress",
        (ANALYTIC,)),

    "switch_gate_slew_above_target": _derived(
        "each switch's gate network takes at least the declared time to "
        "turn the switch on",
        [POWER, LAYOUT], "ao3415a_aos",
        "a switch that closes instantly charges the capacitance behind it "
        "from the capacitance in front of it; the brief's inrush and "
        "high-current-loop requirements are easier to meet if the switch is "
        "the thing that limits it",
        (ANALYTIC, CIRCUIT_SIM)),

    # --- standby -----------------------------------------------------------

    "standby_current_below_self_discharge": _user(
        "the current the board takes from the cell with the output off and "
        "no source attached is small against the cell's own self-discharge",
        POWER, (ANALYTIC,), physical_test=True),

    "latch_hold_capacitor_rated_above_set_level": _derived(
        "the latch's hold capacitor is rated above the highest voltage its "
        "feedback can put on it",
        FUNCTION, "mlcc_samsung_cl",
        "the feedback divider is fed from the converter output, which is "
        "higher than the cell rail every other part of the latch sees",
        (STATIC,)),

    # --- the button and the indicators -------------------------------------

    "button_current_below_contact_rating": _derived(
        "the current through the button's contacts stays below its rating",
        INTERFACE, "ts1187a_xkb",
        "the switch is rated for a signal contact, not a supply one, and the "
        "board pulls its node up",
        (ANALYTIC,)),

    "button_filter_below_ignore_window": _derived(
        "the filter across the button settles well inside the window the "
        "controller ignores a press shorter than",
        INTERFACE, "ip5306_injoinic",
        "the brief requires the button debounced. The controller debounces "
        "in time; the filter exists for noise and static, and must not eat "
        "the window that debounce depends on",
        (ANALYTIC, CIRCUIT_SIM)),

    "no_floating_node": _user(
        "the button presents no floating node",
        INTERFACE, (STATIC,)),

    "indicator_current_within_rating": _derived(
        "every indicator carries less than its rated forward current",
        INTERFACE, ["kt0603g_kento", "kt0603r_kento", "ip5306_injoinic"],
        "the state-of-charge indicators are driven by a current source "
        "inside the controller and the fault indicator by a series resistor, "
        "so the two are bounded differently",
        (ANALYTIC,)),

    "indicator_reverse_within_rating": _derived(
        "an indicator held off by the drive that lights its pair sees less "
        "reverse voltage than it is rated for",
        INTERFACE, "kt0603g_kento",
        "four indicators are driven from three pins as antiparallel pairs, "
        "so lighting one reverse-biases the other by that one's forward "
        "voltage",
        (ANALYTIC,)),

    # --- ratings and structure ---------------------------------------------

    "parts_rated_above_rail_maximum": _derived(
        "every part on a 5 V rail is rated above the highest voltage that "
        "rail can reach",
        POWER, "usb_type_c",
        "the brief bounds the input by the Type-C vSafe5V range; the top of "
        "that range is what parts on the input side see",
        (STATIC, ANALYTIC)),

    "clamp_working_voltage_above_rail": _derived(
        "every clamp's reverse stand-off voltage is at least the highest "
        "steady voltage on the conductor it protects",
        INTERFACE, "tpd1e10b06_ti",
        "a clamp below the rail conducts continuously, which is a fault "
        "rather than protection",
        (STATIC, ANALYTIC)),

    "esd_coverage_complete": _user(
        "every conductor that enters the board at a user-accessible "
        "connector is clamped",
        INTERFACE, (STATIC,), physical_test=True),

    "connector_contract_consistent": _derived(
        "every connector pin carries the net its function names",
        INTERFACE, "usbc_hro",
        "a receptacle that mates mechanically but carries the wrong net on "
        "VBUS or CC is the one mistake the connector itself cannot prevent",
        (STATIC, GEOMETRY)),

    "cell_connector_polarised": _derived(
        "the cell connector is keyed so the cell cannot be fitted reversed",
        CHARGING, "jst_vh",
        "the brief requires a reversed cell to leave the board undamaged. "
        "The protection device's own supply pin sits across the cell, and a "
        "reversed cell drives it below its absolute minimum, so the "
        "reversal is prevented mechanically rather than survived "
        "electrically",
        (STATIC, DOCUMENTATION)),

    "cell_connector_within_current_rating": _derived(
        "the cell connector carries less than its rated current at the "
        "worst-case cell current",
        POWER, "jst_vh",
        "the brief makes cell-side current the figure that sizes conductors, "
        "and the connector is one of them",
        (ANALYTIC,)),

    "port_connector_within_current_rating": _derived(
        "each port carries less than its receptacle's rated current",
        POWER, "usbc_hro",
        "the same figure applies to the receptacles the current enters and "
        "leaves by",
        (ANALYTIC,)),

    "probe_access_complete": _user(
        "every net the brief requires a probe on reaches one",
        BRING_UP, (STATIC,)),

    "kelvin_pairs_present": _user(
        "the cell side, the output and the reference each carry a pair of "
        "probes so current and voltage can be measured separately",
        BRING_UP, (STATIC,)),

    "package_pins_match_land_pattern": _derived(
        "every symbol's pin count equals its land pattern's pad count",
        LAYOUT, "usbc_hro",
        "a simulation and a requirement report can both be right about a "
        "part whose footprint has a pad the schematic never names",
        (STATIC, GEOMETRY)),

    "assembly_within_declared_policy": _derived(
        "the board is assembled the way its declared policy says",
        LAYOUT, "jst_vh",
        "the brief puts the connectors, the button and the indicators on one "
        "face; what that costs at assembly is a count of sides and of hand "
        "operations, and it should be a measurement rather than an intention",
        (STATIC, MANUFACTURING_CHECK)),

    "stock_covers_planned_build": _derived(
        "every part is stocked in at least the quantity the planned build "
        "needs",
        LAYOUT, "jlcpcb_catalogue_snapshot",
        "a design that cannot be built is not finished; the catalogue "
        "snapshot is frozen so this is a statement about a recorded state "
        "rather than about today's web page",
        (DOCUMENTATION,)),

    "conductor_width_for_cell_current": _derived(
        "the conductor width the board declares for its power nets carries "
        "the worst-case cell current inside the declared temperature rise",
        LAYOUT, "conductor_sizing_model",
        "the brief requires conductor cross-sections to meet a stated "
        "temperature-rise limit at worst-case cell-side current. Before "
        "there is copper to measure, the declared net-class width is what "
        "the requirement applies to",
        (ANALYTIC, EXTRACTED), physical_test=True),
}


# ---------------------------------------------------------------------------
# statements no numeric claim is judged against

STATEMENTS = {

    "integrated_controller": _decision(
        "charger, power path, boost converter and state-of-charge indication "
        "are one integrated controller rather than discrete stages",
        "the brief prefers an integrated solution where practical. One "
        "device with one inductor removes the power-path arbitration between "
        "a separate charger and a separate boost, which is the part of this "
        "architecture that is hardest to get right and hardest to verify "
        "from datasheets alone",
        ("a discrete buck charger, a discrete boost converter and a "
         "power-path switch, rejected because the arbitration between them "
         "would be this board's own design and nothing in the datasheets "
         "would establish it",
         "a charger with an I2C-controlled boost, rejected because the "
         "output would then depend on firmware, and the brief requires the "
         "protections to hold with any programmable device unprogrammed"),
        (DOCUMENTATION,)),

    "independent_cell_protection": _decision(
        "cell over-voltage, under-voltage, over-current and short-circuit "
        "protection is a separate analogue device in the cell's negative "
        "leg, not a function of the controller",
        "the brief requires those protections to hold with any programmable "
        "device unpowered or unprogrammed. A protection that shares a die "
        "with the converter shares its failure modes; one that runs from the "
        "cell and switches the cell's own return does not",
        ("relying on the controller's own stated protections, rejected "
         "because they are inside the device whose failure they would have "
         "to survive",
         "a protection device with an external sense resistor, rejected "
         "because the sense resistor would dissipate the cell current "
         "continuously"),
        (STATIC, ANALYTIC)),

    "vias_clear_of_solder_mask_openings": _decision(
        "no via's annulus reaches a pad's solder-mask opening",
        "a via whose annulus reaches an opening cannot be tented or "
        "plugged, so its barrel is open to whatever the assembly puts on "
        "the opening beside it; where that opening is one a paste aperture "
        "fills, the joint's own solder wicks into the barrel and leaves the "
        "joint short of it. The board carries the distance as a rule the "
        "placement searches its stitches against, the search is given the "
        "same figure, and a routed board that still has one is refused, so "
        "it is a property of the board rather than something a review would "
        "have to notice",
        ("allowing a via inside a pad and ordering a filled-and-capped "
         "process, rejected because it prices the whole board for the "
         "handful of vias that wanted it",
         "leaving the contact and relying on the mask to bridge it, "
         "rejected because mask over an annulus that touches an opening is "
         "a sliver rather than a tent, and the fabricator is free to drop "
         "it"),
        (GEOMETRY, MANUFACTURING_CHECK)),

    "advertisement_gated_charging": _decision(
        "the board charges only from a source that advertises 3.0 A, and "
        "takes nothing but its detector's own current from any weaker one",
        "the brief requires the board to draw no more than the source "
        "advertises, and the controller has no input current limit that can "
        "be set from outside. Gating the whole charger input on the "
        "advertisement makes the requirement a property of the hardware "
        "rather than of the controller's behaviour",
        ("drawing the controller's full charge current from any source, "
         "rejected because it violates the brief against every source that "
         "advertises less",
         "a fixed current limiter set to the default advertisement, "
         "rejected because a limiter in constant-current mode drops the "
         "input below the controller's lockout and the pair hiccups",
         "reading the advertisement and selecting between two limits, "
         "rejected as more parts than the added charge rate is worth on a "
         "board whose charge current is an open choice"),
        (STATIC, ANALYTIC, CIRCUIT_SIM)),

    "type_c_output_port": _decision(
        "the output is a Type-C receptacle presenting a source pull-up, and "
        "the board applies VBUS when the user enables the output rather than "
        "when it detects a sink",
        "the rated output current exceeds what a Standard-A receptacle is "
        "rated to carry, and the Type-C receptacle is rated well above it. "
        "The board does not implement Type-C attach detection: it presents "
        "the pull-up and energises the port on the user's press, so it is a "
        "charging port that advertises correctly rather than a conforming "
        "source, and no compliance claim is made for it",
        ("a Standard-A receptacle, rejected because the ones available are "
         "rated at 1.5 A and the board is rated at 2 A",
         "a conforming Type-C source with attach detection, rejected as a "
         "second comparator, a second reference and a two-input enable for "
         "a port whose only function is to deliver 5 V"),
        (STATIC, DOCUMENTATION), physical_test=True),

    "protection_switch_count": _decision(
        "three switch packages carry the cell current in parallel",
        "the protection senses a voltage across the switch, so the switch's "
        "resistance sets the trip current. One package would trip below the "
        "rated output and two would leave the trip current inside the "
        "ripple; three puts the lowest trip current clear of the highest "
        "instantaneous cell current",
        ("one package, rejected because its lowest trip current is below "
         "the average cell current at the rated output",
         "two packages, rejected because the margin over the peak is "
         "smaller than the ripple the inductance produces",
         "a protection device with a higher sense threshold, which would "
         "need one package - none of the ones stocked for a single cell "
         "offers one"),
        (ANALYTIC,)),

    "charlieplexed_indicators": _decision(
        "four state-of-charge indicators are driven from three controller "
        "pins as two antiparallel pairs",
        "the controller's pin table brings out three indicator drivers and "
        "its indication tables describe a four-indicator display; its own "
        "reference application resolves that by pairing the indicators "
        "across the drivers, and this board wires them the same way rather "
        "than choosing the three-indicator mode and losing a level",
        ("three indicators on three pins, rejected because the datasheet's "
         "three-indicator table resolves the charge state more coarsely",
         "a separate indicator driver, rejected as parts spent on something "
         "the controller already does"),
        (STATIC, ANALYTIC)),

    "input_rejected_indicator": _decision(
        "the fault indicator shows one condition: a source is attached and "
        "its advertisement is below what the board requires",
        "the brief asks the indication to separate charge state, charging, "
        "charge complete and fault. The controller's own indicators cover "
        "the first three. Of the faults this board can have, the only one it "
        "can both detect and still be powered to show is a source it has "
        "refused: a protection trip removes the board's own reference and a "
        "converter shutdown removes its supply, so neither can light "
        "anything",
        ("no fault indicator, rejected because the brief asks for one",
         "an indicator driven from the protection device, rejected because "
         "a protection trip disconnects the return everything on the board "
         "is referenced to"),
        (STATIC, ANALYTIC), physical_test=True),

    "usable_cell_range": _decision(
        "the usable cell voltage range is the controller's own battery "
        "operating range, 3.0 V to the charger's 4.2 V termination",
        "the brief makes the battery rail span the cell's discharge cut-off "
        "to its maximum charge voltage. The cell is not part of this design "
        "and no cell datasheet is frozen here, so the range the board can "
        "actually claim is the one its converter is specified over, which is "
        "narrower than any cell's",
        ("a range taken from a nominated cell, rejected because nominating "
         "a cell would put a document this repository does not hold under "
         "every rail claim",),
        (STATIC, DOCUMENTATION)),

    "maximum_ambient": _decision(
        "the board's ratings are claimed at a maximum ambient of 40 degC, "
        "and the sustained-output requirement is evaluated at 25 degC",
        "the brief conditions its thermal requirement on 'still air at room "
        "ambient' and states no figure for the rating case. Every junction "
        "temperature here is computed at one of the two, and which one is "
        "stated with the claim",
        ("evaluating everything at room ambient, rejected because a rating "
         "that only holds on a bench is not a rating",
         "the controller's own 70 degC maximum ambient, rejected because at "
         "that ambient the converter's junction claim has no margin left "
         "for the thermal resistance assumption below it"),
        (ANALYTIC, THERMAL_SIM)),

    "boost_efficiency_floor": _assumption(
        "the converter is at least 85% efficient delivering the rated "
        "output from the lowest usable cell voltage",
        "the cell-side current, and with it the protection margin, the "
        "inductor rating and every conductor width, is computed from the "
        "output power and this efficiency. The controller's datasheet states "
        "a peak efficiency and no minimum, so the floor is this board's",
        "a measured efficiency below 85% at the rated output and 3.0 V, "
        "which would raise the cell current and could put it above the "
        "protection's lowest trip current",
        (PHYSICAL_TEST,), physical_test=True),

    "cell_self_discharge": _assumption(
        "the cell loses 2% of a 2 Ah capacity per month to self-discharge",
        "the brief judges standby current against the cell's self-discharge "
        "and neither names a cell nor states a rate; the comparison needs "
        "both numbers and this repository freezes no cell datasheet",
        "a cell whose self-discharge is lower than this, which would make "
        "the board's standby current the larger of the two",
        (DOCUMENTATION, PHYSICAL_TEST), physical_test=True),

    "capacitor_dc_bias": _assumption(
        "class II ceramic capacitors retain the declared fraction of their "
        "nominal capacitance at the DC bias this board applies",
        "every capacitance figure in the latch timing and the filter timing "
        "depends on it. The datasheets state the effect as a curve this "
        "repository has not digitised, so the fraction is declared rather "
        "than read",
        "a measured capacitance below the declared fraction, which would "
        "shorten the latch's hold and the button filter's settling",
        (DOCUMENTATION, PHYSICAL_TEST), physical_test=True),

    "converter_thermal_resistance": _assumption(
        "the controller's stated junction-to-ambient thermal resistance "
        "applies to this board's copper",
        "the datasheet gives one figure and does not say what board it was "
        "measured on. Every junction temperature for that device rests on it",
        "a measured case temperature that implies a higher thermal "
        "resistance, which would raise the junction temperature at the rated "
        "output",
        (THERMAL_SIM, PHYSICAL_TEST), physical_test=True),

    "controller_stays_inside_recommended_input": _assumption(
        "the controller draws no more from its input than the maximum load "
        "current its recommended operating conditions state",
        "the board has no independent limiter between the input switch and "
        "the charger, so the claim that it stays inside the advertisement "
        "rests on the device staying inside its own recommended conditions",
        "a measured input current above the recommended maximum, which "
        "would break the advertisement claim rather than any rating",
        (PHYSICAL_TEST,), physical_test=True),

    "power_on_output_state": _assumption(
        "the converter does not enable its output without a button press",
        "the controller's datasheet states what a short press and a long "
        "press do, and states neither the converter's state when a cell is "
        "first attached nor whether its integrated load detector enables the "
        "converter unprompted. The board does not depend on the answer - the "
        "enable switch is what holds the port off - but the claim that the "
        "converter itself is off is not established",
        "a first article whose output is live at cell attach behind the "
        "enable switch, which would not change the port's behaviour but "
        "would change what the board dissipates while idle",
        (PHYSICAL_TEST,), physical_test=True),

    "protection_turn_off_time": _assumption(
        "the protection device turns its switch off inside the delay its "
        "datasheet states for the detection",
        "the datasheet characterises the gate outputs only at 10 uA, so the "
        "current available to discharge the parallel gates - and with it the "
        "time between detection and the current actually stopping - is not "
        "established",
        "a measured turn-off time long enough that the short-circuit "
        "current exceeds the switch's pulsed rating before it opens",
        (PHYSICAL_TEST,), physical_test=True),

    "small_against_self_discharge": _decision(
        "'small against the cell's self-discharge' is read as 'not larger "
        "than it', against a 2.5 Ah cell losing 2% of its charge per month",
        "the brief compares two currents and quantifies neither. The cell is "
        "not part of this design, so both numbers are declared: 2.5 Ah is "
        "the low end of a single cell of the size this board is built "
        "around and 2% per month the low end of the usual band, which "
        "together make the comparison the hardest rather than the easiest. "
        "A stricter reading - a factor below the self-discharge - would be a "
        "requirement no integrated controller of this class meets, because "
        "the controller's own standby current is the whole of the board's "
        "and cannot be reduced from outside it",
        ("a factor of two below the self-discharge, rejected because the "
         "controller's own standby current alone exceeds it",
         "a larger cell or a higher self-discharge rate, rejected because "
         "either would make the requirement easier without evidence"),
        (ANALYTIC, PHYSICAL_TEST), physical_test=True),

    "converter_response_budget": _decision(
        "the converter's control loop is allowed ten microseconds - five "
        "switching periods - to answer a step to the rated output current",
        "the datasheet states a switching frequency and no loop response "
        "time, and the output capacitance cannot be sized without one. Five "
        "periods is what a current-mode converter of this class needs to act "
        "on a load step, and it is stated here rather than assumed silently",
        ("sizing the capacitance for a millisecond, rejected because holding "
         "the rated current for that long would need nearly two orders more "
         "capacitance than the converter's own reference design carries",
         "not sizing it at all and relying on the converter, rejected "
         "because nothing in the frozen evidence says what the converter "
         "does during a step"),
        (CIRCUIT_SIM, PHYSICAL_TEST), physical_test=True),

    "conductor_sizing_model": _decision(
        "conductor cross-sections are sized by the IPC-2221 external-layer "
        "current capacity relation at a 20 degC rise",
        "the brief requires conductors to meet a stated temperature-rise "
        "limit and states no limit. The relation is manufacturer-independent "
        "and the rise is this board's declaration",
        ("a fixed rule of thumb in amps per millimetre, rejected because it "
         "hides the temperature rise it assumes",
         "a thermal solve, rejected as more than this stage's evidence "
         "supports"),
        (ANALYTIC, EXTRACTED)),
}


#: Origins that are not datasheets. Each names the file in the tree the
#: requirement was derived from, so a citation cannot point at nothing.
NON_DOCUMENT_ORIGINS = {
    "jlcpcb_catalogue_snapshot": "components/jlcpcb.json",
    "conductor_sizing_model": "design/requirements.py",
}


def _brief_anchors():
    """The anchors BRIEF.md actually offers, from its own headings."""
    anchors = set()
    with open(os.path.join(REPO_ROOT, BRIEF), encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("#"):
                continue
            title = line.lstrip("#").strip().lower()
            anchors.add("".join(character for character in
                                title.replace(" ", "-").replace("—", "")
                                if character.isalnum() or character == "-"))
    return anchors


def _evidence_ids():
    with open(os.path.join(REPO_ROOT, "evidence", "index.json"),
              encoding="utf-8") as handle:
        return set(json.load(handle)["documents"])


def check_origins():
    """Every citation resolves: a brief anchor, a frozen document, or a file.

    A register whose sources point at headings the brief does not have, or
    datasheets the repository never froze, reads exactly like one whose
    sources are real - which is why this is checked rather than reviewed.
    """
    anchors = _brief_anchors()
    documents = _evidence_ids()
    problems = []
    for name, record in sorted(list(REGISTER.items())
                               + list(STATEMENTS.items())):
        origins = record.get("origin", ())
        origins = (origins,) if isinstance(origins, str) else tuple(origins)
        cited = list(origins) + list(record.get("derived_from", ()))
        for origin in cited:
            if origin == name:
                continue
            if origin.startswith(BRIEF + "#"):
                anchor = origin.split("#", 1)[1]
                if anchor not in anchors:
                    problems.append("%s: %s has no such heading in %s"
                                    % (name, origin, BRIEF))
                continue
            if origin in documents:
                continue
            path = NON_DOCUMENT_ORIGINS.get(origin)
            if path is None:
                problems.append(
                    "%s: origin %r is neither a brief anchor, a frozen "
                    "evidence document, nor a declared file origin"
                    % (name, origin))
            elif not os.path.isfile(os.path.join(REPO_ROOT, path)):
                problems.append("%s: origin %r names %s, which does not exist"
                                % (name, origin, path))
    if problems:
        raise ValueError("requirement register cites sources that do not "
                         "resolve:\n  " + "\n  ".join(problems))
    return True


def entry(name):
    try:
        return REGISTER[name]
    except KeyError:
        raise KeyError(
            "requirement %r is judged by a claim but is not registered in "
            "design/requirements.py; every requirement states what kind of "
            "statement it is" % (name,))


def source_of(name):
    """The string a claim records as its requirement's source.

    Kind first, so a reader of one claim can see whether the requirement came
    from the brief or from this design without opening the register.
    """
    record = entry(name)
    origin = record.get("origin", name)
    if not isinstance(origin, str):
        origin = "+".join(origin)
    return "%s:%s" % (record["kind"], origin)


def _serialise(name, record):
    out = {"name": name}
    for key, value in sorted(record.items()):
        out[key] = list(value) if isinstance(value, tuple) else value
    return out


def check():
    """Every entry is well formed for the kind it declares."""
    problems = []
    for name, record in sorted(list(REGISTER.items())
                               + list(STATEMENTS.items())):
        kind = record.get("kind")
        if kind not in KINDS:
            problems.append("%s: kind %r is not one of %s"
                            % (name, kind, list(KINDS)))
            continue
        if not str(record.get("statement", "")).strip():
            problems.append("%s: no statement" % name)
        methods = record.get("verified_by") or ()
        if not methods:
            problems.append("%s: names no verification method" % name)
        for method in methods:
            if method not in METHODS:
                problems.append("%s: %r is not a verification method"
                                % (name, method))
        if kind == USER and not record.get("derived_from"):
            problems.append("%s: a user requirement cites its brief clause"
                            % name)
        if kind == DERIVED:
            if not record.get("derived_from"):
                problems.append("%s: a derived requirement states what it "
                                "was derived from" % name)
            if not str(record.get("rationale", "")).strip():
                problems.append("%s: a derived requirement states its "
                                "rationale" % name)
        if kind == DECISION:
            if not record.get("alternatives_considered"):
                problems.append("%s: a design decision states the "
                                "alternatives it was chosen over" % name)
            if not str(record.get("rationale", "")).strip():
                problems.append("%s: a design decision states its rationale"
                                % name)
        if kind == ASSUMPTION:
            if record.get("revisable") is not True:
                problems.append("%s: an assumption is revisable" % name)
            for field in ("reason", "invalidated_by"):
                if not str(record.get(field, "")).strip():
                    problems.append("%s: an assumption states its %s"
                                    % (name, field))
    if problems:
        raise ValueError("requirement register is malformed:\n  "
                         + "\n  ".join(problems))
    return check_origins()


def counts():
    tally = {}
    for record in list(REGISTER.values()) + list(STATEMENTS.values()):
        tally[record["kind"]] = tally.get(record["kind"], 0) + 1
    return tally


def document():
    check()
    return {
        "kind": "requirement-register",
        "schema": 1,
        "vocabulary": {"statement_kinds": list(KINDS),
                       "verification_methods": list(METHODS)},
        "requirements": [_serialise(name, record)
                         for name, record in sorted(REGISTER.items())],
        "statements": [_serialise(name, record)
                       for name, record in sorted(STATEMENTS.items())],
        "summary": counts(),
        "context": {
            "generated_by": "design/requirements.py",
            "join": "requirements[].name is the requirement name every claim "
                    "in generated/requirements.json is judged against; the "
                    "join is total in both directions",
            "statements": "statements[] are the design decisions and "
                          "assumptions no numeric claim is judged against, "
                          "including the choices that close the brief's open "
                          "questions",
        },
    }


def write():
    os.makedirs(os.path.dirname(REGISTER_PATH), exist_ok=True)
    with open(REGISTER_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return REGISTER_PATH


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
