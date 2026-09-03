"""Board-level electrical checks, stated as claims with their evidence.

Every number here comes from `components/parameters.json` (which cites the
frozen document it was read from), from the Type-C specification, or from the
netlist. Nothing is asserted that a document, a component value or a
measurement does not support, and a quantity that cannot be established is
reported as UNKNOWN rather than assumed.

The requirement each claim is judged against is registered in
`design/requirements.py`, which says what kind of statement it is and how it
can be established.
"""
from __future__ import annotations

import json
import math
import os
import sys

from . import libraries, netlist, requirements

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMETERS_PATH = os.path.join(REPO_ROOT, "components", "parameters.json")
CATALOG_PATH = os.path.join(REPO_ROOT, "components", "jlcpcb.json")
TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
FOOTPRINT_ROOT = "/usr/share/kicad/footprints"
LOCAL_FOOTPRINT_ROOT = os.path.join(REPO_ROOT, "library")

if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa import claim  # noqa: E402

DIRECT = "direct"
ASSUMED = "assumed"
DERIVED = "derived"

EVIDENCE_CLASSES = {
    DIRECT: "datasheet-behavioral",
    ASSUMED: "assumed-behavioral",
    DERIVED: "design-source",
}

REPORT_PATH = os.path.join(REPO_ROOT, "generated", "requirements.json")


