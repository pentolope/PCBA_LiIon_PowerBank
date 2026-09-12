"""Evidence governance this board declares, as data.

The manifest generator merges these blocks into its own document, so the
committed manifest and the generated one agree by construction - the
same discipline every other derived document lives under. Policy content
lives here; the merge logic is `merged` below.
"""

TOP = {'claims': {'approximate': {'default': 'permitted-with-label'},
            'document': 'generated/requirements.json',
            'unsupported': {'default': 'blocking', 'permitted': []}},
 'derived_documents': [{'command': ['python3',
                                    '-m',
                                    'design.requirements'],
                        'path': 'constraints/requirements.json'},
                       {'command': ['python3', '-m', 'design.rules'],
                        'path': 'generated/requirements.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_advertisement.json'],
                        'path': 'sim/pre_layout_advertisement.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_button_filter.json'],
                        'path': 'sim/pre_layout_button_filter.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_gate_slew.json'],
                        'path': 'sim/pre_layout_gate_slew.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_hot_plug.json'],
                        'path': 'sim/pre_layout_hot_plug.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_input_switch.json'],
                        'path': 'sim/pre_layout_input_switch.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_latch_set.json'],
                        'path': 'sim/pre_layout_latch_set.json'},
                       {'command': ['python3',
                                    '-m',
                                    'design.simulation',
                                    'pre_layout_output_hold.json'],
                        'path': 'sim/pre_layout_output_hold.json'}],
 'external_dependencies': [{'blocking': False,
                            'id': 'rated-output-bench',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'rated_output_current_supported',
                            'review_by': '2027-03-01',
                            'statement': 'the assembled board delivers '
                                         'the rated 2.1 A at 5 V '
                                         'across the usable cell '
                                         'range; no conductor-sizing '
                                         'basis is frozen in this '
                                         "repository, so the copper's "
                                         'share is measured, not '
                                         'derived',
                            'status': 'open'}],
 'provenance': {'evidence_index': 'evidence/index.json'},
 'requirements': {'register': 'constraints/requirements.json'}}

EXTRA_MANDATORY_GATES = ['CLAIM.MATRIX',
 'CLAIM.POLICY',
 'EXT.DEPENDENCIES',
 'PROV.DERIVED_DOCUMENTS',
 'PROV.EVIDENCE_INTEGRITY',
 'REQ.CLAIM_JOIN',
 'REQ.REGISTER']

EXTRA_REQUIRED_EVIDENCE = []

REQUIRED_DOMAINS = ['claims', 'requirements', 'simulation', 'external_dependencies']

