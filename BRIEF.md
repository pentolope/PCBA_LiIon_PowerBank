# PCBA_LiIon_PowerBank — Single-Cell Li-Ion Power Bank
## Design brief

Design a single-cell Li-ion power bank board with USB-C input, battery charging, battery protection, and regulated 5 V output capable of at least 2 A. Include fuel/status indication and a pushbutton-controlled output enable. Choose an integrated charger/power-path/boost solution where practical. Respect the layout guidance of the selected power ICs and minimize high-current loop area.

## Functional requirements

- At least 2 A continuous at 5 V across the full usable cell voltage range, not only near full charge.
- Output off at cell attach and after any protection event; only a pushbutton press enables it.
- Indication separates charge state, charging, charge complete and fault, readable with no source attached.

## Power and rails

- Input operates over the Type-C vSafe5V range and draws no more than the source advertises.
- Battery rail spans the cell's discharge cut-off to its maximum charge voltage; parts on it are rated above that maximum.
- Cell-side current at rated output and minimum cell voltage, not output current, sizes conductors, switches and magnetics and sets over-current margin.
- Standby current from the cell, output off and no source attached, stays small against the cell's self-discharge.

## Charging and battery protection

- Charging is current- and voltage-limited to the cell's ratings, terminates, and respects the source's current limit.
- Over-voltage, under-voltage, over-current and short-circuit protection hold with any programmable device unpowered or unprogrammed.
- Shorted output, reversed cell, or source removed mid-charge leaves the board undamaged and protection intact.

## Interfaces, indication and control

- USB-C input presents the sink CC terminations Type-C requires, works in either orientation, ESD-protected at the connector.
- Pushbutton input debounced, press and hold behaviour defined, with no floating node and no standing idle current.

## Layout, thermal and mechanical

- Switching and high-current loops closed over minimum area, capacitors returned to their IC's power ground over unbroken copper, sense nodes Kelvin-connected clear of switching nodes.
- Conductor and via cross-sections meet a stated temperature-rise limit at worst-case cell-side current.
- Rated output sustained in still air at room ambient: no part over rating, no thermal foldback, cell within its permitted temperature range.
- Connector, button and indicators on one face and mechanical reference; keepouts defined for the cell and its connection.

## Test and bring-up

- Test points at VBUS, cell terminals, output and ground, with Kelvin pairs for efficiency measurement.
- The board runs from a bench supply in place of the cell and comes up safely with no cell fitted.

## Open choices

- Charger, power-path, boost and protection partitioning: one integrated device or discrete stages.
- Whether the input negotiates above vSafe5V (Type-C advertisement, BC1.2, USB PD), and the charge rate that follows.
- Whether output works while a source is attached, and what charging does then; the behaviour must be deterministic.
- Indicator type and charge-state resolution; output connector family; cell attachment; temperature-qualified charging.
