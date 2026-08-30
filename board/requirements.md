# Requirements — Single-Cell Li-Ion Power Bank

Two lists. The difference between them is the whole point of this file.

A **fixed requirement** is something [BRIEF.md](../BRIEF.md) asks for. Each one
below quotes the brief text that substantiates it; if a statement cannot be
quoted, it is not a requirement here. An **open decision** is a choice the brief
deliberately left to whoever designs this board.

> Missing details are design freedom, not permission to fabricate unstated user
> requirements.

Promoting a decision into a requirement is the failure this file exists to
prevent. Record a choice under the decision it answers, with the reasoning that
made it — never by adding it to the list above.

Bound to `BRIEF.md` SHA-256 `a83c2729b4cd3572342d1c0d042245c18bb77970d150b0bb1acddd78cdec8627`.

## Fixed by the brief

### REQ-01 — The board is a single-cell Li-ion power bank board.

Brief text:

> Design a single-cell Li-ion power bank board with USB-C input, battery charging

### REQ-02 — The board has a USB-C input.

Brief text:

> power bank board with USB-C input, battery charging, battery protection

### REQ-03 — The board performs battery charging.

Brief text:

> battery charging, battery protection, and regulated 5 V output capable of at least 2 A.

### REQ-04 — The board provides battery protection.

Brief text:

> battery protection, and regulated 5 V output capable of at least 2 A.

### REQ-05 — The board provides a regulated 5 V output capable of at least 2 A.

Brief text:

> regulated 5 V output capable of at least 2 A. Include fuel/status indication

### REQ-06 — The board includes fuel/status indication.

Brief text:

> Include fuel/status indication and a pushbutton-controlled output enable.

### REQ-07 — The output enable is controlled by a pushbutton.

Brief text:

> Include fuel/status indication and a pushbutton-controlled output enable.

### REQ-08 — An integrated charger/power-path/boost solution is to be chosen where practical.

Brief text:

> Choose an integrated charger/power-path/boost solution where practical.

### REQ-09 — The layout must respect the layout guidance of the power ICs actually selected.

Brief text:

> Respect the layout guidance of the selected power ICs

### REQ-10 — High-current loop area must be minimized in the layout.

Brief text:

> Respect the layout guidance of the selected power ICs and minimize high-current loop area.

### REQ-11 — Where the brief is open, the design agent must make and document reasonable engineering decisions rather than invent hidden user requirements.

Brief text:

> where the brief leaves choices open, make and document reasonable engineering decisions rather than inventing hidden user requirements.

### REQ-12 — The repository stays a consumer of the shared PCBA_AutoDesignAndTest toolkit; board-specific logic must not accumulate in the toolkit.

Brief text:

> The repository should remain a consumer of the shared `PCBA_AutoDesignAndTest` toolkit rather than accumulating board-specific logic in the toolkit.

### REQ-13 — The requirements the brief states are to be treated as authoritative.

Brief text:

> Treat stated requirements as authoritative; where the brief leaves choices open

## Open — the design agent decides

### OPEN-01 — Which charger, power-path, protection, and output-stage devices to use, from which vendor, in which packages.

The brief names no part, vendor, IC family, or package anywhere; it only expresses a preference for integration.

*Decision:* **not yet made.**

### OPEN-02 — Whether a single integrated charger/power-path/boost device is used, or the function is split across discrete stages; what makes one or the other "practical" here; and how that judgement is recorded.

The brief asks for integration only "where practical", does not define the practicality test, imposes no burden of proof for departing from integration, and does not say what to do if no integrated device meets the output requirement. Any documentation obligation here comes from REQ-11's general instruction, not from the integration sentence itself.

*Decision:* **not yet made.**

### OPEN-03 — How much power is drawn from the USB-C input, and by what means the sink advertises or negotiates it (CC configuration, any negotiation protocol, any negotiation controller).

The brief states a USB-C input but fixes no input voltage, input current, negotiated profile, or configuration method.

*Decision:* **not yet made.**

### OPEN-04 — Charge current, termination voltage, charge profile, pre-charge and timer behavior, and whether charge current adapts to available input power.

The brief requires battery charging but states no electrical charge parameters at all.

*Decision:* **not yet made.**

### OPEN-05 — The cell or pack itself: chemistry variant, capacity, form factor, and how it attaches to the board (connector, solder tabs, holder, or off-board harness).

The brief says "single-cell Li-ion" and nothing further about the cell, its capacity, or its mechanical/electrical interface.

*Decision:* **not yet made.**

### OPEN-06 — How battery protection is implemented — on-board protection circuitry, a protected pack, or both — by what switching or interrupting elements, and what over-voltage, under-voltage, over-current and short-circuit thresholds and delays apply.

The brief requires "battery protection" as a function but fixes neither its location, its topology, nor any threshold.

*Decision:* **not yet made.**

### OPEN-07 — Whether cell temperature is monitored, and if so by what sensing element and with what charge/discharge inhibit window.

The brief is silent on temperature sensing; "battery safety" appears only as a benchmark stressor, not as a stated requirement for a specific mechanism.

*Decision:* **not yet made.**

### OPEN-08 — The output connector type, how many output ports exist, and how the 2 A capability is apportioned across them.

The brief fixes the output rail's voltage and current capability but names no connector and no port count.

*Decision:* **not yet made.**

