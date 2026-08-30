# Architecture — Single-Cell Li-Ion Power Bank

**A worksheet, not a design.** Every line below is a question this board has to
answer, and none of them is answered here. Nothing in this file is a
recommendation, and the order of the sections carries no preference.

The questions were derived from [the brief](../BRIEF.md) and from what this
board is meant to stress in the benchmark:

- charger layout
- power-path routing
- battery safety
- USB-C power

Those are the places where a wrong answer shows up in copper.

Answer them in this file as the design is made, each answer carrying the
evidence that supports it, and record the corresponding choice against its
`OPEN-nn` entry in [board/requirements.md](../board/requirements.md). An answer
without evidence is a guess wearing a document's clothes — and this benchmark is
allowed to refuse an unsupported claim rather than invent one.

## USB-C input and source power

- What is the assumed input voltage range at the USB-C input, and where does that assumption come from?
- How does this sink present itself on CC, and does the design negotiate anything beyond a default source current?
- What input current does the charge stage actually draw at worst case, and is that consistent with what the input advertises or negotiates?
- How does the design behave when the source supplies less than expected — does charge current fold back, and by what mechanism?
- What happens to the input path when the output is loaded at the same time (pass-through), and is that mode supported at all?
- What physical form does the USB-C input take, and what mechanical and electrical review does that chosen part need: retention, footprint land pattern, and shield/ground return?

## Charger stage

- What charge current, termination voltage, and charge profile are chosen, and against which cell datasheet limits are they justified?
- How are pre-charge, timeout, recharge threshold, and fault behavior handled?
- Is charge current derived from a resistor, a register, or the input's available power, and how is that value verified on the bench?
- What does the charger's own datasheet layout section require — for example sense placement, input capacitor position, or any thermal-pad connection the chosen package has — and where is that reproduced in the layout?
- How is charger power dissipation bounded at worst-case input voltage and full charge current, and what surface temperature results?
- If a temperature-sense input exists on the chosen device, is it used, disabled, or left to the pack, and is that choice documented?

## Battery interface and protection

- Where does protection live — on this board, inside the pack, or both — and what is the failure mode if the pack turns out to be unprotected?
- What over-voltage, under-voltage, over-current, and short-circuit thresholds and delays are set, and how do they relate to the cell's stated limits?
- How is the protection actually realized, and what series impedance does that implementation place between the cell and the output stage — enough to affect achievable output current at low cell voltage?
- How does the board recover after a protection event — does it need input power, a button press, or load removal?
- What is the cell attachment method, and what happens to that connection under drop, vibration, or reverse insertion?
- Is cell temperature sensed, and if not, what argument covers charging and high-current discharge outside a safe temperature window?

## Power path and mode arbitration

- Which source feeds the system when input power and battery are both present, and what device or logic arbitrates that?
- Can the board charge and deliver 5 V output simultaneously, and if so how is input power split between the two?
- What prevents reverse current from the battery into the input, or from the output back into the conversion stage?
- How does the board behave on input plug-in and unplug while the output is enabled — any glitch or brownout on the 5 V rail?
- Is the power path integrated into the chosen charger device or built from separate elements, and what is the practicality argument for that split?

## 5 V output stage

- What conversion topology produces the regulated 5 V output from a single Li-ion cell, and what argues for that choice over the alternatives — including the brief's preferred integrated charger/power-path/boost solution?
- What is the worst-case input condition for that stage — lowest usable cell voltage at full rated output current — and what input current does it imply?
- What energy-storage and filtering components does the chosen topology require at that worst case: for a magnetics-based converter, inductor value and saturation rating with derating for temperature and DC bias; for any other realization, the equivalent limiting element?
- What input and output capacitance is required, and what is the actual capacitance after DC bias derating at the operating voltage?
- What is the expected efficiency at 2 A, and therefore the stage's dissipation and temperature rise?
- How is output over-current and short-circuit handled — by the converter's own limit, by an external element, or not at all?
- What output ripple and transient response is targeted, and how will it be measured?

## Fuel/status indication

- How is state of charge estimated: cell voltage, coulomb counting, a dedicated gauge, or something else?
- If current is measured, what sense element is used and how does its resistance and tolerance affect both accuracy and output capability?
- How many indication states are shown, on what medium, and what does each state mean during charge, discharge, and fault?
- What accuracy is claimed for the indication, and what evidence supports that number?
- What is the indication's power draw, and is it gated when the output is disabled?

## Pushbutton and enable logic

- What press semantics are implemented — short press, long press, double press — and what does each do?
- What holds the output enabled between presses, and what is the quiescent current in the disabled state?
- Does the board auto-disable the output under light load, and if so at what threshold and after what delay?
- How is the button debounced, and is any programmable element involved in that logic?
- What is the button's ESD exposure at the enclosure boundary, and how is that path handled?

## High-current layout and loop control

- Which loops carry the highest current and the highest di/dt — charger input, the conversion stage's input and output loops, the battery discharge path — and what is the planned physical area of each?
- For each selected power IC, which specific layout section of its datasheet governs, and how is compliance shown rather than asserted?
- How are the high-current returns arranged relative to sense and control nets so that measurement points are not corrupted by drop?
- What conductor widths and copper weights carry the charge and discharge currents, and what temperature rise do they imply?
- Where do the high-current paths cross layers, and how many vias carry each transition?
- What is the ground strategy — single pour, split, or stitched — and what is the argument for it at the chosen layer count?

## Stackup, floorplan, and mechanics

- What layer count and stackup does the current density and thermal analysis actually support, what is the deciding number, and how does the result compare with the "likely 2 or 4" the brief header and metadata offer?
- What board outline and connector placement does the intended use imply, and what parts of that are assumptions to be flagged as open?
- Where do the cell, the input interface, the output port, the button, and the indication sit relative to each other and to a hypothetical enclosure?
- What keep-outs do the cell attachment and the high-current paths require?
- Which side or sides carry components, and what does that cost in assembly?

## Thermal behavior

- What ambient and enclosure assumption is the thermal analysis run against, and is that assumption declared as unstated by the brief?
- What is total board dissipation in the two worst cases — maximum-rate charging and full-current output — and are they concurrent?
- What copper area, via count, and placement spacing are needed to keep the charger and output-stage devices within their limits?
- Is any thermal foldback or current derating implemented, and does that conflict with the "at least 2 A" requirement?
- How will the thermal claim be verified on hardware?

## Manufacturability, test, and bring-up

- Which fabricator capability set is the design targeted at, and what minimum trace/space, drill, and copper weight does that permit?
- What test points are needed to measure charge current, cell voltage, output current, and efficiency without cutting traces?
- How is the board brought up safely the first time, given a cell is attached — what is the power-up order and what is the abort condition?
- What is the pass/fail test that demonstrates the 5 V output actually sustains at least 2 A, and at what cell voltage?
- How are the fuel indication states and the button state machine tested repeatably?

## Evidence and documentation discipline

- For every value in the design, is there a cited datasheet, standard, or computed result behind it, or is it an assumption to be listed as such?
- Which decisions in this document were open in the brief, and are they recorded as decisions rather than restated as requirements?
- Does the design use "an integrated charger/power-path/boost solution", or depart from it, and what is the practicality argument for whichever way it went?
- What board-specific logic, if any, was tempting to add to the shared toolkit, and where was it kept instead?

## Answers still owed

All of them. See [status.md](status.md).
