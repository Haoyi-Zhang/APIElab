"""Thirty bounded literature-grounded illustrations.

Each entry is a deliberately small projection of a phenomenon described by a
public scholarly source.  It is not an extraction of an app, bytecode corpus,
or device trace and must not be used as prevalence or deployment evidence.
Expected regions are authored independently of the producer implementation.
"""
from __future__ import annotations
from copy import deepcopy
from .cases import declaration, call, var, ret


SOURCES = {
    'li2018cid': {
        'title': 'CiD: Automating the Detection of API-related Compatibility Issues in Android Apps',
        'url': 'https://orbilu.uni.lu/handle/10993/37890',
        'role': 'API lifecycle, introduction/removal/reintroduction, and SDK-guard examples',
    },
    'dagenais2009semdiff': {
        'title': 'SemDiff: Analysis and Recommendation Support for API Evolution',
        'url': 'https://doi.org/10.1109/ICSE.2009.5070565',
        'role': 'method/class deletion and replacement-call recommendations',
    },
    'liu2021silent': {
        'title': 'Identifying and Characterizing Silently-Evolved Methods in the Android API',
        'url': 'https://doi.org/10.1109/ICSE-SEIP52600.2021.00040',
        'role': 'same-signature behavioral evolution',
    },
    'wei2016fragmentation': {
        'title': 'Taming Android Fragmentation: Characterizing and Detecting Compatibility Issues for Android Apps',
        'url': 'https://doi.org/10.1145/2970276.2970312',
        'role': 'platform/device fragmentation and guarded compatibility',
    },
    'fazzini2019update': {
        'title': 'Automated API-Usage Update for Android Apps',
        'url': 'https://doi.org/10.1145/3293882.3330571',
        'role': 'API replacement and usage-update patterns',
    },
}


def source_records():
    return [{'key': key, **value} for key, value in SOURCES.items()]