def load_parameters():
    with open(PARAMETERS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _mpn(reference):
    return netlist.PARTS[reference]["mpn"]


def _spec(parameters, reference):
    return parameters["parts"][_mpn(reference)]


def _by_mpn(parameters, mpn):
    return parameters["parts"][mpn]


def _evidence(basis, documents, assumptions=(), omissions=()):
    provenance = {"source": "components/parameters.json",
                  "documents": sorted(set(documents))}
    return claim.evidence(
        "device_electrical", EVIDENCE_CLASSES.get(basis, "design-source"),
        provenance, assumptions=list(assumptions),
        omitted_contributions=list(omissions))


def _requirement(name, op, value):
    return claim.requirement(name, requirements.source_of(name),
                             {"op": op, "value": value})


#: How the requirement's operator turns a conservatively computed number into
#: the knowledge shape it actually supports. A worst case evaluated against a
#: floor is a lower bound on the real quantity; against a ceiling it is an
#: upper bound. Nothing that omits a contribution or rests on a premise is
#: ever allowed to call itself exact.
_BOUND_FOR_OPERATOR = {">=": claim.LOWER_BOUND, ">": claim.LOWER_BOUND,
                       "<=": claim.UPPER_BOUND, "<": claim.UPPER_BOUND}


def _claim(identity, units, significance, value, basis, documents,
           requirement, knowledge=None, scope_level="net",
           assumptions=(), omissions=()):
    if value is None:
        return claim.claim(
            scope_level, identity, units, claim.UNKNOWN, {},
            _evidence(basis, documents, assumptions, omissions),
            significance, None, requirement)
    if knowledge is None:
        if basis == ASSUMED or omissions:
            knowledge = _BOUND_FOR_OPERATOR.get(
                requirement["assertion"]["op"], claim.APPROXIMATE)
        else:
            knowledge = claim.EXACT
    basis_record = None
    if knowledge != claim.EXACT:
        basis_record = claim.knowledge_basis(
            basis, "datasheet_limit" if basis == DIRECT else basis)
    return claim.claim(
        scope_level, identity, units, knowledge, {"value": value},
        _evidence(basis, documents, assumptions, omissions),
        significance, basis_record, requirement)


def _structural(identity, significance, violations, requirement_name,
                documents=(), basis=DERIVED, assumptions=(), omissions=()):
    """A count of violations: zero is the only acceptable answer."""
    return _claim(identity, "violations", significance, float(len(violations)),
                  basis, documents, _requirement(requirement_name, "<=", 0.0),
                  scope_level="board", assumptions=assumptions,
                  omissions=omissions)


def _resistor_ohms(parameters, reference):
    return _spec(parameters, reference)["resistor"]["resistance_ohm"]["value"]


def _resistor_tolerance(parameters, reference):
    return _spec(parameters, reference)["resistor"]["tolerance"]["value"]


def _resistor_min(parameters, reference):
    return _resistor_ohms(parameters, reference) * (
        1.0 - _resistor_tolerance(parameters, reference))


def _resistor_max(parameters, reference):
    return _resistor_ohms(parameters, reference) * (
        1.0 + _resistor_tolerance(parameters, reference))


def _capacitance_farads(parameters, reference):
    return _spec(parameters, reference)["capacitor"]["capacitance_f"]["value"]


def _capacitance_low(parameters, reference):
    """A capacitance at the low end of everything that reduces it.

    Tolerance and DC bias both take capacitance away, and every question this
    board asks a capacitor - how long a latch holds, how fast a gate moves -
    is answered worse by less of it.
    """
    spec = _spec(parameters, reference)["capacitor"]
    value = spec["capacitance_f"]["value"] * (1.0 - spec["tolerance"]["value"])
    return value * spec["dc_bias_retained_fraction"]["value"]


# ---------------------------------------------------------------------------
# the operating model every downstream claim is built on

class Operating:
    """Worst-case currents and voltages, from parameters and part values.

    Currents are upper bounds and drops are computed at the highest current
    and the highest resistance the datasheets and the tolerances permit, so
    no downstream figure is optimistic.
    """

    def __init__(self, parameters):
        self.parameters = parameters
        self.documents = {"ip5306_injoinic", "ao8810_aos", "ao3415a_aos",
                          "swpa8040_sunlord", "usb_type_c"}

        controller = _by_mpn(parameters, "IP5306")
        self.input_min_v = netlist.INPUT_SUPPLY["min_v"]
        self.input_max_v = netlist.INPUT_SUPPLY["max_v"]

        self.controller_input_max_a = controller["recommended"][
            "load_current_max_a"]["value"]
        self.controller_uvlo_v = controller["charger"][
            "input_uvlo_rising_v"]["value"]
        self.charge_current_a = controller["charger"][
            "charge_current_typ_a"]["value"]
        self.charge_target_v = controller["charger"][
            "target_charge_voltage_v"]["value"]
        self.output_voltage_v = controller["boost"][
            "output_voltage_typ_v"]["value"]
        self.battery_floor_v = controller["boost"][
            "battery_voltage_min_v"]["value"]
        self.battery_ceiling_v = controller["boost"][
            "battery_voltage_max_v"]["value"]
        self.switching_hz = controller["boost"][
            "switching_frequency_hz"]["value"]
        self.controller_standby_a = controller["boost"][
            "battery_standby_current_typ_a"]["value"]
        self.controller_theta_ja = controller["thermal"][
            "junction_to_ambient_c_per_w"]["value"]
        self.controller_shutdown_c = controller["thermal"][
            "shutdown_rising_c"]["value"]

        # The cell-side current the whole board is sized by: the rated
        # output power, divided by the declared efficiency floor and the
        # lowest cell voltage the converter operates at.
        self.rated_output_a = netlist.RATED_OUTPUT_A
        self.output_power_w = self.output_voltage_v * self.rated_output_a
        self.efficiency_floor = netlist.BOOST_EFFICIENCY_FLOOR
        self.cell_current_a = self.output_power_w / (
            self.efficiency_floor * self.battery_floor_v)

        # Ripple in the boost inductor at that operating point, at the low
        # end of the inductance tolerance, which is where ripple is worst.
        inductor = _by_mpn(parameters, "SWPA8040S1R0NT")["inductor"]
        self.inductance_min_h = inductor["inductance_h"]["value"] * (
            1.0 - inductor["tolerance"]["value"])
        self.inductor_dcr_ohm = inductor["dc_resistance_max_ohm"]["value"]
        self.inductor_isat_a = inductor["saturation_current_a"]["value"]
        self.inductor_irms_a = inductor["heat_rating_current_a"]["value"]
        duty = 1.0 - self.battery_floor_v / self.output_voltage_v
        self.inductor_ripple_a = (self.battery_floor_v * duty) / (
            self.inductance_min_h * self.switching_hz)
        self.cell_peak_a = self.cell_current_a + self.inductor_ripple_a / 2.0
        self.cell_rms_a = math.sqrt(
            self.cell_current_a ** 2 + self.inductor_ripple_a ** 2 / 12.0)

        # The protection switch: the packages are in parallel, so the
        # resistance the protection senses across is one package's two
        # series devices divided by the number of packages.
        protection = _by_mpn(parameters, "AO8810")
        self.protection_rds_cold_ohm = 2.0 * protection["fet"][
            "rds_on_ohm"]["2.5"]["value"] / netlist.PROTECTION_PACKAGES
        hot = protection["fet"]["rds_on_hot_ohm"]["4.5"]["value"]
        cold = protection["fet"]["rds_on_ohm"]["4.5"]["value"]
        #: How much the switch's resistance rises per kelvin, from the two
        #: temperatures the datasheet tabulates the same drive at.
        self.rds_rise_per_k = (hot / cold - 1.0) / (125.0 - 25.0)
        self.protection_junction_c = self._protection_junction()
        self.protection_rds_hot_ohm = self.protection_rds_cold_ohm * (
            1.0 + self.rds_rise_per_k
            * (self.protection_junction_c - 25.0))

        # The two P-channel switches.
        switch = _by_mpn(parameters, "AO3415A")
        self.switch_rds_weak_ohm = switch["fet"]["rds_on_ohm"]["2.5"]["value"]
        self.switch_rds_strong_ohm = switch["fet"]["rds_on_ohm"][
            "4.5"]["value"]
        self.switch_theta_ja = switch["thermal"][
            "junction_to_ambient_max_c_per_w"]["value"]
        self.input_switch_junction_c, self.input_switch_rds_ohm = \
            self._switch_junction(self.switch_rds_weak_ohm,
                                  self.controller_input_max_a)
        self.output_switch_junction_c, self.output_switch_rds_ohm = \
            self._switch_junction(self.switch_rds_strong_ohm,
                                  self.rated_output_a)

    def _protection_junction(self):
        """Iterate the switch's junction: resistance sets loss, loss sets
        temperature, temperature sets resistance."""
        theta = _by_mpn(self.parameters, "AO8810")["thermal"][
            "junction_to_ambient_max_c_per_w"]["value"]
        junction = netlist.AMBIENT_MAX_C
        for _ in range(20):
            resistance = self.protection_rds_cold_ohm * (
                1.0 + self.rds_rise_per_k * (junction - 25.0))
            per_package = (self.cell_current_a ** 2 * resistance
                           / netlist.PROTECTION_PACKAGES)
            junction = netlist.AMBIENT_MAX_C + per_package * theta
        return junction

    def _switch_junction(self, cold_ohm, current_a):
        junction = netlist.AMBIENT_MAX_C
        resistance = cold_ohm
        for _ in range(20):
            resistance = cold_ohm * (
                1.0 + self.rds_rise_per_k * (junction - 25.0))
            junction = (netlist.AMBIENT_MAX_C
                        + current_a ** 2 * resistance * self.switch_theta_ja)
        return junction, resistance

    # -- Type-C reading ----------------------------------------------------

    def sink_cc_voltage(self, advertisement, form, extreme):
        """What this board's termination reads against one source pull-up.

        `extreme` is "max" or "min": the combination of supply, pull-up and
        termination tolerance that produces the highest or lowest reading.
        """
        parameters = self.parameters
        termination = (_resistor_max(parameters, "R1") if extreme == "max"
                       else _resistor_min(parameters, "R1"))
        if form == "resistor":
            entry = netlist.CC_PULL_UP_FORMS[advertisement]
            if extreme == "max":
                pull_up = entry["ohm"] * (1.0 - entry["tolerance"])
                supply = self.input_max_v
            else:
                pull_up = entry["ohm"] * (1.0 + entry["tolerance"])
                supply = self.input_min_v
            return supply * termination / (pull_up + termination)
        entry = netlist.CC_PULL_UP_CURRENTS[advertisement]
        current = entry["amp"] * (
            (1.0 + entry["tolerance"]) if extreme == "max"
            else (1.0 - entry["tolerance"]))
        return current * termination

    def detector_threshold(self, extreme):
        """The CC voltage the detector actually switches at.

        The reference, the comparator's own offset and the voltage its input
        current develops across the conductor it is reading all move it.
        """
        parameters = self.parameters
        reference = _by_mpn(parameters, "TLV431AIDBZR")["reference"]
        comparator = _by_mpn(parameters, "LM393DR2G")["comparator"]
        offset = comparator["offset_voltage_over_temperature_max_v"]["value"]
        bias = comparator[
            "input_bias_current_over_temperature_max_a"]["value"]
        # the CC conductor's own impedance is the termination in parallel
        # with the strongest pull-up a source may present
        strongest = min(entry["ohm"] for entry in
                        netlist.CC_PULL_UP_FORMS.values())
        termination = _resistor_max(parameters, "R1")
        source_impedance = strongest * termination / (strongest + termination)
        if extreme == "max":
            return (reference["voltage_max_v"]["value"] + offset
                    + bias * source_impedance)
        return (reference["voltage_min_v"]["value"] - offset
                - bias * source_impedance)

    def detector_quiescent_a(self):
        """What the detector takes from the source with charging refused."""
        parameters = self.parameters
        comparator = _by_mpn(parameters, "LM393DR2G")["comparator"]
        reference = _by_mpn(parameters, "TLV431AIDBZR")["reference"]
        bias = (self.input_max_v - reference["voltage_min_v"]["value"]) \
            / _resistor_min(parameters, "R4")
        indicator = _by_mpn(parameters, "KT-0603R")["led"]
        led = (self.input_max_v
               - indicator["forward_voltage_min_v"]["value"]) \
            / _resistor_min(parameters, "R9")
        gate = self.input_max_v / (_resistor_min(parameters, "R5")
                                   + _resistor_min(parameters, "R6"))
        return (comparator["supply_current_max_a"]["value"] + bias + led
                + gate)


# ---------------------------------------------------------------------------
# the input port

def evaluate_sink_termination(parameters):
    """The board terminates both CC conductors inside the specification."""
    results = []
    permitted = 0.10
    for reference, net in (("R1", "CC1"), ("R2", "CC2")):
        nominal = _resistor_ohms(parameters, reference)
        error = abs(nominal - netlist.CC_SINK_TERMINATION_OHM) \
            / netlist.CC_SINK_TERMINATION_OHM \
            + _resistor_tolerance(parameters, reference)
        results.append({
            "id": "sink_termination_within_specification",
            "identity": net,
            "measured": error,
            "claim": _claim(
                net, "fraction", "interface_compliance", error, DIRECT,
                ("usb_type_c", "res_0603_uniroyal"),
                _requirement("sink_termination_within_specification", "<=",
                             permitted)),
        })
    entering = netlist.pin_to_net()
    missing = [net for net in ("CC1", "CC2")
               if not any(pin.startswith("J1.") for pin in netlist.NETS[net])]
    results.append({
        "id": "both_orientations_terminated",
        "identity": "J1",
        "measured": float(len(missing)),
        "claim": _structural("J1", "interface_compliance", missing,
                             "both_orientations_terminated",
                             ("usb_type_c",)),
    })
    del entering
    return results


def evaluate_advertisement_detection(parameters):
    """The detector separates the advertisements it has to separate."""
    operating = Operating(parameters)
    documents = ("usb_type_c", "tlv431_ti", "lm393_onsemi",
                 "res_0603_uniroyal")
    highest_1_5 = max(
        operating.sink_cc_voltage("1.5A", form, "max")
        for form in ("resistor", "current"))
    lowest_3_0 = min(
        operating.sink_cc_voltage("3.0A", form, "min")
        for form in ("resistor", "current"))
    results = [{
        "id": "threshold_above_1_5A_advertisement",
        "identity": "VREF",
        "measured": operating.detector_threshold("min"),
        "claim": _claim(
            "VREF", "V", "interface_compliance",
            operating.detector_threshold("min"), DIRECT, documents,
            _requirement("threshold_above_1_5A_advertisement", ">=",
                         highest_1_5),
            assumptions=(
                "the highest reading a 1.5 A advertisement can produce is "
                "computed from the specification's own pull-up table at the "
                "extremes of supply, pull-up tolerance and termination "
                "tolerance",)),
    }, {
        "id": "threshold_below_3_0A_advertisement",
        "identity": "VREF",
        "measured": operating.detector_threshold("max"),
        "claim": _claim(
            "VREF", "V", "interface_compliance",
            operating.detector_threshold("max"), DIRECT, documents,
            _requirement("threshold_below_3_0A_advertisement", "<=",
                         lowest_3_0),
            assumptions=(
                "the lowest reading a 3.0 A advertisement can produce is "
                "computed from the specification's own pull-up table at the "
                "extremes of supply, pull-up tolerance and termination "
                "tolerance",)),
    }]

    reference = _by_mpn(parameters, "TLV431AIDBZR")["reference"]
    bias_min = (operating.input_min_v
                - reference["voltage_max_v"]["value"]) \
        / _resistor_max(parameters, "R4")
    bias_max = (operating.input_max_v
                - reference["voltage_min_v"]["value"]) \
        / _resistor_min(parameters, "R4")
    results.append({
        "id": "reference_bias_above_regulation_minimum",
        "identity": "VREF",
        "measured": bias_min,
        "claim": _claim(
            "VREF", "A", "interface_compliance", bias_min, DIRECT,
            ("tlv431_ti", "res_0603_uniroyal"),
            _requirement("reference_bias_above_regulation_minimum", ">=",
                         reference["cathode_current_min_a"]["value"]),
            omissions=("the comparator inputs draw current from the "
                       "reference node as well; their bias current is three "
                       "orders below this and is not subtracted",)),
    })
    results.append({
        "id": "reference_bias_below_maximum",
        "identity": "VREF",
        "measured": bias_max,
        "claim": _claim(
            "VREF", "A", "interface_compliance", bias_max, DIRECT,
            ("tlv431_ti", "res_0603_uniroyal"),
            _requirement("reference_bias_below_maximum", "<=",
                         reference["cathode_current_max_a"]["value"])),
    })
    results.append({
        "id": "reference_load_capacitance_within_stable_range",
        "identity": "VREF",
        "measured": _capacitance_farads(parameters, "C2"),
        "claim": _claim(
            "VREF", "F", "interface_compliance",
            _capacitance_farads(parameters, "C2"), DIRECT,
            ("tlv431_ti", "mlcc_yageo_cc0603"),
            _requirement("reference_load_capacitance_within_stable_range",
                         "<=",
                         reference["stable_load_capacitance_max_f"]["value"])),
    })

    comparator = _by_mpn(parameters, "LM393DR2G")["comparator"]
    highest_cc = max(
        operating.sink_cc_voltage("3.0A", form, "max")
        for form in ("resistor", "current"))
    headroom = operating.input_min_v - comparator[
        "common_mode_headroom_v"]["value"]
    results.append({
        "id": "comparator_input_within_common_mode_range",
        "identity": "CC1",
        "measured": highest_cc,
        "claim": _claim(
            "CC1", "V", "interface_compliance", highest_cc, DIRECT,
            ("lm393_onsemi", "usb_type_c"),
            _requirement("comparator_input_within_common_mode_range", "<=",
                         headroom)),
    })
    return results


def evaluate_input_current(parameters):
    """The board takes no more than the source offered it."""
    operating = Operating(parameters)
    quiescent = operating.detector_quiescent_a()
    smallest = min(entry["advertises_a"]
                   for entry in netlist.CC_PULL_UP_FORMS.values())
    results = [{
        "id": "rejected_source_current_below_default",
        "identity": "VBUS",
        "measured": quiescent,
        "claim": _claim(
            "VBUS", "A", "interface_compliance", quiescent, DIRECT,
            ("lm393_onsemi", "tlv431_ti", "kt0603r_kento",
             "res_0603_uniroyal", "usb_type_c"),
            _requirement("rejected_source_current_below_default", "<=",
                         smallest)),
    }]
    accepted = operating.controller_input_max_a + quiescent
    results.append({
        "id": "input_current_below_advertisement",
        "identity": "VBUS",
        "measured": accepted,
        "claim": _claim(
            "VBUS", "A", "interface_compliance", accepted, ASSUMED,
            ("ip5306_injoinic", "usb_type_c"),
            _requirement("input_current_below_advertisement", "<=",
                         netlist.REQUIRED_ADVERTISEMENT_A),
            assumptions=(
                "the charger stays inside the maximum load current its "
                "recommended operating conditions state; the board carries "
                "no independent limiter between the switch and the charger",),
            omissions=(
                "the datasheet states no hard input current limit for the "
                "charger, so this is a bound on specified operation rather "
                "than on the device's behaviour under fault",)),
    })

    drop = operating.controller_input_max_a * operating.input_switch_rds_ohm
    results.append({
        "id": "charger_input_above_undervoltage_lockout",
        "identity": "VIN",
        "measured": operating.input_min_v - drop,
        "claim": _claim(
            "VIN", "V", "power_margin", operating.input_min_v - drop, DIRECT,
            ("ip5306_injoinic", "ao3415a_aos", "usb_type_c"),
            _requirement("charger_input_above_undervoltage_lockout", ">=",
                         operating.controller_uvlo_v),
            assumptions=(
                "the switch conducts at the resistance its datasheet states "
                "for a 2.5 V gate drive, which is the weakest drive it "
                "tabulates and is below the drive this gate network gives "
                "it",),
            omissions=("board copper between the receptacle and the charger "
                       "is not included; it has not been laid out yet",)),
    })
    return results


# ---------------------------------------------------------------------------
# the cell and its protection

def evaluate_cell_protection(parameters):
    operating = Operating(parameters)
    protection = _by_mpn(parameters, "DW01A")["protection"]
    trip_min = protection["overcurrent_min_v"]["value"] \
        / operating.protection_rds_hot_ohm
    results = [{
        "id": "protection_does_not_trip_at_rated_output",
        "identity": "CELLN",
        "measured": trip_min,
        "claim": _claim(
            "CELLN", "A", "safety_margin", trip_min, DIRECT,
            ("dw01a_puolop", "ao8810_aos", "ip5306_injoinic",
             "swpa8040_sunlord"),
            _requirement("protection_does_not_trip_at_rated_output", ">=",
                         operating.cell_peak_a),
            assumptions=(
                "the conversion efficiency is at the declared floor, which "
                "is what makes the cell current worst case",
                "the switch resistance rises with temperature at the rate "
                "the two tabulated junction temperatures give, applied to "
                "the gate drive the protection device actually provides",),
            omissions=(
                "the cell's own internal resistance is outside the board "
                "and is not included; it lowers the cell voltage under load "
                "and therefore raises this current",)),
    }]
    results.append({
        "id": "protection_overcharge_above_charge_target",
        "identity": "BAT",
        "measured": protection["overcharge_min_v"]["value"],
        "claim": _claim(
            "BAT", "V", "safety_margin",
            protection["overcharge_min_v"]["value"], DIRECT,
            ("dw01a_puolop", "ip5306_injoinic"),
            _requirement("protection_overcharge_above_charge_target", ">=",
                         operating.charge_target_v)),
    })
    results.append({
        "id": "protection_overdischarge_below_operating_floor",
        "identity": "BAT",
        "measured": protection["overdischarge_max_v"]["value"],
        "claim": _claim(
            "BAT", "V", "safety_margin",
            protection["overdischarge_max_v"]["value"], DIRECT,
            ("dw01a_puolop", "ip5306_injoinic"),
            _requirement("protection_overdischarge_below_operating_floor",
                         "<=", operating.battery_floor_v)),
    })

    switch = _by_mpn(parameters, "AO8810")["absolute_maximum"]
    per_package = operating.cell_current_a / netlist.PROTECTION_PACKAGES
    results.append({
        "id": "protection_switch_within_current_rating",
        "identity": "CELLN",
        "measured": per_package,
        "claim": _claim(
            "CELLN", "A", "device_rating", per_package, DIRECT,
            ("ao8810_aos",),
            _requirement("protection_switch_within_current_rating", "<=",
                         switch["drain_current_70c_a"]["value"]),
            assumptions=("the packages share the cell current equally; they "
                         "are the same part with their sources and drains "
                         "tied together",)),
    })
    results.append({
        "id": "protection_switch_junction_below_maximum",
        "identity": "CELLN",
        "measured": operating.protection_junction_c,
        "claim": _claim(
            "CELLN", "degC", "thermal_margin",
            operating.protection_junction_c, DIRECT, ("ao8810_aos",),
            _requirement("protection_switch_junction_below_maximum", "<=",
                         switch["junction_temperature_c"]["value"]),
            assumptions=(
                "the ambient is the maximum this board declares",
                "the package's stated junction-to-ambient resistance applies "
                "to this board's copper",),
            omissions=("heat from the neighbouring packages is not added; "
                       "each is treated as if it stood alone",)),
    })

    connector = _by_mpn(parameters, "B2P-VH(LF)(SN)")["connector"]
    results.append({
        "id": "cell_connector_within_current_rating",
        "identity": "J3",
        "measured": operating.cell_peak_a,
        "claim": _claim(
            "J3", "A", "device_rating", operating.cell_peak_a, DIRECT,
            ("jst_vh",),
            _requirement("cell_connector_within_current_rating", "<=",
                         connector["current_rating_a"]["value"])),
    })
    results.append({
        "id": "cell_connector_polarised",
        "identity": "J3",
        "measured": 0.0,
        "claim": _structural(
            "J3", "safety_margin",
            [] if connector["polarised"]["value"] else ["J3"],
            "cell_connector_polarised", ("jst_vh",), basis=DIRECT),
    })
    return results


def _cell_rail_references():
    """Every part with a pin on a net whose potential is the cell rail."""
    mapping = netlist.pin_to_net()
    found = set()
    for pin, net in mapping.items():
        if net in netlist.CELL_RAIL_NETS:
            found.add(pin.split(".", 1)[0])
    return sorted(reference for reference in found
                  if netlist.PARTS[reference]["in_bom"])


#: Part families whose rating is not a voltage across a rail, and the
#: claim that judges them instead. A part here is not counted as unrated;
#: the reason says where its limit is actually checked.
VOLTAGE_RATING_EXEMPT = {
    "inductor": "the datasheet states no voltage rating; what bounds this "
                "part is current, and the saturation and heat-rating claims "
                "judge it",
    "led": "an indicator's ratings are a forward current and a reverse "
           "voltage; both are judged by the indicator claims, and neither "
           "indicator on this board stands a rail across itself - each sits "
           "in series with the element that sets its current",
}


def _rating_exemption(parameters, reference):
    spec = _spec(parameters, reference)
    for family, reason in VOLTAGE_RATING_EXEMPT.items():
        if family in spec:
            return reason
    return None


def _part_voltage_rating(parameters, reference):
    """The highest steady voltage a part may stand across it, or None."""
    spec = _spec(parameters, reference)
    if "capacitor" in spec:
        return spec["capacitor"]["voltage_max_v"]["value"]
    if "resistor" in spec:
        return spec["resistor"]["working_voltage_max_v"]["value"]
    if "absolute_maximum" in spec:
        maximum = spec["absolute_maximum"]
        for key in ("drain_source_voltage_v", "supply_voltage_v",
                    "input_voltage_v"):
            if key in maximum:
                return maximum[key]["value"]
    if "clamp" in spec:
        return spec["clamp"]["working_voltage_max_v"]["value"]
    if "led" in spec:
        return spec["led"]["reverse_voltage_max_v"]["value"]
    if "connector" in spec:
        return spec["connector"]["voltage_rating_v"]["value"]
    if "switch" in spec:
        return spec["switch"]["contact_voltage_max_v"]["value"]
    if "inductor" in spec:
        return None
    return None


def evaluate_voltage_ratings(parameters):
    """No part sees more than it is rated for, on either rail system."""
    protection = _by_mpn(parameters, "DW01A")["protection"]
    ceiling = protection["overcharge_max_v"]["value"]
    unrated, exceeded, exempt = [], [], {}
    for reference in _cell_rail_references():
        reason = _rating_exemption(parameters, reference)
        if reason is not None:
            exempt[reference] = reason
            continue
        rating = _part_voltage_rating(parameters, reference)
        if rating is None:
            unrated.append(reference)
        elif rating < ceiling:
            exceeded.append(reference)
    results = [{
        "id": "cell_rail_parts_rated_above_protection_ceiling",
        "identity": "BAT",
        "measured": float(len(exceeded) + len(unrated)),
        "claim": _structural(
            "BAT", "device_rating", exceeded + unrated,
            "cell_rail_parts_rated_above_protection_ceiling",
            ("dw01a_puolop",), basis=DIRECT,
            assumptions=("the ceiling is the protection device's own "
                         "over-charge threshold at the top of its "
                         "tolerance, not the charger's termination "
                         "voltage",),
            omissions=tuple(
                "%s was not judged here: %s" % (reference, reason)
                for reference, reason in sorted(exempt.items()))),
    }]

    mapping = netlist.pin_to_net()
    five_volt_nets = ("VBUS", "VIN", "VBUS_DAMP", "VOUT", "VOUT_SW",
                      "FAULT_A", "FAULT_K", "OUT_G", "VIN_G")
    highest = netlist.INPUT_SUPPLY["max_v"]
    over, unknown, rail_exempt = [], [], {}
    for pin, net in sorted(mapping.items()):
        if net not in five_volt_nets:
            continue
        reference = pin.split(".", 1)[0]
        if not netlist.PARTS[reference]["in_bom"]:
            continue
        reason = _rating_exemption(parameters, reference)
        if reason is not None:
            rail_exempt[reference] = reason
            continue
        rating = _part_voltage_rating(parameters, reference)
        if rating is None:
            if reference not in unknown:
                unknown.append(reference)
        elif rating < highest and reference not in over:
            over.append(reference)
    results.append({
        "id": "parts_rated_above_rail_maximum",
        "identity": "VBUS",
        "measured": float(len(over)),
        "claim": _structural(
            "VBUS", "device_rating", over,
            "parts_rated_above_rail_maximum",
            ("usb_type_c",), basis=DIRECT,
            omissions=tuple(
                "%s carries no voltage rating in the frozen parameters and "
                "was not judged" % reference for reference in unknown)
            + tuple("%s was not judged here: %s" % (reference, reason)
                    for reference, reason in sorted(rail_exempt.items()))),
    })

    clamp = _by_mpn(parameters, "TPD1E10B06DPYR")["clamp"]
    conductors = {"VBUS": highest, "CC1": highest, "CC2": highest,
                  "VOUT_SW": netlist.RATED_OUTPUT_V, "OUT_CC1": highest,
                  "OUT_CC2": highest}
    too_low = [net for net, level in conductors.items()
               if clamp["working_voltage_max_v"]["value"] < level]
    results.append({
        "id": "clamp_working_voltage_above_rail",
        "identity": "VBUS",
        "measured": float(len(too_low)),
        "claim": _structural(
            "VBUS", "device_rating", too_low,
            "clamp_working_voltage_above_rail", ("tpd1e10b06_ti",),
            basis=DIRECT),
    })
    return results


# ---------------------------------------------------------------------------
# the converter and the output

def evaluate_converter(parameters):
    operating = Operating(parameters)
    results = [{
        "id": "inductor_peak_below_saturation",
        "identity": "SW",
        "measured": operating.cell_peak_a,
        "claim": _claim(
            "SW", "A", "device_rating", operating.cell_peak_a, DIRECT,
            ("swpa8040_sunlord", "ip5306_injoinic"),
            _requirement("inductor_peak_below_saturation", "<=",
                         operating.inductor_isat_a),
            assumptions=(
                "the inductance is at the low end of its tolerance, which "
                "is where the ripple and therefore the peak is worst",
                "the conversion efficiency is at the declared floor",)),
    }, {
        "id": "inductor_rms_below_heat_rating",
        "identity": "SW",
        "measured": operating.cell_rms_a,
        "claim": _claim(
            "SW", "A", "device_rating", operating.cell_rms_a, DIRECT,
            ("swpa8040_sunlord",),
            _requirement("inductor_rms_below_heat_rating", "<=",
                         operating.inductor_irms_a),
            assumptions=("the ripple is triangular, so its contribution to "
                         "the RMS is the peak-to-peak over the square root "
                         "of twelve",)),
    }]

    switch = _by_mpn(parameters, "AO3415A")["absolute_maximum"]
    results.append({
        "id": "input_switch_junction_below_maximum",
        "identity": "VIN",
        "measured": operating.input_switch_junction_c,
        "claim": _claim(
            "VIN", "degC", "thermal_margin",
            operating.input_switch_junction_c, DIRECT, ("ao3415a_aos",),
            _requirement("input_switch_junction_below_maximum", "<=",
                         switch["junction_temperature_c"]["value"]),
            assumptions=(
                "the switch conducts at the resistance stated for the "
                "weakest gate drive the datasheet tabulates",
                "the ambient is the maximum this board declares",
                "the package's stated junction-to-ambient resistance applies "
                "to this board's copper",)),
    })
    results.append({
        "id": "output_switch_junction_below_maximum",
        "identity": "VOUT_SW",
        "measured": operating.output_switch_junction_c,
        "claim": _claim(
            "VOUT_SW", "degC", "thermal_margin",
            operating.output_switch_junction_c, DIRECT, ("ao3415a_aos",),
            _requirement("output_switch_junction_below_maximum", "<=",
                         switch["junction_temperature_c"]["value"]),
            assumptions=(
                "the ambient is the maximum this board declares",
                "the package's stated junction-to-ambient resistance applies "
                "to this board's copper",)),
    })

    port_v = operating.output_voltage_v \
        - operating.rated_output_a * operating.output_switch_rds_ohm
    results.append({
        "id": "port_voltage_above_source_minimum",
        "identity": "VOUT_SW",
        "measured": port_v,
        "claim": _claim(
            "VOUT_SW", "V", "interface_compliance", port_v, DIRECT,
            ("ip5306_injoinic", "ao3415a_aos", "usb_type_c"),
            _requirement("port_voltage_above_source_minimum", ">=",
                         netlist.INPUT_SUPPLY["min_v"]),
            omissions=(
                "board copper between the converter and the receptacle is "
                "not included; it has not been laid out yet",
                "the converter's regulated output is a typical figure with "
                "no tolerance stated, so the starting point of this "
                "subtraction is not bounded",)),
    })

    # what a sink reads on this port's CC conductor
    pull_up_max = _resistor_max(parameters, "R20")
    pull_up_min = _resistor_min(parameters, "R20")
    sink_termination = netlist.CC_SINK_TERMINATION_OHM
    lowest = port_v * (sink_termination * 0.9) / (
        pull_up_max + sink_termination * 0.9)
    highest = operating.output_voltage_v * (sink_termination * 1.1) / (
        pull_up_min + sink_termination * 1.1)
    band_low, band_high = 1.31, 2.04
    results.append({
        "id": "output_advertisement_lands_in_3_0A_band",
        "identity": "OUT_CC1",
        "measured": lowest,
        "claim": _claim(
            "OUT_CC1", "V", "interface_compliance", lowest, DIRECT,
            ("usb_type_c", "res_0603_uniroyal"),
            _requirement("output_advertisement_lands_in_3_0A_band", ">=",
                         band_low),
            assumptions=("the sink terminates with the specification's "
                         "nominal resistance at the loosest tolerance it "
                         "permits a sink that reads advertisements",)),
    })
    results.append({
        "id": "output_advertisement_lands_in_3_0A_band",
        "identity": "OUT_CC2",
        "measured": highest,
        "claim": _claim(
            "OUT_CC2", "V", "interface_compliance", highest, DIRECT,
            ("usb_type_c", "res_0603_uniroyal"),
            _requirement("output_advertisement_lands_in_3_0A_band", "<=",
                         band_high),
            assumptions=("the sink terminates with the specification's "
                         "nominal resistance at the loosest tolerance it "
                         "permits a sink that reads advertisements",)),
    })

    port = _by_mpn(parameters, "TYPE-C-31-M-12")["connector"]
    for identity, current in (("J1", operating.controller_input_max_a),
                              ("J2", operating.rated_output_a)):
        results.append({
            "id": "port_connector_within_current_rating",
            "identity": identity,
            "measured": current,
            "claim": _claim(
                identity, "A", "device_rating", current, DIRECT,
                ("usbc_hro",),
                _requirement("port_connector_within_current_rating", "<=",
                             port["current_rating_a"]["value"])),
        })

    hold_capacitance = sum(
        _capacitance_low(parameters, reference)
        for reference in ("C10", "C11", "C12", "C13"))
    droop = operating.rated_output_a * netlist.CONVERTER_RESPONSE_BUDGET_S \
        / hold_capacitance
    results.append({
        "id": "output_holds_through_response_budget",
        "identity": "VOUT",
        "measured": operating.output_voltage_v - droop,
        "claim": _claim(
            "VOUT", "V", "power_margin", operating.output_voltage_v - droop,
            ASSUMED, ("ip5306_injoinic", "mlcc_cctc_1206"),
            _requirement("output_holds_through_response_budget", ">=",
                         netlist.CONVERTER_OVERLOAD_FLOOR_V),
            assumptions=(
                "the converter contributes nothing for the whole of the "
                "declared response budget, which is the worst case its "
                "datasheet leaves open",
                "the output capacitors are at the low end of their tolerance "
                "and retain only the declared fraction of that under bias",),
            omissions=(
                "the capacitors' equivalent series resistance adds a step at "
                "the instant the load appears; it is not included, and it "
                "makes the dip deeper",)),
    })

    # The rated output itself. The controller's datasheet states a typical
    # boost current and no minimum at any battery voltage, so what the board
    # is rated to deliver cannot be established from it.
    results.append({
        "id": "rated_output_current_supported",
        "identity": "VOUT",
        "measured": None,
        "claim": _claim(
            "VOUT", "A", "functional_capability", None, DIRECT,
            ("ip5306_injoinic",),
            _requirement("rated_output_current_supported", ">=",
                         netlist.RATED_OUTPUT_A),
            omissions=(
                "the controller's datasheet states a typical boost output "
                "current and a recommended maximum load current, and no "
                "minimum output current at any battery voltage; nothing in "
                "the frozen evidence bounds what the converter delivers at "
                "the bottom of the cell range",)),
    })

    dissipation = operating.output_power_w * (
        1.0 / operating.efficiency_floor - 1.0)
    elsewhere = (operating.cell_rms_a ** 2 * operating.inductor_dcr_ohm
                 + operating.cell_current_a ** 2
                 * operating.protection_rds_hot_ohm
                 + operating.rated_output_a ** 2
                 * operating.output_switch_rds_ohm)
    junction = netlist.ROOM_AMBIENT_C + max(dissipation - elsewhere, 0.0) \
        * operating.controller_theta_ja
    results.append({
        "id": "converter_junction_below_thermal_shutdown",
        "identity": "U1",
        "measured": junction,
        "claim": _claim(
            "U1", "degC", "thermal_margin", junction, ASSUMED,
            ("ip5306_injoinic", "swpa8040_sunlord", "ao8810_aos",
             "ao3415a_aos"),
            _requirement("converter_junction_below_thermal_shutdown", "<=",
                         operating.controller_shutdown_c),
            assumptions=(
                "the whole difference between the output power and the "
                "declared efficiency floor is dissipated on this board, and "
                "what the inductor, the protection switch and the output "
                "switch dissipate is subtracted from it, so the remainder is "
                "attributed to the converter",
                "the converter's stated junction-to-ambient resistance "
                "applies to this board's copper",
                "the ambient is room ambient, which is the condition the "
                "brief states this requirement at",),
            omissions=(
                "the capacitors' equivalent series resistance and the "
                "board's own copper losses are not separated out, so they "
                "are attributed to the converter",)),
    })
    return results


# ---------------------------------------------------------------------------
# the output enable

def evaluate_output_enable(parameters):
    """Nothing but a press turns the port on, and the latch holds it."""
    mapping = netlist.pin_to_net()
    operating = Operating(parameters)
    latch = _by_mpn(parameters, "AO3400A")["fet"]
    threshold = latch["vgs_threshold_max_v"]["value"]

    # structural: the only conductor between the converter and the port is
    # the enable switch, and the only thing that sets the latch is the button
    port_nets = {net for pin, net in mapping.items()
                 if pin.startswith("J2.")}
    bridging = sorted({pin.split(".", 1)[0] for pin, net in mapping.items()
                       if net == "VOUT"}
                      & {pin.split(".", 1)[0] for pin, net in mapping.items()
                         if net == "VOUT_SW"})
    del port_nets
    results = [{
        "id": "output_off_until_a_press",
        "identity": "VOUT_SW",
        "measured": float(len(bridging) - 1),
        "claim": _structural(
            "VOUT_SW", "functional_capability",
            [reference for reference in bridging if reference != "Q6"],
            "output_off_until_a_press", ("ip5306_injoinic",),
            assumptions=(
                "with no charge on the latch's hold capacitor the latch "
                "device's gate is at the reference and the enable switch's "
                "gate is at its own source, so both are off",),
            omissions=(
                "whether the converter itself starts without a press is not "
                "established by its datasheet; this claim is about the port, "
                "which the enable switch holds off either way",)),
    }]

    set_level = netlist.CELL["board_floor_v"] * _resistor_min(
        parameters, "R14") / (_resistor_max(parameters, "R13")
                              + _resistor_min(parameters, "R14"))
    results.append({
        "id": "latch_set_level_above_threshold",
        "identity": "SET",
        "measured": set_level,
        "claim": _claim(
            "SET", "V", "functional_capability", set_level, DIRECT,
            ("ao3400a_aos", "ao3401a_aos", "res_0603_uniroyal"),
            _requirement("latch_set_level_above_threshold", ">=", threshold),
            omissions=("the drop across the device that connects the cell "
                       "rail to this divider is not subtracted; at this "
                       "current it is microvolts",)),
    })

    hold_level = operating.output_voltage_v * _resistor_min(
        parameters, "R14") / (_resistor_max(parameters, "R15")
                              + _resistor_min(parameters, "R14"))
    results.append({
        "id": "latch_hold_level_above_threshold",
        "identity": "SET",
        "measured": hold_level,
        "claim": _claim(
            "SET", "V", "functional_capability", hold_level, DIRECT,
            ("ao3400a_aos", "ao3415a_aos", "res_0603_uniroyal"),
            _requirement("latch_hold_level_above_threshold", ">=",
                         threshold)),
    })

    hold_time = _resistor_min(parameters, "R14") \
        * _capacitance_low(parameters, "C15") \
        * math.log(netlist.CELL["board_floor_v"] / threshold)
    results.append({
        "id": "latch_hold_time_above_target",
        "identity": "SET",
        "measured": hold_time,
        "claim": _claim(
            "SET", "s", "functional_capability", hold_time, ASSUMED,
            ("mlcc_samsung_cl", "res_0603_uniroyal", "ao3400a_aos"),
            _requirement("latch_hold_time_above_target", ">=",
                         netlist.LATCH_HOLD_TARGET_S),
            assumptions=(
                "the hold capacitor is at the low end of its tolerance and "
                "retains only the declared fraction of that under bias",
                "the latch releases when its gate falls to the device's "
                "highest stated threshold",),
            omissions=("the latch device's own gate leakage is not "
                       "subtracted from the discharge",)),
    })

    hold = _spec(parameters, "C15")["capacitor"]["voltage_max_v"]["value"]
    results.append({
        "id": "latch_hold_capacitor_rated_above_set_level",
        "identity": "SET",
        "measured": hold,
        "claim": _claim(
            "SET", "V", "device_rating", hold, DIRECT, ("mlcc_samsung_cl",),
            _requirement("latch_hold_capacitor_rated_above_set_level", ">=",
                         operating.output_voltage_v)),
    })

    for identity, gate_ref, source_v, mpn in (
            ("VIN_G", "Q1", netlist.INPUT_SUPPLY["max_v"], "AO3415A"),
            ("OUT_G", "Q6", operating.output_voltage_v, "AO3415A"),
            ("SET", "Q7", netlist.CELL["protection_ceiling_v"], "AO3400A")):
        rating = _by_mpn(parameters, mpn)["absolute_maximum"][
            "gate_source_voltage_v"]["value"]
        results.append({
            "id": "switch_gate_within_rating",
            "identity": identity,
            "measured": source_v,
            "claim": _claim(
                identity, "V", "device_rating", source_v, DIRECT,
                ("ao3415a_aos", "ao3400a_aos"),
                _requirement("switch_gate_within_rating", "<=", rating)),
        })
        del gate_ref

    for identity, pull_up, series, capacitor in (
            ("VIN_G", "R5", "R6", "C3"), ("OUT_G", "R17", "R16", "C16")):
        low = _resistor_min(parameters, pull_up) \
            * _resistor_min(parameters, series) \
            / (_resistor_min(parameters, pull_up)
               + _resistor_min(parameters, series))
        constant = low * _capacitance_low(parameters, capacitor)
        results.append({
            "id": "switch_gate_slew_above_target",
            "identity": identity,
            "measured": constant,
            "claim": _claim(
                identity, "s", "functional_capability", constant, ASSUMED,
                ("res_0603_uniroyal", "mlcc_yageo_cc0603"),
                _requirement("switch_gate_slew_above_target", ">=",
                             netlist.SWITCH_SLEW_TARGET_S),
                assumptions=(
                    "the gate capacitor is at the low end of its tolerance "
                    "and retains only the declared fraction of that under "
                    "bias",),
                omissions=("the device's own gate charge is not added; it "
                           "lengthens this time rather than shortening it",)),
        })
    return results


# ---------------------------------------------------------------------------
# standby

def evaluate_standby(parameters):
    operating = Operating(parameters)
    protection = _by_mpn(parameters, "DW01A")["supply"]
    standby = (operating.controller_standby_a
               + protection["quiescent_current_max_a"]["value"]
               + netlist.CELL["protection_ceiling_v"]
               / (_resistor_min(parameters, "R12")
                  + _resistor_min(parameters, "R11")))
    self_discharge = (netlist.CELL_CAPACITY_AH
                      * netlist.CELL_SELF_DISCHARGE_PER_MONTH
                      / (30.0 * 24.0))
    return [{
        "id": "standby_current_below_self_discharge",
        "identity": "BAT",
        "measured": standby,
        "claim": _claim(
            "BAT", "A", "power_margin", standby, ASSUMED,
            ("ip5306_injoinic", "dw01a_puolop", "res_0603_uniroyal"),
            _requirement("standby_current_below_self_discharge", "<=",
                         self_discharge),
            assumptions=(
                "the cell loses the declared fraction of the declared "
                "capacity per month",
                "the pull-up on the button's node is counted as if the "
                "controller's button pin held that node at the reference, "
                "which is the most that path can take; the controller's "
                "datasheet states no bias for that pin, so the alternative "
                "reading - that it carries nothing - is not established",),
            omissions=(
                "the controller's standby current is a typical figure and "
                "the datasheet states no maximum, so this sum is not "
                "bounded above",
                "leakage through the switches and the capacitors is not "
                "included",)),
    }]


# ---------------------------------------------------------------------------
# the button and the indicators

def evaluate_button(parameters):
    switch = _by_mpn(parameters, "TS-1187A-B-A-B")["switch"]
    controller = _by_mpn(parameters, "IP5306")
    current = netlist.CELL["protection_ceiling_v"] / _resistor_min(
        parameters, "R12") + netlist.CELL["protection_ceiling_v"] \
        / _resistor_min(parameters, "R11")
    results = [{
        "id": "button_current_below_contact_rating",
        "identity": "SW1",
        "measured": current,
        "claim": _claim(
            "SW1", "A", "device_rating", current, DIRECT,
            ("ts1187a_xkb", "res_0603_uniroyal"),
            _requirement("button_current_below_contact_rating", "<=",
                         switch["contact_current_max_a"]["value"]),
            assumptions=(
                "the controller's own pull-up on its button pin is treated "
                "as if it pulled the pin to the cell rail through this "
                "board's series element, which is the largest current that "
                "path can carry; the datasheet states no value for it",)),
    }]

    settling = 5.0 * _resistor_max(parameters, "R11") \
        * _capacitance_low(parameters, "C14")
    results.append({
        "id": "button_filter_below_ignore_window",
        "identity": "KEY",
        "measured": settling,
        "claim": _claim(
            "KEY", "s", "functional_capability", settling, DIRECT,
            ("ip5306_injoinic", "res_0603_uniroyal", "mlcc_yageo_cc0603"),
            _requirement("button_filter_below_ignore_window", "<=",
                         controller["button"]["ignore_below_s"]["value"]),
            assumptions=("settling is taken as five time constants",)),
    })

    mapping = netlist.pin_to_net()
    pulled = [pin for pin, net in mapping.items()
              if net == "BTN" and pin.startswith("R12.")]
    results.append({
        "id": "no_floating_node",
        "identity": "BTN",
        "measured": 0.0 if pulled else 1.0,
        "claim": _structural(
            "BTN", "functional_capability", [] if pulled else ["BTN"],
            "no_floating_node"),
    })
    return results


def evaluate_indicators(parameters):
    operating = Operating(parameters)
    controller = _by_mpn(parameters, "IP5306")["indicator"]
    green = _by_mpn(parameters, "KT-0603G")["led"]
    red = _by_mpn(parameters, "KT-0603R")["led"]
    results = [{
        "id": "indicator_current_within_rating",
        "identity": "LED1",
        "measured": controller["led_current_typ_a"]["value"],
        "claim": _claim(
            "LED1", "A", "device_rating",
            controller["led_current_typ_a"]["value"], DIRECT,
            ("ip5306_injoinic", "kt0603g_kento"),
            _requirement("indicator_current_within_rating", "<=",
                         green["forward_current_max_a"]["value"]),
            assumptions=("the controller's indicator drivers are current "
                         "sources at the value its datasheet states; it "
                         "gives one figure and no tolerance",)),
    }]
    fault_current = (operating.input_max_v
                     - red["forward_voltage_min_v"]["value"]) \
        / _resistor_min(parameters, "R9")
    results.append({
        "id": "indicator_current_within_rating",
        "identity": "FAULT_A",
        "measured": fault_current,
        "claim": _claim(
            "FAULT_A", "A", "device_rating", fault_current, DIRECT,
            ("kt0603r_kento", "res_0603_uniroyal", "usb_type_c"),
            _requirement("indicator_current_within_rating", "<=",
                         red["forward_current_max_a"]["value"]),
            omissions=("the drop across the device in series with the "
                       "indicator is not subtracted; leaving it out "
                       "overstates the current",)),
    })
    results.append({
        "id": "indicator_reverse_within_rating",
        "identity": "LED3",
        "measured": green["forward_voltage_max_v"]["value"],
        "claim": _claim(
            "LED3", "V", "device_rating",
            green["forward_voltage_max_v"]["value"], DIRECT,
            ("kt0603g_kento",),
            _requirement("indicator_reverse_within_rating", "<=",
                         green["reverse_voltage_max_v"]["value"]),
            assumptions=("an indicator held off by its pair sees that pair's "
                         "forward voltage in reverse, because the two share "
                         "both drivers",)),
    })
    return results


# ---------------------------------------------------------------------------
# structure, access and manufacture

def evaluate_esd_coverage(parameters):
    """Every conductor that enters the board is clamped or exempt."""
    mapping = netlist.pin_to_net()
    clamped = set()
    for reference, part in netlist.PARTS.items():
        if part["mpn"] != "TPD1E10B06DPYR":
            continue
        for pin, net in mapping.items():
            if pin.startswith(reference + ".") and net != "GND":
                clamped.add(net)
    uncovered = [net for net in sorted(netlist.entering_conductors())
                 if net not in clamped and net not in netlist.ESD_EXEMPT]
    del parameters
    return [{
        "id": "esd_coverage_complete",
        "identity": "board",
        "measured": float(len(uncovered)),
        "claim": _structural("board", "safety_margin", uncovered,
                             "esd_coverage_complete", ("tpd1e10b06_ti",)),
    }]


def evaluate_connector_contract(parameters):
    mapping = netlist.pin_to_net()
    wrong = []
    for reference, functions in sorted(
            netlist.CONNECTOR_FUNCTION_NETS.items()):
        for function, net in sorted(functions.items()):
            if reference in ("J1", "J2"):
                pins = netlist.USB_C_PINS.get(function, ())
            elif function == "CELL_POSITIVE":
                pins = ("1",)
            else:
                pins = ("2",)
            for pin in pins:
                key = "%s.%s" % (reference, pin)
                if mapping.get(key) != net:
                    wrong.append(key)
    del parameters
    return [{
        "id": "connector_contract_consistent",
        "identity": "board",
        "measured": float(len(wrong)),
        "claim": _structural("board", "interface_compliance", wrong,
                             "connector_contract_consistent",
                             ("usbc_hro", "jst_vh"), basis=DIRECT),
    }]


def evaluate_probe_access(parameters):
    mapping = netlist.pin_to_net()
    probed = {net for pin, net in mapping.items() if pin.startswith("TP")}
    missing = [net for net in netlist.PROBE_REQUIRED_NETS
               if net not in probed]
    results = [{
        "id": "probe_access_complete",
        "identity": "board",
        "measured": float(len(missing)),
        "claim": _structural("board", "functional_capability", missing,
                             "probe_access_complete"),
    }]
    broken = []
    for first, second in netlist.KELVIN_PROBE_PAIRS:
        one = mapping.get(first + ".1")
        other = mapping.get(second + ".1")
        if one is None or one != other or first == second:
            broken.append("%s/%s" % (first, second))
    results.append({
        "id": "kelvin_pairs_present",
        "identity": "board",
        "measured": float(len(broken)),
        "claim": _structural("board", "functional_capability", broken,
                             "kelvin_pairs_present"),
    })
    del parameters
    return results


def _footprint_pad_count(footprint):
    library, _, name = footprint.partition(":")
    for base in (LOCAL_FOOTPRINT_ROOT, FOOTPRINT_ROOT):
        path = os.path.join(base, library + ".pretty", name + ".kicad_mod")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            numbers = set()
            index = 0
            while True:
                index = text.find('(pad "', index)
                if index < 0:
                    break
                index += 6
                end = text.find('"', index)
                number = text[index:end]
                if number:
                    numbers.add(number)
            return numbers
    raise FileNotFoundError(footprint)


def evaluate_package_correspondence(parameters):
    from . import ksym
    library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
    mismatched = []
    for reference, part in sorted(netlist.PARTS.items()):
        if not part["footprint"]:
            continue
        pins = set(library.pins(part["lib_id"]))
        pads = _footprint_pad_count(part["footprint"])
        if pads and pins != pads:
            mismatched.append(reference)
    del parameters
    return [{
        "id": "package_pins_match_land_pattern",
        "identity": "board",
        "measured": float(len(mismatched)),
        "claim": _structural("board", "interface_compliance", mismatched,
                             "package_pins_match_land_pattern",
                             ("usbc_hro",), basis=DIRECT),
    }]


def _footprint_is_through_hole(footprint):
    """Whether the land pattern declares itself a through-hole part.

    The declared attribute, not the presence of a plated pad: a surface-mount
    receptacle with through-hole shell posts has both, and which of the two
    it is decides how it is assembled.
    """
    library, _, name = footprint.partition(":")
    for base in (LOCAL_FOOTPRINT_ROOT, FOOTPRINT_ROOT):
        path = os.path.join(base, library + ".pretty", name + ".kicad_mod")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return "(attr through_hole" in handle.read()
    raise FileNotFoundError(footprint)


def evaluate_assembly(parameters):
    through_hole = sorted(
        reference for reference, part in netlist.PARTS.items()
        if part["footprint"] and part["in_bom"]
        and _footprint_is_through_hole(part["footprint"]))
    declared = netlist.ASSEMBLY_POLICY["through_hole_soldered_parts"]
    del parameters
    return [{
        "id": "assembly_within_declared_policy",
        "identity": "board",
        "measured": float(len(through_hole)),
        "claim": _claim(
            "board", "parts", "manufacturability", float(len(through_hole)),
            DERIVED, ("jst_vh",),
            _requirement("assembly_within_declared_policy", "<=",
                         float(declared)),
            scope_level="board"),
    }]


def evaluate_supply_availability(parameters):
    catalog = load_catalog()["parts"]
    counts = {}
    for part in netlist.PARTS.values():
        if part["in_bom"]:
            counts[part["lcsc"]] = counts.get(part["lcsc"], 0) + 1
    limits = {code: catalog[code]["stock"] // number
              for code, number in counts.items()}
    tightest = min(limits, key=limits.get)
    del parameters
    return [{
        "id": "stock_covers_planned_build",
        "identity": tightest,
        "measured": float(limits[tightest]),
        "claim": _claim(
            tightest, "boards", "manufacturability", float(limits[tightest]),
            DERIVED, (),
            _requirement("stock_covers_planned_build", ">=",
                         float(netlist.PLANNED_BUILD_QUANTITY)),
            scope_level="board",
            assumptions=("the stock figures are the ones frozen in "
                         "components/jlcpcb.json, not today's",)),
    }]


#: IPC-2221 external-layer current capacity: I = k * dT^0.44 * A^0.725 with
#: A in square mils, k = 0.048 for an external conductor.
IPC_EXTERNAL_K = 0.048
IPC_TEMPERATURE_EXPONENT = 0.44
IPC_AREA_EXPONENT = 0.725
#: The temperature rise the conductor sizing is stated at.
CONDUCTOR_RISE_C = 20.0
#: One ounce of finished copper, in millimetres, from the fabrication
#: requirements this board declares.
COPPER_THICKNESS_MM = 0.03556
MM2_PER_MIL2 = 0.00064516


def required_conductor_width_mm(current_a, rise_c=CONDUCTOR_RISE_C):
    area_mil2 = (current_a / (IPC_EXTERNAL_K
                              * rise_c ** IPC_TEMPERATURE_EXPONENT)) \
        ** (1.0 / IPC_AREA_EXPONENT)
    return area_mil2 * MM2_PER_MIL2 / COPPER_THICKNESS_MM


def evaluate_conductor_sizing(parameters):
    from . import build
    operating = Operating(parameters)
    declared = min(entry["track_width"] for entry in build.NET_CLASSES
                   if entry["name"] == "Power")
    required = required_conductor_width_mm(operating.cell_current_a)
    return [{
        "id": "conductor_width_for_cell_current",
        "identity": "BAT",
        "measured": declared,
        "claim": _claim(
            "BAT", "mm", "thermal_margin", declared, DERIVED,
            ("swpa8040_sunlord",),
            _requirement("conductor_width_for_cell_current", ">=", required),
            knowledge=claim.EXACT,
            assumptions=(
                "the conductor is on an external layer in one ounce of "
                "finished copper, which is what this board's fabrication "
                "requirements declare",
                "the temperature rise is the one this design declares",
                "this judges the width the board declares for its power net "
                "class, not copper; there is no copper yet, and the same "
                "requirement applies again to the routed board",)),
    }]


# ---------------------------------------------------------------------------

PRODUCERS = (
    evaluate_sink_termination,
    evaluate_advertisement_detection,
    evaluate_input_current,
    evaluate_cell_protection,
    evaluate_voltage_ratings,
    evaluate_converter,
    evaluate_output_enable,
    evaluate_standby,
    evaluate_button,
    evaluate_indicators,
    evaluate_esd_coverage,
    evaluate_connector_contract,
    evaluate_probe_access,
    evaluate_package_correspondence,
    evaluate_assembly,
    evaluate_supply_availability,
    evaluate_conductor_sizing,
)


def evaluate_all():
    parameters = load_parameters()
    results = []
    for producer in PRODUCERS:
        results.extend(producer(parameters))
    for result in results:
        result["verdict"] = claim.verdict(result["claim"])
    return results


def judged_requirements(results=None):
    """Every requirement name a claim is actually judged against."""
    results = evaluate_all() if results is None else results
    return {result["claim"]["requirement"]["name"] for result in results}


def write_report():
    """The whole claim set, as an artifact rather than a console report.

    Each entry carries what was measured, the evidence class it rests on, the
    documents behind it, the assumptions it was evaluated under and the
    verdict - so a later reader can see not only that the board passed but
    what "passed" was allowed to mean.
    """
    evaluated = evaluate_all()
    document = {
        "kind": "board-requirement-evidence",
        "summary": summarise(evaluated),
        "results": [
            {"id": result["id"], "identity": result["identity"],
             "claim": result["claim"], "verdict": result["verdict"]}
            for result in sorted(evaluated,
                                 key=lambda item: (item["id"],
                                                   item["identity"]))],
    }
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return REPORT_PATH


def summarise(results):
    counts = {}
    for result in results:
        counts[result["verdict"]["result"]] = counts.get(
            result["verdict"]["result"], 0) + 1
    return counts


if __name__ == "__main__":
    evaluated = evaluate_all()
    write_report()
    for result in sorted(evaluated, key=lambda item: (
            item["verdict"]["result"], item["id"], item["identity"])):
        value = result["claim"]["quantity"].get("value")
        rendered = "-" if value is None else "%.6g" % value
        assertion = result["claim"]["requirement"]["assertion"]
        sys.stdout.write("%-8s %-52s %-10s %12s %-6s %s %g\n" % (
            result["verdict"]["result"], result["id"], result["identity"],
            rendered, result["claim"]["units"], assertion["op"],
            assertion["value"]))
    sys.stdout.write("\n" + json.dumps(summarise(evaluated), sort_keys=True)
                     + "\n")
    del libraries
