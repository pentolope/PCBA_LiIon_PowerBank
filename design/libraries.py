"""Symbols and land patterns this board draws itself, from the package
drawings frozen in `evidence/`.

Every dimension below cites the document it came from. A symbol is drawn
here when the installed KiCad library has no symbol for the part, or has one
whose pin numbering or unit split does not match the package the board
actually fits; a land pattern is drawn here when the drawing states a
recommended pattern that no installed footprint reproduces.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_NAME = "LiIonPowerBank"
SYMBOL_LIB_PATH = os.path.join(REPO_ROOT, "library",
                               LIBRARY_NAME + ".kicad_sym")
FOOTPRINT_DIR = os.path.join(REPO_ROOT, "library", LIBRARY_NAME + ".pretty")
SYM_LIB_TABLE = os.path.join(REPO_ROOT, "sym-lib-table")
FP_LIB_TABLE = os.path.join(REPO_ROOT, "fp-lib-table")

SYMBOL_LIB_VERSION = "20251024"
FOOTPRINT_VERSION = "20260206"
GENERATOR = "liion-power-bank-design-source"

# IP5306 V1.10, pin definition table: VIN, LED1, LED2, LED3, KEY, BAT, SW,
# VOUT on pins 1..8 and the power pad connected to GND. The pad is drawn as
# pin 9 because it is the device's only ground connection and a symbol that
# leaves it off cannot be checked against the land pattern.
IP5306_SYMBOL_NAME = "IP5306"
IP5306_PINS = [("1", "VIN", "power_in", "left"),
               ("6", "BAT", "power_in", "left"),
               ("7", "SW", "passive", "right"),
               ("8", "VOUT", "power_out", "right"),
               ("2", "LED1", "output", "right"),
               ("3", "LED2", "output", "right"),
               ("4", "LED3", "output", "right"),
               ("5", "KEY", "input", "left"),
               ("9", "GND", "power_in", "bottom")]
IP5306_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                    "309666add984eaea02a8f06d99102496.pdf")

# DW01A Rev B, pin configuration table: OD, VM, OC, TD, VCC, GND on pins
# 1..6. TD is a test pin and the datasheet's own application circuit leaves
# it open, so it is drawn and declared no-connect rather than omitted.
DW01A_SYMBOL_NAME = "DW01A"
DW01A_PINS = [("5", "VCC", "power_in", "left"),
              ("2", "VM", "input", "left"),
              ("4", "TD", "input", "left"),
              ("1", "OD", "output", "right"),
              ("3", "OC", "output", "right"),
              ("6", "GND", "power_in", "bottom")]
DW01A_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                   "0d2b2b5e8d1207bf276387cb4ff3a495.pdf")

# LM393 in one symbol rather than the installed library's three units. The
# design source places exactly one symbol per package, so a part split into
# units would leave two thirds of its pins unplaced and its supply pins on a
# unit nothing instantiates.
LM393_SYMBOL_NAME = "LM393"
LM393_PINS = [("3", "INA+", "input", "left"),
              ("2", "INA-", "input", "left"),
              ("5", "INB+", "input", "left"),
              ("6", "INB-", "input", "left"),
              ("1", "OUTA", "open_collector", "right"),
              ("7", "OUTB", "open_collector", "right"),
              ("8", "V+", "power_in", "top"),
              ("4", "V-", "power_in", "bottom")]
LM393_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                   "0a7f69005bd54ef2bf3e8b1a5a2f8965.pdf")

# TLV431 SLVS139V, "6 Pin Configuration and Functions", DBZ (SOT-23-3)
# package: REF, CATHODE, ANODE on pins 1, 2, 3.
TLV431_SYMBOL_NAME = "TLV431A"
TLV431_PINS = [("1", "REF", "input", "left"),
               ("2", "K", "passive", "top"),
               ("3", "A", "passive", "bottom")]
TLV431_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                    "1f0b6b30afca4cb79b547decc5f49aec.pdf")

# AO3415A Rev 3.0, SOT23 pin figure: gate, source, drain on pins 1, 2, 3.
AO3415A_SYMBOL_NAME = "AO3415A"
AO3415A_PINS = [("1", "G", "input", "left"),
                ("2", "S", "passive", "top"),
                ("3", "D", "passive", "bottom")]
AO3415A_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                     "4fe5043a2c3149108be834737fd7b448.pdf")

# AO8810 Rev 8, TSSOP-8 top view: D1/D2 on pins 1 and 8, S1 on 2 and 3, G1
# on 4, G2 on 5, S2 on 6 and 7. Both drain pins and both pins of each source
# are drawn, so the schematic and the land pattern agree pad for pad instead
# of relying on a note that the rest are connected internally.
AO8810_SYMBOL_NAME = "AO8810"
AO8810_PINS = [("4", "G1", "input", "left"),
               ("5", "G2", "input", "left"),
               ("2", "S1", "passive", "left"),
               ("3", "S1", "passive", "left"),
               ("6", "S2", "passive", "right"),
               ("7", "S2", "passive", "right"),
               ("1", "D", "passive", "right"),
               ("8", "D", "passive", "right")]
AO8810_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                    "26d8ed0c631e45aaacbd4f8082ccbf0c.pdf")

# A single-throw push button whose land pattern carries four pads: the two
# pads of each terminal are separate pins so every pad on the board belongs
# to a pin the schematic names.
SWITCH_SYMBOL_NAME = "SW_Push_4P"
SWITCH_PINS = [("1", "A", "passive", "left"),
               ("2", "A", "passive", "left"),
               ("3", "B", "passive", "right"),
               ("4", "B", "passive", "right")]
SWITCH_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                    "56c8799ae5193945a16a1ffbe378246a.pdf")

TVS_SYMBOL_NAME = "TPD1E10B06"
TVS_DATASHEET = "https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf"

# TI DPY0002A, drawing 4224561/C (SLLSEB1G): land pattern 2x (0.3) wide by
# 2x (0.5) tall on (0.7) centres; package outline 1.1/0.9 by 0.7/0.5.
X1SON_FOOTPRINT_NAME = "TI_X1SON-2_1.0x0.6mm_P0.65mm"
X1SON_PAD_SIZE_MM = (0.30, 0.50)
X1SON_PAD_PITCH_MM = 0.70
X1SON_BODY_MM = (1.10, 0.70)
X1SON_COURTYARD_MARGIN_MM = 0.15

# IP5306 V1.10 package information: D 4.70/4.90/5.10 body length, E1
# 3.70/3.90/4.10 body width, E 5.80/6.00/6.20 lead span, e 1.27 BSC, b
# 0.39-0.48 lead width, L 0.50/0.60/0.80 foot length, D1 = E2 = 2.09
# exposed pad. The lead pads are the JEDEC MS-012 pattern for that lead span
# and the exposed pad is the drawing's own 2.09 square, which is why this is
# drawn rather than taken from the installed library: no installed SOIC-8
# with an exposed pad carries a 2.09 square one.
ESOP8_FOOTPRINT_NAME = "ESOP-8_3.9x4.9mm_P1.27mm_EP2.09x2.09mm"
ESOP8_PITCH_MM = 1.27
ESOP8_PAD_SIZE_MM = (1.95, 0.60)
ESOP8_PAD_CENTRE_X_MM = 2.475
#: The exposed pad takes less paste than copper, because a single aperture
#: over its whole area floats the package.
ESOP8_PASTE_PAD_MM = 1.85
ESOP8_EXPOSED_PAD_MM = 2.09
ESOP8_BODY_MM = (4.90, 3.90)
ESOP8_COURTYARD_MARGIN_MM = 0.25

# Sunlord SMD power inductor catalogue, shape and dimensions table:
# SWPA8040S is 8.0+/-0.3 by 8.0+/-0.3 by 4.2 max, and its recommended
# land pattern is a = 3.8 between the pads, b = 2.2 pad width, c = 7.5
# pad length, so the pads sit on 6.0 centres.
INDUCTOR_FOOTPRINT_NAME = "L_Sunlord_SWPA8040S"
INDUCTOR_PAD_SIZE_MM = (2.20, 7.50)
INDUCTOR_PAD_PITCH_MM = 6.00
INDUCTOR_BODY_MM = (8.00, 8.00)
INDUCTOR_COURTYARD_MARGIN_MM = 0.30

# XKB TS-1187A drawing, "P.C.B LAYOUT TOP VIEW": the four pads span 7.0
# outside and 5.0 inside across the part, and 4.5 outside and 3.0
# inside along it, so each pad is 1.00 by 0.75 and the centres are 6.00
# and 3.75 apart. Body 5.1 +/-0.05 square.
SWITCH_FOOTPRINT_NAME = "SW_TS-1187A_5.1x5.1mm"
SWITCH_PAD_SIZE_MM = (1.00, 0.75)
SWITCH_PAD_SPAN_X_MM = 6.00
SWITCH_PAD_SPAN_Y_MM = 3.75
SWITCH_BODY_MM = (5.10, 5.10)
SWITCH_COURTYARD_MARGIN_MM = 0.25


def _effects():
    return ("\n\t\t\t\t(effects\n\t\t\t\t\t(font\n"
            "\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t)\n\t\t\t\t)")


def _symbol_property(key, value, index, hide):
    hidden = "\n\t\t\t(hide yes)" if hide else ""
    return ('\t\t(property "%s" "%s"\n\t\t\t(at 0 %.2f 0)%s\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            % (key, value, 17.78 - 2.54 * index, hidden))


def _pin_text(kind, x, y, angle, name, number):
    return ('\t\t\t(pin %s line\n\t\t\t\t(at %.2f %.2f %d)\n'
            '\t\t\t\t(length 2.54)\n'
            '\t\t\t\t(name "%s"%s\n\t\t\t\t)\n'
            '\t\t\t\t(number "%s"%s\n\t\t\t\t)\n\t\t\t)\n'
            % (kind, x, y, angle, name, _effects(), number, _effects()))


def _rectangle(half_x, half_y):
    return ('\t\t\t(rectangle\n\t\t\t\t(start %.2f %.2f)\n'
            '\t\t\t\t(end %.2f %.2f)\n'
            '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type '
            'default)\n\t\t\t\t)\n'
            '\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n'
            '\t\t\t)\n' % (-half_x, half_y, half_x, -half_y))


def _placed_pin(number, pin_name, kind, side, placed, half_x, half_y):
    """One pin, on the side the caller asked for, stepping down that side."""
    index = placed.setdefault(side, 0)
    placed[side] = index + 1
    if side == "left":
        return _pin_text(kind, -half_x - 2.54, half_y - 2.54 * (index + 1),
                         0, pin_name, number)
    if side == "right":
        return _pin_text(kind, half_x + 2.54, half_y - 2.54 * (index + 1),
                         180, pin_name, number)
    if side == "top":
        return _pin_text(kind, -half_x + 2.54 * (index + 1), half_y + 2.54,
                         270, pin_name, number)
    return _pin_text(kind, -half_x + 2.54 * (index + 1), -half_y - 2.54,
                     90, pin_name, number)


def _boxed_symbol(name, reference_prefix, value, footprint, datasheet,
                  pins, description, footprint_filter=None):
    """A rectangular symbol with its pins on the sides the caller chose."""
    counts = {}
    for _, _, _, side in pins:
        counts[side] = counts.get(side, 0) + 1
    half_y = 1.27 * (max(counts.get("left", 0), counts.get("right", 0)) + 1)
    half_x = 1.27 * (max(counts.get("top", 0), counts.get("bottom", 0)) + 3)
    half_x = max(half_x, 6.35)
    half_y = max(half_y, 3.81)
    out = ['\t(symbol "%s"\n' % name,
           '\t\t(pin_names\n\t\t\t(offset 0.254)\n\t\t)\n',
           '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n']
    out.append(_symbol_property("Reference", reference_prefix, 0, False))
    out.append(_symbol_property("Value", value, 1, False))
    out.append(_symbol_property("Footprint", footprint, 2, True))
    out.append(_symbol_property("Datasheet", datasheet, 3, True))
    out.append(_symbol_property("Description", description, 4, True))
    if footprint_filter:
        out.append('\t\t(property "ki_fp_filters" "%s"\n'
                   '\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n'
                   '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 '
                   '1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n' % footprint_filter)
    out.append('\t\t(symbol "%s_0_1"\n' % name)
    out.append(_rectangle(half_x, half_y))
    out.append("\t\t)\n")
    out.append('\t\t(symbol "%s_1_1"\n' % name)
    placed = {}
    for number, pin_name, kind, side in pins:
        out.append(_placed_pin(number, pin_name, kind, side, placed,
                               half_x, half_y))
    out.append("\t\t)\n\t)\n")
    return "".join(out)


def ip5306_symbol_text():
    return _boxed_symbol(
        IP5306_SYMBOL_NAME, "U", "IP5306",
        "%s:%s" % (LIBRARY_NAME, ESOP8_FOOTPRINT_NAME), IP5306_DATASHEET,
        IP5306_PINS,
        "Power bank controller: switching charger, boost converter and "
        "state-of-charge indicator driver")


def dw01a_symbol_text():
    return _boxed_symbol(
        DW01A_SYMBOL_NAME, "U", "DW01A",
        "Package_TO_SOT_SMD:SOT-23-6", DW01A_DATASHEET, DW01A_PINS,
        "One-cell lithium-ion protection controller",
        footprint_filter="SOT?23*")


def lm393_symbol_text():
    return _boxed_symbol(
        LM393_SYMBOL_NAME, "U", "LM393",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", LM393_DATASHEET, LM393_PINS,
        "Dual differential comparator with open-collector outputs",
        footprint_filter="SOIC*3.9x4.9mm*P1.27mm*")


def tlv431_symbol_text():
    return _boxed_symbol(
        TLV431_SYMBOL_NAME, "U", "TLV431A",
        "Package_TO_SOT_SMD:SOT-23", TLV431_DATASHEET, TLV431_PINS,
        "1.24 V adjustable precision shunt regulator",
        footprint_filter="SOT?23*")


def ao3415a_symbol_text():
    return _boxed_symbol(
        AO3415A_SYMBOL_NAME, "Q", "AO3415A",
        "Package_TO_SOT_SMD:SOT-23", AO3415A_DATASHEET, AO3415A_PINS,
        "-20 V P-channel MOSFET", footprint_filter="SOT?23*")


def ao8810_symbol_text():
    return _boxed_symbol(
        AO8810_SYMBOL_NAME, "Q", "AO8810",
        "Package_SO:TSSOP-8_3x3mm_P0.65mm", AO8810_DATASHEET, AO8810_PINS,
        "20 V common-drain dual N-channel MOSFET",
        footprint_filter="TSSOP*3x3mm*P0.65mm*")


def switch_symbol_text():
    return _boxed_symbol(
        SWITCH_SYMBOL_NAME, "SW", "SW_Push",
        "%s:%s" % (LIBRARY_NAME, SWITCH_FOOTPRINT_NAME), SWITCH_DATASHEET,
        SWITCH_PINS,
        "Momentary push button, one throw, two pads per terminal")


def tvs_symbol_text():
    """A two-terminal unidirectional clamp: cathode on pin 1, anode on 2."""
    name = TVS_SYMBOL_NAME
    out = ['\t(symbol "%s"\n' % name,
           '\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n',
           '\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t\t(hide yes)\n\t\t)\n',
           '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n']
    out.append(_symbol_property("Reference", "D", 0, False))
    out.append(_symbol_property("Value", TVS_SYMBOL_NAME, 1, False))
    out.append(_symbol_property(
        "Footprint", "%s:%s" % (LIBRARY_NAME, X1SON_FOOTPRINT_NAME), 2, True))
    out.append(_symbol_property("Datasheet", TVS_DATASHEET, 3, True))
    out.append(_symbol_property(
        "Description",
        "Single-line 6 V ESD clamp, unidirectional, X1SON-2", 4, True))
    out.append('\t\t(symbol "%s_0_1"\n' % name)
    out.append('\t\t\t(polyline\n\t\t\t\t(pts\n'
               '\t\t\t\t\t(xy -1.27 1.27) (xy -1.27 -1.27)\n\t\t\t\t)\n'
               '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n'
               '\t\t\t\t\t(type default)\n\t\t\t\t)\n'
               '\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n')
    out.append('\t\t\t(polyline\n\t\t\t\t(pts\n'
               '\t\t\t\t\t(xy 1.27 1.27) (xy 1.27 -1.27) (xy -1.27 0) '
               '(xy 1.27 1.27)\n\t\t\t\t)\n'
               '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n'
               '\t\t\t\t\t(type default)\n\t\t\t\t)\n'
               '\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n')
    out.append("\t\t)\n")
    out.append('\t\t(symbol "%s_1_1"\n' % name)
    out.append(_pin_text("passive", -3.81, 0, 0, "K", "1"))
    out.append(_pin_text("passive", 3.81, 0, 180, "A", "2"))
    out.append("\t\t)\n\t)\n")
    return "".join(out)


def symbol_library_text():
    body = "".join([
        ao3415a_symbol_text(),
        ao8810_symbol_text(),
        dw01a_symbol_text(),
        ip5306_symbol_text(),
        lm393_symbol_text(),
        switch_symbol_text(),
        tlv431_symbol_text(),
        tvs_symbol_text(),
    ])
    return ('(kicad_symbol_lib\n\t(version %s)\n\t(generator "%s")\n'
            '\t(generator_version "10.0")\n%s)\n'
            % (SYMBOL_LIB_VERSION, GENERATOR, body))


# ---------------------------------------------------------------------------
# land patterns

def _outline(layer, half_x, half_y, thickness, start_y=None, end_y=None):
    low = -half_y if start_y is None else start_y
    high = half_y if end_y is None else end_y
    return ('\t(fp_rect\n\t\t(start %.4f %.4f)\n\t\t(end %.4f %.4f)\n'
            '\t\t(stroke\n\t\t\t(width %.4f)\n\t\t\t(type solid)\n\t\t)\n'
            '\t\t(fill no)\n\t\t(layer "%s")\n\t)\n'
            % (-half_x, low, half_x, high, thickness, layer))


def _footprint_header(name, descr, tags, attr, ref_y, value_y, size,
                      thickness):
    return ('(footprint "%s"\n\t(version %s)\n\t(generator "%s")\n'
            '\t(generator_version "10.0")\n\t(layer "F.Cu")\n'
            '\t(descr "%s")\n\t(tags "%s")\n\t(attr %s)\n'
            '\t(property "Reference" "REF**"\n\t\t(at 0 %.4f 0)\n'
            '\t\t(layer "F.SilkS")\n\t\t(uuid "")\n'
            '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %.2f %.2f)\n'
            '\t\t\t\t(thickness %.4f)\n\t\t\t)\n\t\t)\n\t)\n'
            '\t(property "Value" "%s"\n\t\t(at 0 %.4f 0)\n'
            '\t\t(layer "F.Fab")\n\t\t(uuid "")\n'
            '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %.2f %.2f)\n'
            '\t\t\t\t(thickness %.4f)\n\t\t\t)\n\t\t)\n\t)\n'
            % (name, FOOTPRINT_VERSION, GENERATOR, descr, tags, attr,
               ref_y, size, size, thickness, name, value_y, size, size,
               thickness))


def _smd_pad(number, x, y, width, height, layers='"F.Cu" "F.Paste" "F.Mask"'):
    return ('\t(pad "%s" smd rect\n\t\t(at %.4f %.4f)\n'
            '\t\t(size %.4f %.4f)\n\t\t(layers %s)\n\t\t(uuid "")\n\t)\n'
            % (number, x, y, width, height, layers))


def x1son_footprint_text():
    half_pitch = X1SON_PAD_PITCH_MM / 2.0
    pad_w, pad_h = X1SON_PAD_SIZE_MM
    body_x, body_y = X1SON_BODY_MM
    court_x = body_x / 2.0 + X1SON_COURTYARD_MARGIN_MM
    court_y = max(body_y, pad_h) / 2.0 + X1SON_COURTYARD_MARGIN_MM
    out = [_footprint_header(
        X1SON_FOOTPRINT_NAME,
        "TI X1SON-2, drawing 4224561/C: 0.3 x 0.5 pads on 0.7 centres",
        "X1SON DPY0002A", "smd", -1.2, 1.2, 0.6, 0.12)]
    out.append(_smd_pad("1", -half_pitch, 0.0, pad_w, pad_h))
    out.append(_smd_pad("2", half_pitch, 0.0, pad_w, pad_h))
    out.append(_outline("F.Fab", body_x / 2.0, body_y / 2.0, 0.1))
    out.append(_outline("F.CrtYd", court_x, court_y, 0.05))
    out.append(')\n')
    return "".join(out)


def esop8_footprint_text():
    pad_w, pad_h = ESOP8_PAD_SIZE_MM
    body_x, body_y = ESOP8_BODY_MM
    court_x = ESOP8_PAD_CENTRE_X_MM + pad_w / 2.0 + ESOP8_COURTYARD_MARGIN_MM
    court_y = body_x / 2.0 + ESOP8_COURTYARD_MARGIN_MM
    out = [_footprint_header(
        ESOP8_FOOTPRINT_NAME,
        "Injoinic eSOP8: 1.27 pitch leads on a 6.0 span with a 2.09 square "
        "exposed pad, from the IP5306 package drawing",
        "eSOP8 SOIC exposed pad", "smd", -court_y - 0.8, court_y + 0.8,
        1.0, 0.15)]
    # pins 1..4 down the left side, 5..8 up the right side, the same order
    # the package drawing numbers them in
    for index in range(4):
        y = ESOP8_PITCH_MM * (index - 1.5)
        out.append(_smd_pad("%d" % (index + 1), -ESOP8_PAD_CENTRE_X_MM, y,
                            pad_w, pad_h))
    for index in range(4):
        y = ESOP8_PITCH_MM * (1.5 - index)
        out.append(_smd_pad("%d" % (index + 5), ESOP8_PAD_CENTRE_X_MM, y,
                            pad_w, pad_h))
    out.append(
        '\t(pad "9" smd rect\n\t\t(at 0 0)\n\t\t(size %.4f %.4f)\n'
        '\t\t(property pad_prop_heatsink)\n'
        '\t\t(layers "F.Cu" "F.Mask")\n\t\t(zone_connect 2)\n'
        '\t\t(uuid "")\n\t)\n'
        % (ESOP8_EXPOSED_PAD_MM, ESOP8_EXPOSED_PAD_MM))
    out.append(_smd_pad("9", 0.0, 0.0, ESOP8_PASTE_PAD_MM,
                        ESOP8_PASTE_PAD_MM, layers='"F.Paste"'))
    out.append(_outline("F.Fab", body_y / 2.0, body_x / 2.0, 0.1))
    out.append(_outline("F.CrtYd", court_x, court_y, 0.05))
    # pin-one mark, outside the courtyard on the silkscreen
    out.append('\t(fp_circle\n\t\t(center %.4f %.4f)\n\t\t(end %.4f %.4f)\n'
               '\t\t(stroke\n\t\t\t(width 0.12)\n\t\t\t(type solid)\n\t\t)\n'
               '\t\t(fill solid)\n\t\t(layer "F.SilkS")\n\t)\n'
               % (-court_x - 0.3, -ESOP8_PITCH_MM * 1.5,
                  -court_x - 0.15, -ESOP8_PITCH_MM * 1.5))
    out.append(')\n')
    return "".join(out)


def inductor_footprint_text():
    pad_w, pad_h = INDUCTOR_PAD_SIZE_MM
    half_pitch = INDUCTOR_PAD_PITCH_MM / 2.0
    body_x, body_y = INDUCTOR_BODY_MM
    court_x = max(body_x / 2.0, half_pitch + pad_w / 2.0) \
        + INDUCTOR_COURTYARD_MARGIN_MM
    court_y = max(body_y, pad_h) / 2.0 + INDUCTOR_COURTYARD_MARGIN_MM
    out = [_footprint_header(
        INDUCTOR_FOOTPRINT_NAME,
        "Sunlord SWPA8040S: 2.4 x 6.6 pads on 6.0 centres under an 8 x 8 "
        "shielded body",
        "inductor SWPA8040", "smd", -court_y - 0.8, court_y + 0.8, 1.0, 0.15)]
    out.append(_smd_pad("1", -half_pitch, 0.0, pad_w, pad_h))
    out.append(_smd_pad("2", half_pitch, 0.0, pad_w, pad_h))
    out.append(_outline("F.Fab", body_x / 2.0, body_y / 2.0, 0.1))
    out.append(_outline("F.CrtYd", court_x, court_y, 0.05))
    out.append(')\n')
    return "".join(out)


def switch_footprint_text():
    pad_w, pad_h = SWITCH_PAD_SIZE_MM
    half_x = SWITCH_PAD_SPAN_X_MM / 2.0
    half_y = SWITCH_PAD_SPAN_Y_MM / 2.0
    body_x, body_y = SWITCH_BODY_MM
    court_x = half_x + pad_w / 2.0 + SWITCH_COURTYARD_MARGIN_MM
    court_y = max(body_y / 2.0, half_y + pad_h / 2.0) \
        + SWITCH_COURTYARD_MARGIN_MM
    out = [_footprint_header(
        SWITCH_FOOTPRINT_NAME,
        "XKB TS-1187A: four 1.4 x 1.0 pads, 6.4 across and 4.5 along, under "
        "a 5.1 x 5.1 body",
        "tactile switch TS-1187A", "smd", -court_y - 0.8, court_y + 0.8,
        1.0, 0.15)]
    for number, sign_x, sign_y in (("1", -1, -1), ("2", -1, 1),
                                   ("3", 1, -1), ("4", 1, 1)):
        out.append(_smd_pad(number, sign_x * half_x, sign_y * half_y,
                            pad_w, pad_h))
    out.append(_outline("F.Fab", body_x / 2.0, body_y / 2.0, 0.1))
    out.append(_outline("F.CrtYd", court_x, court_y, 0.05))
    out.append(')\n')
    return "".join(out)


def sym_lib_table_text():
    return ('(sym_lib_table\n\t(version 7)\n'
            '\t(lib (name "%s")(type "KiCad")'
            '(uri "${KIPRJMOD}/library/%s.kicad_sym")(options "")(descr ""))\n'
            ')\n' % (LIBRARY_NAME, LIBRARY_NAME))


def fp_lib_table_text():
    return ('(fp_lib_table\n\t(version 7)\n'
            '\t(lib (name "%s")(type "KiCad")'
            '(uri "${KIPRJMOD}/library/%s.pretty")(options "")(descr ""))\n'
            ')\n' % (LIBRARY_NAME, LIBRARY_NAME))


def artifacts():
    """Every file this module owns, and the exact text it must contain."""
    produced = {
        SYMBOL_LIB_PATH: symbol_library_text(),
        SYM_LIB_TABLE: sym_lib_table_text(),
        FP_LIB_TABLE: fp_lib_table_text(),
    }
    for name, text in (
            (X1SON_FOOTPRINT_NAME, x1son_footprint_text()),
            (ESOP8_FOOTPRINT_NAME, esop8_footprint_text()),
            (INDUCTOR_FOOTPRINT_NAME, inductor_footprint_text()),
            (SWITCH_FOOTPRINT_NAME, switch_footprint_text())):
        produced[os.path.join(FOOTPRINT_DIR, name + ".kicad_mod")] = text
    return produced


def write():
    os.makedirs(FOOTPRINT_DIR, exist_ok=True)
    for path, text in sorted(artifacts().items()):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    return sorted(artifacts())


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
