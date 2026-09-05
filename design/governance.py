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
                            'statement': 'the assembled board delivers '
                                         'the rated 2.1 A at 5 V across '
                                         'the usable cell range; no '
                                         'conductor-sizing basis is '
                                         'frozen in this repository, so '
                                         "the copper's share is "
                                         'measured, not derived',
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
  'reason': 'device figures live in components/parameters.json with '
            'per-figure document citations; none is a typical-only '
            'figure a knowledge level would demote'},
 {'domain': 'orientation',
  'reason': 'no part on this board needs a rotation correction; the CPL '
            'ships library angles and the fabrication order review '
            'checks the preview'},
 {'domain': 'timing',
  'reason': "no timing interfaces are declared; the board's buses are DC "
            'control lines with no budget to state'}]

EXTRA_SOURCE_CLOSURE = ['evidence/datasheets/*']



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