### OPEN-09 — How fuel/status is measured and displayed — voltage-based estimate, coulomb counting with a sense element, a dedicated gauge device, or a host-side readout — and what resolution or accuracy is claimed.

The brief asks for "fuel/status indication" without specifying the estimation method, the display medium, the number of states, or any accuracy target.

*Decision:* **not yet made.**

### OPEN-10 — Pushbutton semantics: momentary versus latching, short/long press behavior, wake and shutdown rules, auto-shutdown on light load, debounce, and where that state machine lives.

The brief fixes only that a pushbutton controls the output enable; all behavior around it is unstated.

*Decision:* **not yet made.**

### OPEN-11 — Whether any microcontroller or programmable logic exists on the board at all, and if so what it controls.

The brief never mentions a controller; the required indication and enable behavior could be realized with or without one.

*Decision:* **not yet made.**

### OPEN-12 — Board outline, dimensions, mounting features, keep-outs, connector positions, and any enclosure or cell-pack mechanical envelope.

The brief states no mechanical constraint of any kind.

*Decision:* **not yet made.**

### OPEN-13 — Layer count, stackup, copper weight, and minimum trace/space class.

The brief header and metadata both call 2 or 4 layers "likely"; neither fixes a layer count or excludes another stackup, so the choice must follow from current density, thermal, and fabricator capability analysis.

*Decision:* **not yet made.**

### OPEN-14 — Thermal strategy for the charge and output stages at full rated load: copper area, pours, vias, component placement, and any derating or thermal-foldback behavior.

The brief states an output capability but no ambient, duty cycle, surface-temperature limit, or airflow assumption.

*Decision:* **not yet made.**

### OPEN-15 — Protection strategy beyond the battery itself — input transient handling, output over-current and short-circuit response, reverse-current and hot-plug behavior, ESD posture at exposed connectors.

The brief names battery protection only; it does not state what happens at the input or output ports under fault or transient conditions.

*Decision:* **not yet made.**

### OPEN-16 — Efficiency, quiescent/standby current, and self-discharge targets.

The brief sets no efficiency or standby budget, even though a power bank's usefulness depends on both.

*Decision:* **not yet made.**

### OPEN-17 — Test, bring-up, and programming provisions: test points, sense access, in-circuit test strategy, and how the 2 A claim will be measured.

The brief specifies no test or verification requirement.

*Decision:* **not yet made.**

### OPEN-18 — Fabrication and assembly process constraints: fabricator, single- versus double-sided assembly, finish, and DFM rule set.

The brief names no vendor, process, or manufacturing constraint.

*Decision:* **not yet made.**

### OPEN-19 — The physical form of the USB-C input interface — receptacle variant, orientation and mounting style, or a captive cable/plug — and its mechanical retention approach.

The brief says only "USB-C input". It names no connector part, variant, or mounting style, and does not fix that the input is a receptacle rather than a captive cable or plug.

*Decision:* **not yet made.**

## Where a decision gets recorded

1. Set `chosen` and `rationale` on the matching entry in
   [requirements.json](requirements.json). **That file is the authoritative
   record**, and the only one the benchmark's scripts read: a decision written
   only in prose is invisible to `board_status.py` and to any result that
   counts how many decisions an attempt actually made.
2. Answer it under its `OPEN-nn` heading here as well, with the reasoning and
   the evidence that made the choice. This file is the readable copy; where the
   two disagree, the JSON is what happened.
3. Cite the datasheet or standard in [docs/sources.md](../docs/sources.md).

A choice recorded this way stays visibly a choice. That is what lets a later
reader tell this board's engineering apart from its brief.

## Where this board is most likely to be faked

Places where a design run would be tempted to assert something it cannot
substantiate:

- The "at least 2 A" output is the easiest thing to assert and the hardest to earn: expect a design that states 2 A without a worst-case low-cell-voltage input current, a saturation check at temperature for the energy-storage element, an efficiency figure, or a dissipation number.
- The brief's preference for "an integrated charger/power-path/boost solution where practical" invites either naming a plausible-sounding integrated device without confirming a real available part meets the requirement, or quietly declaring integration impractical with no argument. Note that the brief imposes the preference, not a burden of proof for departing from it — the obligation to record the reasoning comes from the brief's general instruction to make and document open decisions.
- "Battery protection" can be faked by assuming a protected pack. If protection is delegated off-board, that must be stated as an assumption and as a stated dependency, not treated as satisfying the requirement silently. Equally, a specific protection topology must be presented as the agent's choice, since the brief fixes only the function.
- "Respect the layout guidance of the selected power ICs" is a checkable claim. Watch for a design that says it followed layout guidance without naming which datasheet section, which loop, and what the resulting loop area is.
- USB-C is often reduced to "a connector". A design that assumes an input current without the corresponding CC configuration, or that draws more than it advertises, has fabricated its input power budget. The input's physical form is likewise unfixed by the brief.
- Fuel/status indication tempts invention: a specific number of LED states, a percentage readout, or an accuracy claim, none of which the brief specifies and none of which an unstated estimation method can support.
- Mechanical envelope, enclosure fit, board dimensions, and cell format are entirely absent from the brief; any concrete number in those areas is the design agent's assumption and must be labeled as one.
- Layer count is "likely 2 or 4" in the brief header and metadata, and fixed by neither. Picking 2 for cost and then asserting the high-current paths and thermal behavior are fine, without copper area and temperature-rise numbers, is the characteristic failure here.
