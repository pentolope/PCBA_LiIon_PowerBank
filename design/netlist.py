"""The design source: every part, every connection, and the figures the
board's own claims are evaluated against.

Current runs cell -> protection -> boost -> output port. The cell's negative
leg is interrupted by the protection switch, so the system reference is the
pack negative and not the cell negative; those are two distinct nets and only
the protection switch bridges them.

Both ports are the same Type-C receptacle. The input presents the sink
terminations and the output presents a source pull-up, so the CC mechanism
itself decides which one a cable may deliver power through, and a plug in the
wrong socket carries no current rather than being prevented by a label.
"""
from __future__ import annotations

import os

PROJECT_NAME = "liion_power_bank"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYMBOL_LIBRARY_PATHS = (
    os.path.join(_REPO_ROOT, "library"),
    "/usr/share/kicad/symbols",
)

LIBRARY_NAME = "LiIonPowerBank"

#: Protection switch packages wired in parallel. The over-current threshold
#: is a voltage across the switch, so the number of packages is what sets the
#: current at which the protection trips; it is chosen against the peak cell
#: current, not against conduction loss.
PROTECTION_PACKAGES = 3

#: Type-C receptacle pins by function, from the receptacle's own numbering.
#: Both CC pins are used because a plug presents one or the other depending
#: on which way round it goes in, and the board has to work either way.
USB_C_PINS = {
    "GND": ("A1", "B1", "A12", "B12"),
    "VBUS": ("A4", "B4", "A9", "B9"),
    "CC1": ("A5",),
    "CC2": ("B5",),
    "SHIELD": ("SH",),
}

#: Receptacle pins the board leaves unconnected. Nothing here speaks USB
#: data, and an unconnected pad carries no conductor into the board that
#: would need a clamp.
USB_C_UNUSED = ("A6", "B6", "A7", "B7", "A8", "B8")

#: IP5306 package pins by name. The thermal pad is the device's ground
#: connection, so it is a numbered pin here and not a mechanical feature.
IP5306_PINS = {"VIN": "1", "LED1": "2", "LED2": "3", "LED3": "4",
               "KEY": "5", "BAT": "6", "SW": "7", "VOUT": "8", "GND": "9"}

#: DW01A package pins by name.
DW01A_PINS = {"OD": "1", "VM": "2", "OC": "3", "TD": "4", "VCC": "5",
              "GND": "6"}

#: AO8810 package pins. The two drains are tied inside the package; both
#: drain pins are brought out and both are used, so the land pattern and the
#: schematic agree pad for pad.
AO8810_PINS = {"D": ("1", "8"), "S1": ("2", "3"), "G1": "4", "G2": "5",
               "S2": ("6", "7")}

#: LM393 package pins. Two comparators and one supply pair, in one symbol,
#: because the design source places one symbol per package.
LM393_PINS = {"OUTA": "1", "INA-": "2", "INA+": "3", "V-": "4",
              "INB+": "5", "INB-": "6", "OUTB": "7", "V+": "8"}


def _part(lib_id, footprint, value, mpn=None, manufacturer=None, lcsc=None,
          datasheet="", in_bom=True, on_board=True):
    return {
        "lib_id": lib_id,
        "footprint": footprint,
        "value": value,
        "mpn": mpn,
        "manufacturer": manufacturer,
        "lcsc": lcsc,
        "datasheet": datasheet,
        "in_bom": in_bom,
        "on_board": on_board,
    }


def _resistor(value, lcsc, mpn):
    return _part("Device:R", "Resistor_SMD:R_0603_1608Metric", value,
                 mpn, "UNI-ROYAL(Uniroyal Elec)", lcsc)


def _capacitor(value, footprint, lcsc, mpn, manufacturer):
    return _part("Device:C", footprint, value, mpn, manufacturer, lcsc)