def scholarly_cases():
    result = []

    def add(history, client, region, least, source, phenomenon, projection,
            inputs=(0, 1), reference=0):
        identifier = f'S{len(result)+1:03d}'
        case = {'id': identifier, 'reference': reference, 'inputs': list(inputs),
                'trace_limit': 20, 'history': deepcopy(history), 'client': deepcopy(client)}
        expected = {'id': identifier, 'region': list(region),
                    'least_counterexample': deepcopy(least)}
        metadata = {
            'id': identifier,
            'source_key': source,
            'phenomenon': phenomenon,
            'projection': projection,
            'fidelity_limit': ('Hand-authored Boolean projection of a reported evolution pattern; '
                               'not a reproduction of source apps, bytecode, devices, or prevalence.'),
        }
        result.append((case, expected, metadata))

    ident = declaration(2)
    neg = declaration(1)
    zero = declaration(0)
    direct = call(arg=var())
    presence = {'op': 'if_present', 'api': 'f', 'then': direct, 'else': ret()}
    versioned = {'op': 'if_version', 'min': 1, 'then': direct, 'else': ret()}

    # CiD reports seven Android APIs whose lifecycle includes removal followed
    # by reintroduction.  Each receives a separate neutral finite projection.
    reintroduced = [
        'Gravity.getAbsoluteGravity', 'KeyEvent.getDeviceId', 'MotionEvent.getDeviceId',
        'DatagramSocketImpl.getOption', 'DatagramSocketImpl.setOption',
        'SocketImpl.getOption', 'SocketImpl.setOption',
    ]
    for api_name in reintroduced:
        add([{'f': ident}, {}, {'f': ident}], direct, [0, 2], {'state': 1, 'input': 0},
            'li2018cid', f'removal and reintroduction: {api_name}',
            'Three-state available/absent/available lifecycle with unchanged Boolean behavior.')

    add([{}, {'f': ident}], direct, [1], {'state': 0, 'input': 0}, 'li2018cid',
        'unguarded use before introduction', 'Two-state introduction with the later state as reference.',
        reference=1)
    add([{}, {'f': ident}], versioned, [0, 1], None, 'li2018cid',
        'SDK-level guard around an introduced API',
        'Version guard selects a behavior-preserving fallback before introduction.', reference=1)
    add([{'f': ident}, {}], direct, [0], {'state': 1, 'input': 0}, 'li2018cid',
        'use after removal', 'Two-state removal makes an unguarded call fault.')
    add([{'f': ident}, {}], presence, [0, 1], None, 'li2018cid',
        'availability guard around a removed API',
        'Presence guard selects an observationally equal fallback after removal.')
    add([{}, {'f': ident}], direct, [1], {'state': 0, 'input': 0}, 'li2018cid',
        'API introduced at a later platform level',
        'Introduction boundary represented by one absent and one available state.', reference=1)
    add([{}, {'f': ident}], versioned, [0, 1], None, 'li2018cid',
        'SDK_INT-style guard', 'Version guard exactly separates absent and available states.', reference=1)
    add([{'f': ident}, {'f': neg}], direct, [0], {'state': 1, 'input': 0}, 'li2018cid',
        'behavior-change boundary outside lifecycle-only detection',
        'Same availability and type, but a changed truth table; included as a stated scope boundary.')

    # SemDiff-style deletions and replacement adaptations.
    add([{'f': ident}, {}], direct, [0], {'state': 1, 'input': 0}, 'dagenais2009semdiff',
        'deleted method', 'Method deletion as an unavailable declaration in the later state.')
    replacement_same = {'op': 'if_version', 'min': 1,
                        'then': call('g', var()), 'else': call('f', var())}
    add([{'f': ident}, {'g': ident}], replacement_same, [0, 1], None, 'dagenais2009semdiff',
        'one-call replacement preserving behavior',
        'Version-indexed elaboration switches from the deleted method to an equivalent replacement.')
    add([{'f': ident}, {'g': neg}], replacement_same, [0], {'state': 1, 'input': 0},
        'dagenais2009semdiff', 'suggested replacement with different behavior',
        'Replacement remains type-correct but fails the stronger observational condition.')
    replacement_pair = {'op': 'if_version', 'min': 1,
                        'then': call('g', var(), 'y', call('h', var('y'), 'z')),
                        'else': call('f', var())}
    add([{'f': ident}, {'g': neg, 'h': neg}], replacement_pair, [0, 1], None,
        'dagenais2009semdiff', 'one-to-many replacement sequence',
        'Two replacement calls jointly preserve the reference result although each negates it.')

    # Same-signature behavior changes and context sensitivity.
    add([{'f': ident}, {'f': zero}], direct, [0], {'state': 1, 'input': 1},
        'liu2021silent', 'same signature with changed result',
        'The declaration remains present and typed, but differs on the least distinguishing input.')
    trace_ab = declaration(2, words=(('a', 'b'), ('a', 'b')))
    trace_ba = declaration(2, words=(('b', 'a'), ('b', 'a')))
    add([{'f': trace_ab}, {'f': trace_ba}], direct, [0], {'state': 1, 'input': 0},
        'liu2021silent', 'same result with changed event order',
        'A trace-sensitive observation distinguishes APIs that return equal values.')
    default_zero = declaration(2, default={'value': 0, 'trace': []})
    default_one = declaration(2, default={'value': 1, 'trace': []})
    add([{'f': default_zero}, {'f': default_one}], call(), [0], {'state': 1, 'input': 0},
        'liu2021silent', 'changed implicit default',
        'Omitted-argument elaboration exposes a default-value change.')
    pair = call('f', var(), 'y', call('g', var('y'), 'z'))
    add([{'f': neg, 'g': neg}, {'f': ident, 'g': ident}], pair, [0, 1], None,
        'liu2021silent', 'context masks two local changes',
        'Sequential composition is observationally stable although both component tables change.')

    # Fragmentation and platform-specific adaptation.
    add([{}, {'f': ident}], presence, [0, 1], None, 'wei2016fragmentation',
        'guarded platform-specific API availability',
        'A presence guard abstracts a compatibility check across two platform states.', reference=1)
    add([{}, {'f': ident}], direct, [1], {'state': 0, 'input': 0},
        'wei2016fragmentation', 'unguarded platform-specific API availability',
        'The same history without a guard faults on the earlier platform state.', reference=1)
    add([{'f': ident}, {'f': neg}], direct, [0], {'state': 1, 'input': 0},
        'wei2016fragmentation', 'device-dependent behavior behind a stable signature',
        'Two abstract platform states expose different behavior for an equally typed API.')
    adapted = {'op': 'if_version', 'min': 1,
               'then': call('f', {'not': var()}), 'else': call('f', var())}
    add([{'f': ident}, {'f': neg}], adapted, [0, 1], None, 'wei2016fragmentation',
        'state-aware adaptation for platform variation',
        'A state guard and argument adapter restore the reference Boolean behavior.')

    # API-usage update patterns, including defaults, replacements, and effects.
    no_default = declaration(2, default=None)
    add([{'f': no_default}, {'f': default_zero}], call(), [1], {'state': 0, 'input': 0},
        'fazzini2019update', 'new default enables omitted argument',
        'The same call site becomes defined only after a default is introduced.', reference=1)
    traced_f = declaration(2, words=(('a',), ('a',)))
    traced_g = declaration(2, words=(('a',), ('a',)))
    add([{'f': traced_f}, {'g': traced_g}], replacement_same, [0, 1], None,
        'fazzini2019update', 'replacement preserves result and trace',
        'Version-indexed replacement preserves both return value and event word.')
    traced_g_changed = declaration(2, words=(('b',), ('b',)))
    add([{'f': traced_f}, {'g': traced_g_changed}], replacement_same, [0],
        {'state': 1, 'input': 0}, 'fazzini2019update',
        'replacement preserves value but changes effects',
        'A return-only test would accept; trace refinement rejects the update.')
    add([{'f': ident, 'g': ident}, {'f': neg, 'g': neg}], pair, [0, 1], None,
        'fazzini2019update', 'multi-call update preserves context behavior',
        'Whole-client equivalence holds even though independent component checks would reject.')

    assert len(result) == 30
    return result
