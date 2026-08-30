# Sources — Single-Cell Li-Ion Power Bank

The evidence this board's design will have to cite. **Classes of document, not
documents:** the specific parts are not chosen yet, so naming a datasheet here
would be choosing one.

A number that reaches the board carries its provenance: source, document id or
URL, retrieval date, units, and the condition it applies under. A number without
that is not evidence, and no live network lookup may change a validation or
release result.

| Kind of source | What the design needs from it |
|---|---|
| Charger / power-path / output-stage IC datasheets | The brief requires respecting "the layout guidance of the selected power ICs", so the specific layout, thermal, and external-component sections of whatever devices are chosen are load-bearing evidence, not background reading. |
| USB Type-C connector and cable specification (sink-side requirements) | The USB-C input's CC configuration, current advertisement, and connector requirements determine how much input power the board may legitimately draw. |
| Li-ion cell or pack datasheet | Charge voltage, charge current, discharge current, and temperature window all come from the cell, and every charger and protection threshold must be justified against it. |
| Datasheets for the battery protection implementation chosen — protection IC, protected-pack specification, and any switching or interrupting elements it uses | Protection thresholds, delay times, and the series resistance of whatever conducts the discharge current set both the safety behavior and the achievable output current at low cell voltage. |
| Passive component datasheets with derating curves, for the energy-storage and filtering parts the chosen conversion topology requires | A 2 A output claim depends on saturation current at temperature for any magnetics used and on real capacitance after DC-bias derating, not on nominal catalog values. |
| Current-sense element specifications, if fuel gauging uses one | Sense resistance, tolerance, and power rating affect both indication accuracy and the output path's loss budget. |
| PCB fabricator capability documentation | Minimum trace/space, copper weight options, and available stackups for the chosen layer count bound the high-current conductor design. |
| Conductor sizing and thermal reference data (trace width vs current and temperature rise) | The charge and discharge paths need a defensible width/copper-weight derivation rather than an eyeballed one. |
| Land pattern / footprint standards and connector mechanical drawings | The USB-C input interface, the output port, the button, and the cell attachment all need footprints traceable to a published drawing or standard. |
| Li-ion battery safety and transport standards | "Battery safety" is a listed stressor; any claim about safe charging, fault response, or shippability should point at a recognized standard rather than at intuition. |
| Bench measurement records from bring-up | Efficiency, output current under load at low cell voltage, temperature rise, and fuel-indication accuracy are claims that only measured data can settle. |

## Recording a source, once one is chosen

Replace the class with the actual document — manufacturer, part number, revision
and date — and state the fact taken from it, in the units the document uses.
Keep the class row: it says why the document was needed.

JLCPCB-wide process limits are **not** recorded here. They live in the toolkit's
`profiles/jlcpcb/`, with their own provenance; this board records only its own
tighter targets and its own selected options. A limit copied into two places is
a rival threshold, and the toolkit has a gate that says so.