#: Resistor values this board uses, and the catalogue part behind each. The
#: damping resistors are the one 5% part; every other value is 1%, because
#: the advertisement thresholds and the latch dividers are decided by ratios.
RESISTOR_PARTS = {
    "2.2R": ("C25226", "0603WAJ022JT5E"),
    "100R": ("C22775", "0603WAF1000T5E"),
    "1k": ("C21190", "0603WAF1001T5E"),
    "1.5k": ("C22843", "0603WAF1501T5E"),
    "4.7k": ("C23162", "0603WAF4701T5E"),
    "5.1k": ("C23186", "0603WAF5101T5E"),
    "10k": ("C25804", "0603WAF1002T5E"),
    "100k": ("C25803", "0603WAF1003T5E"),
    "470k": ("C23178", "0603WAF4703T5E"),
    "1M": ("C22935", "0603WAF1004T5E"),
}

#: Every resistor on the board. What each value is for is stated beside it;
#: whether the value serves that purpose is decided in `rules`.
_RESISTOR_VALUES = {
    # sink termination, one per CC conductor of the input port
    1: "5.1k", 2: "5.1k",
    # input hot-plug damper
    3: "2.2R",
    # shunt-reference bias
    4: "4.7k",
    # input switch gate: the pull-up holds it off, the series element slews
    # it on
    5: "100k", 6: "10k",
    # input-rejected indicator: inverter and the indicator's series element
    7: "100k", 8: "470k", 9: "1.5k",
    # cell-rail damper
    10: "2.2R",
    # push button: series into the controller, and the pull-up that defines
    # the node the button pulls down. The pull-up is large because the
    # controller does not state which way its button pin is biased, so
    # this resistor has to be assumed to carry current continuously.
    11: "10k", 12: "1M",
    # output enable latch: set path, hold divider, feedback
    13: "10k", 14: "1M", 15: "100k",
    # output switch gate
    16: "10k", 17: "1M",
    # protection device supply filter and current-sense input
    18: "100R", 19: "1k",
    # source pull-up, one per CC conductor of the output port
    20: "10k", 21: "10k",
}

#: Every capacitor, by reference, with what it is there for. The four
#: values are four jobs: 100 nF beside a pin, 2.2 uF where a node has to
#: hold a level without being driven, 10 uF where a rail needs bulk behind a
#: switch, and 22 uF where the rail carries the cell current or has to
#: answer a step on its own.
_CAPACITORS = {
    1: ("100nF", "comparator supply"),
    2: ("100nF", "shunt reference"),
    3: ("100nF", "input switch gate slew"),
    4: ("22uF", "input damper capacitance, at the receptacle"),
    5: ("10uF", "charger input bulk"),
    6: ("100nF", "charger input, high frequency"),
    7: ("22uF", "cell rail"),
    8: ("22uF", "cell rail"),
    9: ("10uF", "cell rail damper"),
    10: ("22uF", "converter output"),
    11: ("22uF", "converter output"),
    12: ("22uF", "converter output"),
    13: ("22uF", "converter output"),
    14: ("100nF", "push-button filter"),
    15: ("2.2uF", "enable latch hold"),
    16: ("100nF", "output switch gate slew"),
    17: ("100nF", "protection device supply"),
}

CAPACITOR_PARTS = {
    "100nF": ("C14663", "CC0603KRX7R9BB104", "YAGEO",
              "Capacitor_SMD:C_0603_1608Metric"),
    "2.2uF": ("C23630", "CL10A225KO8NNNC", "Samsung Electro-Mechanics",
              "Capacitor_SMD:C_0603_1608Metric"),
    "10uF": ("C15850", "CL21A106KAYNNNE", "Samsung Electro-Mechanics",
             "Capacitor_SMD:C_0805_2012Metric"),
    "22uF": ("C380359", "TCC1206X5R226M250HT", "CCTC",
             "Capacitor_SMD:C_1206_3216Metric"),
}