DECLINED_DOMAINS = [{'domain': 'device_parameters',
  'reason': 'the assumed figures this board leans on (regulator '
            'dropout beyond its 1 mA characterisation, DC-bias '
            'fractions) enter the claim set as BOUNDS with stated '
            'assumptions, never as exact knowledge; the toolkit-shaped '
            'records land when an exact claim needs one demoted'},
 {'domain': 'orientation',
  'reason': 'no part on this board needs a rotation correction; the '
            'CPL ships library angles and the fabrication order review '
            'checks the preview'},
 {'domain': 'timing',
  'reason': "no timing interfaces are declared; the board's buses are "
            'DC control lines with no budget to state'},
 {'domain': 'thermal',
  'reason': 'the converter junction temperatures and the switch dissipations are judged as claims against their stated maxima, several of them awaiting a bench measurement that the register records as still required; no theta record has been frozen, so THERMAL.* has nothing to derate against'},
 {'domain': 'current_capacity',
  'reason': 'this board carries the largest currents on the bench and its conductor widths are judged as claims rather than against a capacity curve; declaring current.paths needs a capacity basis with its own source and edition, and putting an unsourced curve behind a several-amp conductor is exactly what this toolkit refuses'},
 {'domain': 'power_integrity',
  'reason': 'the cell and output paths are judged as claims over the declared conductor geometry; a rail mesh has not been declared, and the drops that matter here are dominated by the switches rather than by the copper'},
 {'domain': 'differential_pairs',
  'reason': 'this board routes no differential pair; every net on it is single-ended and there is no pair impedance to hold'},
 {'domain': 'reference_continuity',
  'reason': 'no interface on this board declares a return-path requirement; the currents that matter are DC and their return is judged by the same claims that judge the outbound path'},
 {'domain': 'lifecycle',
  'reason': "no lifecycle snapshot has been frozen for this board; the domain wants a status for each fitted part, the basis it rests on, and evidence bytes behind a digest, and what this board holds is the stock and price in components/jlcpcb.json retrieved 2026-09-02 - no status for any of its 29 part numbers, no catalogue page frozen, and nobody named as having reviewed one. The gap is already on the record as the supply claim's own stated assumption, that the stock figures are the frozen ones rather than today's; closing it is an acquisition and a human review, not a manifest edit"},
 {'domain': 'assembly_process',
  'reason': 'the process block asks for four figures at once and this board can source two of them: all 81 footprints sit on the front, and the three through-hole operations are already measured against ASSEMBLY_POLICY by the assembly_within_declared_policy claim. The other two are established nowhere here - no reflow profile and no cleaning step is frozen for the assembler this board orders from, and that order is still an open external dependency. The per-part half is worse: of 29 part numbers, 9 have frozen datasheets stating no soldering temperature at all (three of the four AOS switches, DW01A, IP5306, SWPA8040, TS-1187A, the HRO receptacle, and LM393DR2G, which mentions soldering only to point at a reference manual this board has not frozen), the fourth AOS part gives 260 degC only as a JESD22-A113 precondition row rather than a rating, and most of what the others state - 260 degC for 10 s, 270 +/- 5 degC - are solder-bath and immersion tests, which are solderability rather than a reflow ceiling. An empty record means reviewed-and-needs-nothing; nine of them resting on silence would say that falsely'},
 {'domain': 'flow_repeatability',
  'reason': "the domain applies squarely - this board's copper came out of a search its own routing record calls not bit-reproducible - and the evidence it wants cannot be produced here, because the router that drew this copper is no longer in the tree. FLOW.REPEATABILITY refuses a study whose router identity differs from the adopted record's, and four parts of that identity have moved since this board was routed: KiCadRoutingTools 3fb9c05f -> 58430d49, its grid_router.so 0.21.4 -> 0.22.0 on a different binary digest, the KRT version 0.21.5 -> 0.22.0, and KiCad 10.0.5 -> 10.0.6. Measured rather than assumed: one full search under today's tools from candidates/route-current/placed.kicad_pcb (31ae0090), which the adopted record names as its own source, ran nine and a half minutes and refused all three attempts - a different net left open each time (OUT_CC2, OUT_CC2, VOUT) and a different count of duplicate and dangling geometry - so a distribution sampled now would describe a tool this board never ran under, and would describe it as failing. Closing this is routing the board again under the current toolchain, adopting that copper and sampling the search that produced it: a re-layout, not a manifest edit"}]

EXTRA_SOURCE_CLOSURE = ['evidence/datasheets/*', 'generated/requirements.json']


def merged(document):
    import copy

    doc = copy.deepcopy(document)
    doc.update(copy.deepcopy(TOP))
    profile = doc["release_profile"]
    profile["mandatory_gates"] = sorted(
        set(profile["mandatory_gates"]) | set(EXTRA_MANDATORY_GATES))
    profile["required_evidence"] = sorted(
        set(profile.get("required_evidence", []))
        | set(EXTRA_REQUIRED_EVIDENCE))
    profile["required_domains"] = list(REQUIRED_DOMAINS)
    profile["declined_domains"] = copy.deepcopy(DECLINED_DOMAINS)
    closure = doc["reports"]["source_closure"]
    for pattern in EXTRA_SOURCE_CLOSURE:
        if pattern not in closure:
            closure.append(pattern)
    return doc
