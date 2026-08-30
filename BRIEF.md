# PCBA_LiIon_PowerBank — Single-Cell Li-Ion Power Bank

**Benchmark ID:** 07  
**Difficulty:** 2/5  
**Brief detail:** 2/5  
**Category:** power-management  
**Likely layer count:** 2 or 4  
**Primary stressors:** charger layout, power-path routing, battery safety, USB-C power

## Design brief

Design a single-cell Li-ion power bank board with USB-C input, battery charging, battery protection, and regulated 5 V output capable of at least 2 A. Include fuel/status indication and a pushbutton-controlled output enable. Choose an integrated charger/power-path/boost solution where practical. Respect the layout guidance of the selected power ICs and minimize high-current loop area.

## Benchmark intent

This brief is intentionally one member of a heterogeneous PCBA-autodesign benchmark. Treat stated requirements as authoritative; where the brief leaves choices open, make and document reasonable engineering decisions rather than inventing hidden user requirements. The repository should remain a consumer of the shared `PCBA_AutoDesignAndTest` toolkit rather than accumulating board-specific logic in the toolkit.