def _parts():
    parts = {
        "U1": _part(
            "%s:IP5306" % LIBRARY_NAME,
            "%s:ESOP-8_3.9x4.9mm_P1.27mm_EP2.09x2.09mm" % LIBRARY_NAME,
            "IP5306", "IP5306", "INJOINIC", "C181692"),
        "U2": _part(
            "%s:DW01A" % LIBRARY_NAME, "Package_TO_SOT_SMD:SOT-23-6",
            "DW01A", "DW01A", "PUOLOP", "C351410"),
        "U3": _part(
            "%s:LM393" % LIBRARY_NAME,
            "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            "LM393", "LM393DR2G", "onsemi", "C7955"),
        "U4": _part(
            "%s:TLV431A" % LIBRARY_NAME, "Package_TO_SOT_SMD:SOT-23",
            "TLV431A", "TLV431AIDBZR", "Texas Instruments", "C56765"),
        "L1": _part(
            "Device:L", "%s:L_Sunlord_SWPA8040S" % LIBRARY_NAME,
            "1uH", "SWPA8040S1R0NT", "Sunlord", "C96968"),
        "Q1": _part(
            "%s:AO3415A" % LIBRARY_NAME, "Package_TO_SOT_SMD:SOT-23",
            "AO3415A", "AO3415A", "Alpha & Omega Semiconductor", "C133233"),
        "Q2": _part(
            "Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23",
            "AO3400A", "AO3400A", "Alpha & Omega Semiconductor", "C20917"),
        "Q6": _part(
            "%s:AO3415A" % LIBRARY_NAME, "Package_TO_SOT_SMD:SOT-23",
            "AO3415A", "AO3415A", "Alpha & Omega Semiconductor", "C133233"),
        "Q7": _part(
            "Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23",
            "AO3400A", "AO3400A", "Alpha & Omega Semiconductor", "C20917"),
        "Q8": _part(
            "Transistor_FET:AO3401A", "Package_TO_SOT_SMD:SOT-23",
            "AO3401A", "AO3401A", "Alpha & Omega Semiconductor", "C15127"),
        "SW1": _part(
            "%s:SW_Push_4P" % LIBRARY_NAME,
            "%s:SW_TS-1187A_5.1x5.1mm" % LIBRARY_NAME,
            "TS-1187A-B-A-B", "TS-1187A-B-A-B", "XKB Connection", "C318884"),
        "J3": _part(
            "Connector_Generic:Conn_01x02",
            "Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical",
            "B2P-VH(LF)(SN)", "B2P-VH(LF)(SN)", "JST", "C160315"),
    }
    for reference in ("J1", "J2"):
        parts[reference] = _part(
            "Connector:USB_C_Receptacle_USB2.0_16P",
            "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
            "TYPE-C-31-M-12", "TYPE-C-31-M-12", "Korean Hroparts Elec",
            "C165948")
    for index in range(3, 3 + PROTECTION_PACKAGES):
        parts["Q%d" % index] = _part(
            "%s:AO8810" % LIBRARY_NAME, "Package_SO:TSSOP-8_3x3mm_P0.65mm",
            "AO8810", "AO8810", "Alpha & Omega Semiconductor", "C21426")
    for index in range(1, 5):
        parts["D%d" % index] = _part(
            "Device:LED", "LED_SMD:LED_0603_1608Metric",
            "KT-0603G", "KT-0603G", "Hubei KENTO Elec", "C12624")
    parts["D5"] = _part(
        "Device:LED", "LED_SMD:LED_0603_1608Metric",
        "KT-0603R", "KT-0603R", "Hubei KENTO Elec", "C2286")
    for index in range(6, 12):
        parts["D%d" % index] = _part(
            "%s:TPD1E10B06" % LIBRARY_NAME,
            "%s:TI_X1SON-2_1.0x0.6mm_P0.65mm" % LIBRARY_NAME,
            "TPD1E10B06DPYR", "TPD1E10B06DPYR", "Texas Instruments", "C48260")
    for index, (value, _) in sorted(_CAPACITORS.items()):
        lcsc, mpn, manufacturer, footprint = CAPACITOR_PARTS[value]
        parts["C%d" % index] = _capacitor(
            value, footprint, lcsc, mpn, manufacturer)
    for index, value in sorted(_RESISTOR_VALUES.items()):
        lcsc, mpn = RESISTOR_PARTS[value]
        parts["R%d" % index] = _resistor(value, lcsc, mpn)
    for index in range(1, 12):
        parts["TP%d" % index] = _part(
            "Connector:TestPoint", "TestPoint:TestPoint_Pad_D1.0mm",
            "TestPoint", in_bom=False)
    for index in range(1, 5):
        parts["H%d" % index] = _part(
            "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3",
            "MountingHole_M3", in_bom=False)
    for index in range(1, 8):
        parts["#FLG%d" % index] = _part(
            "power:PWR_FLAG", "", "PWR_FLAG", in_bom=False, on_board=False)
    return parts


PARTS = _parts()


def _nets():
    #: The system reference: the pack negative. Everything the converter and
    #: the indicators return to, and the shell of both receptacles.
    ground = [
        "U1.%s" % IP5306_PINS["GND"], "U3.%s" % LM393_PINS["V-"], "U4.3",
        "Q2.2", "Q7.2", "SW1.3", "SW1.4",
        "R1.2", "R2.2", "R8.2", "R14.2", "R19.1",
        "C1.2", "C2.2", "C4.2", "C5.2", "C6.2", "C7.2", "C8.2", "C9.2",
        "C10.2", "C11.2", "C12.2", "C13.2", "C14.2", "C15.2",
        "D6.1", "D7.1", "D8.1", "D9.1", "D10.1", "D11.1",
        "TP2.1", "TP6.1", "TP11.1", "#FLG1.1",
    ]
    for reference in ("J1", "J2"):
        for pin in USB_C_PINS["GND"] + USB_C_PINS["SHIELD"]:
            ground.append("%s.%s" % (reference, pin))

    #: The conductor the source drives, ahead of the input switch.
    vbus = ["R3.1", "D6.2", "Q1.2", "C3.2",
            "U3.%s" % LM393_PINS["V+"], "C1.1", "R4.1", "R5.1", "R9.1",
            "TP1.1", "#FLG2.1"]
    for pin in USB_C_PINS["VBUS"]:
        vbus.append("J1.%s" % pin)

    #: The charger input, behind the switch the advertisement gates.
    vin = ["Q1.3", "C5.1", "C6.1", "U1.%s" % IP5306_PINS["VIN"], "TP3.1",
           "#FLG3.1"]

    #: The cell's positive terminal. Every part on it is rated above the
    #: highest voltage the protection device allows the cell to reach.
    bat = ["J3.1", "U1.%s" % IP5306_PINS["BAT"], "L1.2", "C7.1", "C8.1",
           "R10.1", "R18.1", "Q8.2", "R12.2", "TP4.1", "TP10.1",
           "#FLG4.1"]

    #: The cell's negative terminal, inside the protection switch.
    celln = ["J3.2", "U2.%s" % DW01A_PINS["GND"], "C17.2", "TP5.1",
             "#FLG5.1"]

    #: The converter output, ahead of the enable switch.
    vout = ["U1.%s" % IP5306_PINS["VOUT"], "C10.1", "C11.1", "C12.1",
            "C13.1", "Q6.2", "R17.2", "C16.2", "TP7.1"]

    #: The output port's supply, behind the enable switch.
    vout_sw = ["Q6.3", "R15.1", "R20.1", "R21.1", "D9.2",
               "TP8.1", "TP9.1", "#FLG7.1"]
    for pin in USB_C_PINS["VBUS"]:
        vout_sw.append("J2.%s" % pin)

    nets = {
        "GND": ground,
        "VBUS": vbus,
        "VIN": vin,
        "BAT": bat,
        "CELLN": celln,
        "VOUT": vout,
        "VOUT_SW": vout_sw,
        # what the source advertises, and the reference it is read against
        "CC1": ["J1.A5", "R1.1", "D7.2", "U3.%s" % LM393_PINS["INA-"]],
        "CC2": ["J1.B5", "R2.1", "D8.2", "U3.%s" % LM393_PINS["INB-"]],
        "VREF": ["R4.2", "C2.1", "U4.1", "U4.2",
                 "U3.%s" % LM393_PINS["INA+"],
                 "U3.%s" % LM393_PINS["INB+"]],
        "ADV_3A": ["U3.%s" % LM393_PINS["OUTA"],
                   "U3.%s" % LM393_PINS["OUTB"], "R6.2", "R7.1"],
        # input switch gate, and the damper across the source
        "VIN_G": ["Q1.1", "R5.2", "R6.1", "C3.1"],
        "VBUS_DAMP": ["R3.2", "C4.1"],
        # input-rejected indicator
        "FAULT_G": ["Q2.1", "R7.2", "R8.1"],
        "FAULT_K": ["Q2.3", "D5.1"],
        "FAULT_A": ["D5.2", "R9.2"],
        # converter switch node, and the cell-rail damper
        "SW": ["U1.%s" % IP5306_PINS["SW"], "L1.1"],
        "BAT_DAMP": ["R10.2", "C9.1"],
        # state-of-charge indicators: four across three drivers, in
        # antiparallel pairs, as the controller's own reference wires them
        "LED1": ["U1.%s" % IP5306_PINS["LED1"], "D1.2", "D2.1"],
        "LED2": ["U1.%s" % IP5306_PINS["LED2"], "D3.2", "D4.1"],
        "LED3": ["U1.%s" % IP5306_PINS["LED3"], "D1.1", "D2.2", "D3.1",
                 "D4.2"],
        # push button
        "BTN": ["SW1.1", "SW1.2", "R11.1", "R12.1", "Q8.1"],
        "KEY": ["U1.%s" % IP5306_PINS["KEY"], "R11.2", "C14.1"],
        # output enable latch
        "SET_D": ["Q8.3", "R13.1"],
        "SET": ["R13.2", "R14.1", "R15.2", "C15.1", "Q7.1"],
        "OUT_G_D": ["Q7.3", "R16.1"],
        "OUT_G": ["R16.2", "R17.1", "C16.1", "Q6.1"],
        # cell protection
        "PROT_VCC": ["R18.2", "U2.%s" % DW01A_PINS["VCC"], "C17.1",
                     "#FLG6.1"],
        "PROT_OD": ["U2.%s" % DW01A_PINS["OD"]],
        "PROT_OC": ["U2.%s" % DW01A_PINS["OC"]],
        "PROT_VM": ["U2.%s" % DW01A_PINS["VM"], "R19.2"],
        # what the output port advertises
        "OUT_CC1": ["J2.A5", "R20.2", "D10.2"],
        "OUT_CC2": ["J2.B5", "R21.2", "D11.2"],
    }
    for index in range(3, 3 + PROTECTION_PACKAGES):
        for pin in AO8810_PINS["S1"]:
            nets["CELLN"].append("Q%d.%s" % (index, pin))
        for pin in AO8810_PINS["S2"]:
            nets["GND"].append("Q%d.%s" % (index, pin))
        # Each package's two drains are common inside it, so they are one
        # net per package rather than one net across the three: tying the
        # midpoints together would need copper past the source pads of every
        # package, and the packages already share the current at both ends.
        nets["PROT_D%d" % index] = ["Q%d.%s" % (index, pin)
                                    for pin in AO8810_PINS["D"]]
        nets["PROT_OD"].append("Q%d.%s" % (index, AO8810_PINS["G1"]))
        nets["PROT_OC"].append("Q%d.%s" % (index, AO8810_PINS["G2"]))
    return nets


NETS = _nets()

#: Receptacle pads and device pins the design deliberately leaves
#: unconnected.
NO_CONNECT = tuple(
    "%s.%s" % (reference, pin)
    for reference in ("J1", "J2") for pin in USB_C_UNUSED
) + ("U2.%s" % DW01A_PINS["TD"],)


# ---------------------------------------------------------------------------
# what the board declares about itself

#: The Type-C source contract at the receptacle. The board never sees more
#: than this: a Type-C source supplies vSafe5V until something negotiates
#: otherwise, and this board negotiates nothing.
INPUT_SUPPLY = {"min_v": 4.75, "max_v": 5.5}

#: Type-C sink advertisement thresholds, from the specification's own table
#: of what a sink reads on its CC conductor.
CC_THRESHOLD_1_5A_V = 0.66
CC_THRESHOLD_3_0A_V = 1.23

#: The sink termination the specification requires, and its tolerance.
CC_SINK_TERMINATION_OHM = 5100.0

#: The source pull-ups a sink may meet, in the resistor form: value, the
#: tolerance the specification permits, and the current being advertised.
CC_PULL_UP_FORMS = {
    "default": {"ohm": 56000.0, "tolerance": 0.20, "advertises_a": 0.5},
    "1.5A": {"ohm": 22000.0, "tolerance": 0.05, "advertises_a": 1.5},
    "3.0A": {"ohm": 10000.0, "tolerance": 0.05, "advertises_a": 3.0},
}

#: The current sources a Type-C source may present instead of a resistor.
CC_PULL_UP_CURRENTS = {
    "default": {"amp": 80.0e-6, "tolerance": 0.20, "advertises_a": 0.5},
    "1.5A": {"amp": 180.0e-6, "tolerance": 0.08, "advertises_a": 1.5},
    "3.0A": {"amp": 330.0e-6, "tolerance": 0.08, "advertises_a": 3.0},
}

#: The advertisement the board requires before it closes the input switch.
#: Below it the board takes nothing from the source but the detector's own
#: quiescent current.
REQUIRED_ADVERTISEMENT_A = 3.0

#: The pull-up the output port presents, and what it advertises.
OUTPUT_ADVERTISEMENT_A = 3.0

#: The cell the board is designed around: one lithium-ion cell. The ceiling
#: is the protection device's own over-charge threshold rather than the
#: charger's target, because the ceiling is what parts on the cell rail have
#: to survive.
CELL = {
    "nominal_v": 3.7,
    "charge_target_v": 4.2,
    "protection_ceiling_v": 4.35,
    "board_floor_v": 3.0,
}

#: What the board is rated to deliver, and the port voltage it is rated at.
RATED_OUTPUT_A = 2.0
RATED_OUTPUT_V = 5.0

#: A budget, not a measurement: the conversion efficiency the cell-side
#: current is computed at. The controller's datasheet states a peak figure
#: and no minimum, so this floor is the board's own.
BOOST_EFFICIENCY_FLOOR = 0.85

#: Converter operating point the ripple and peak-current figures come from.
SWITCHING_FREQUENCY_HZ = 500.0e3
INDUCTANCE_H = 1.0e-6
INDUCTANCE_TOLERANCE = 0.30

#: The highest ambient the board's ratings are claimed at, and the ambient
#: the sustained-output requirement is evaluated at.
AMBIENT_MAX_C = 40.0
ROOM_AMBIENT_C = 25.0

#: A budget, not a measurement: how much charge a healthy lithium-ion cell
#: loses to self-discharge, and the pack the standby figure is judged
#: against. Both are the board's declarations - the cell is not part of this
#: design and no cell datasheet is frozen here.
CELL_SELF_DISCHARGE_PER_MONTH = 0.02
CELL_CAPACITY_AH = 2.5

#: Push-button behaviour the controller defines, restated because the filter
#: across the button is sized against it.
KEY_IGNORE_BELOW_S = 0.050
KEY_LONG_PRESS_S = 2.0

#: How long the enable latch must hold its set state with no feedback, so a
#: press that starts the converter still latches when the press ends. A
#: design target: the controller states no converter start-up time.
LATCH_HOLD_TARGET_S = 0.5

#: Time constants the gate networks are required to stay above, so neither
#: switch closes faster than the capacitance behind it can be charged.
SWITCH_SLEW_TARGET_S = 0.5e-3

#: A budget, not a measurement: the inductance of the cable and the mated
#: connector a live source arrives through. It is what the input damper is
#: sized against.
CABLE_INDUCTANCE_H = 1.0e-6

#: A budget, not a measurement: how long the converter's control loop is
#: allowed to take to answer a load step. The controller's datasheet states
#: no loop response time, so the output capacitance is sized against this
#: declaration instead: five periods at the declared switching frequency.
CONVERTER_RESPONSE_BUDGET_S = 10.0e-6

#: The output level the converter's own datasheet treats as an overload,
#: which is what a transient dip has to stay above.
CONVERTER_OVERLOAD_FLOOR_V = 4.4

#: Nets that must reach a probe with the board assembled.
PROBE_REQUIRED_NETS = ("VBUS", "VIN", "BAT", "CELLN", "VOUT", "VOUT_SW",
                       "GND")

#: Probe pairs that carry one net and exist so current and voltage can be
#: measured at separate points of the same conductor. Efficiency is a
#: ratio of two powers, so the cell side and the output side each need a
#: pair, and the reference needs one too.
KELVIN_PROBE_PAIRS = (("TP4", "TP10"), ("TP8", "TP9"), ("TP2", "TP6"))

#: The protection switch, and the two nets only it bridges.
PROTECTION_REFERENCES = tuple(
    "Q%d" % index for index in range(3, 3 + PROTECTION_PACKAGES))
CELL_NEGATIVE_NET = "CELLN"
SYSTEM_GROUND_NET = "GND"

#: Every net the board treats as a supply.
POWER_NETS = ("VBUS", "VIN", "BAT", "VOUT", "VOUT_SW", "GND", "CELLN")

#: Nets whose highest potential is the cell rail rather than the 5 V side.
CELL_RAIL_NETS = ("BAT", "PROT_VCC", "SET", "SET_D", "BTN")

#: Nets that carry the cell-side current, and the ones that carry the output
#: current. Conductor sizing is judged over these.
CELL_CURRENT_NETS = ("BAT", "SW", "CELLN", "GND")
OUTPUT_CURRENT_NETS = ("VOUT", "VOUT_SW")

#: The build this board is costed and supplied for.
PLANNED_BUILD_QUANTITY = 50

#: What the assembler has to do beyond one reflow of the front side.
ASSEMBLY_POLICY = {
    "placement_sides": 1,
    # the cell connector, and the two receptacles whose shell posts pass
    # through the board: three parts that need a through-hole operation
    "through_hole_soldered_parts": 3,
}

CONNECTOR_FUNCTION_NETS = {
    "J1": {"VBUS": "VBUS", "CC1": "CC1", "CC2": "CC2", "GND": "GND"},
    "J2": {"VBUS": "VOUT_SW", "CC1": "OUT_CC1", "CC2": "OUT_CC2",
           "GND": "GND"},
    "J3": {"CELL_POSITIVE": "BAT", "CELL_NEGATIVE": "CELLN"},
}

#: A conductor that enters the board and needs no clamp of its own, and why.
ESD_EXEMPT = {
    "GND": "the reference the clamps divert into",
    "CELLN": "inside the cell connector's own housing, reachable only by "
             "unmating the cell; it is not a user-accessible conductor",
    "BAT": "inside the cell connector's own housing, reachable only by "
           "unmating the cell; it is not a user-accessible conductor",
}


def entering_conductors():
    """Every conductor that enters the board, and the connector it enters by.

    Each one either carries a clamp or appears in ESD_EXEMPT with a reason.
    """
    entering = {}
    for reference, functions in CONNECTOR_FUNCTION_NETS.items():
        for net in functions.values():
            entering.setdefault(net, []).append(reference)
    return {net: sorted(refs) for net, refs in entering.items()}


def pin_to_net():
    mapping = {}
    for net_name, pin_refs in NETS.items():
        for pin_ref in pin_refs:
            if pin_ref in mapping:
                raise ValueError(
                    "pin %s assigned to both %s and %s"
                    % (pin_ref, mapping[pin_ref], net_name))
            mapping[pin_ref] = net_name
    for pin_ref in NO_CONNECT:
        if pin_ref in mapping:
            raise ValueError(
                "pin %s is both no-connect and on net %s"
                % (pin_ref, mapping[pin_ref]))
    return mapping
