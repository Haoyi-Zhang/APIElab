"""Deterministic, closed pilot grammars. All inputs are authored/generated here."""
from copy import deepcopy
from itertools import product


def declaration(code=2, default=None, words=((), ()), effects=None):
    used = set(words[0]) | set(words[1])
    if default is not None:
        used |= set(default['trace'])
    return {'type': 'Bool->Bool', 'effects': sorted(used if effects is None else effects),
            'default': deepcopy(default),
            'table': [{'value': (code >> i) & 1, 'trace': list(words[i])} for i in (0, 1)]}


def var(name='x'): return {'var': name}
def const(x): return {'const': x}
def ret(e=None): return {'op': 'return', 'value': var() if e is None else e}
def call(api='f', arg=None, name='y', body=None):
    return {'op': 'let', 'name': name, 'api': api, 'arg': arg,
            'body': ret(var(name)) if body is None else body}


TRUTH_TEMPLATE_NAMES = (
    'explicit_input',
    'explicit_zero',
    'explicit_one',
    'presence_guard_fallback',
    'two_call_composition',
    'input_branch',
)


def templates():
    """Six clients; none contains a numerical version guard and at most two calls occur syntactically."""
    return [call(arg=var()), call(arg=const(0)), call(arg=const(1)),
            {'op': 'if_present', 'api': 'f', 'then': call(arg=var()), 'else': ret()},
            call(arg=var(), body=call(arg=var('y'), name='z')),
            {'op': 'if', 'cond': var(), 'then': call(arg=const(0)), 'else': call(arg=const(1))}]


def history_cases():
    """First exhaustive family: 4 reference functions x 5 x 5 candidate profiles x 6 clients."""
    number = 0
    for reference in range(4):
        for a, b in product(range(-1, 4), repeat=2):
            history = [{'f': declaration(reference)}] + [({} if c == -1 else {'f': declaration(c)}) for c in (a, b)]
            for client in templates():
                number += 1
                yield {'id': f'H{number:04d}', 'reference': 0, 'inputs': [0, 1],
                       'trace_limit': 20, 'history': deepcopy(history), 'client': client}


def controls():
    answer = []
    def add(history, client, expected, least=None, inputs=(0, 1), reference=0, purpose=''):
        name = f'C{len(answer)+1:03d}'
        answer.append(({'id': name, 'reference': reference, 'inputs': list(inputs),
                        'trace_limit': 20, 'history': history, 'client': client},
                       {'id': name, 'region': expected, 'least_counterexample': least, 'purpose': purpose}))
    direct = lambda: call(arg=var())
    pair = lambda: call('f', var(), 'y', call('g', var('y'), 'z'))
    add([{'f': declaration()}, {}, {'f': declaration()}], direct(), [0, 2],
        {'state': 1, 'input': 0}, purpose='Non-contiguous availability')
    add([{'f': declaration()}, {}, {'f': declaration()}], templates()[3], [0, 1, 2],
        purpose='Presence guard with a behavior-preserving fallback')
    add([{'f': declaration()}, {'f': declaration(0)}], direct(), [0],
        {'state': 1, 'input': 1}, purpose='Least failing input is one, not zero')
    add([{'f': declaration(words=(('a','b'),('a','b')))},
         {'f': declaration(words=(('b','a'),('b','a')))}], direct(), [0],
        {'state': 1, 'input': 0}, purpose='Equal effect rows, unequal event order')
    add([{'f': declaration(default={'value':0,'trace':[event]})} for event in ('a','a','b')],
        call(), [0,1], {'state':2,'input':0}, purpose='Fixed effectful defaults preserve semantic principality')
    add([{'f': declaration(default={'value':v,'trace':[]})} for v in (0,1)], call(), [0],
        {'state':1,'input':0}, purpose='Default-value change')
    add([{'f': declaration(default={'value':0,'trace':[]})}, {'f': declaration()}], call(), [0],
        {'state':1,'input':0}, purpose='Absent required default is an error')
    add([{'f': declaration(words=(w,w))} for w in (('a',),('a','a'))], direct(), [0],
        {'state':1,'input':0}, purpose='Equal effect rows, unequal event multiplicity')
    add([{'f': declaration(c), 'g': declaration(c)} for c in (2,1)], pair(), [0,1],
        purpose='Two negations mask two isolated mismatches')
    add([{'f': declaration(3), 'g': declaration(c)} for c in (2,0)], pair(), [0],
        {'state':1,'input':0}, inputs=(0,), purpose='Initial-input-only local checks are unsound')
    add([{'f': declaration()}, {}],
        {'op':'if_version','min':1,'then':ret(),'else':direct()}, [0,1],
        purpose='Version guard bypasses unavailable API')
    add([{'f': declaration(words=(('a',),('a',))), 'g': declaration()},
         {'f': declaration(words=(('a',),('a',)))}], pair(), [0],
        {'state':1,'input':0}, purpose='Observable prefix is retained before a later error')
    add([{'f':declaration(2)}, {'f':declaration(1)}],
        {'op':'if','cond':{'not':var()},'then':call(arg={'not':var()}),
         'else':ret({'not':var()})}, [0], {'state':1,'input':0},
        purpose='Negation expressions and input-dependent branches')
    add([{}, {}], {'op':'if','cond':const(1),'then':ret(),'else':call('absent',var())},
        [0,1], purpose='Unreachable unavailable call does not make execution fail')
    add([{'f':declaration(default={'value':0,'trace':[event]})} for event in ('a','b')],
        direct(), [0,1], purpose='Explicit argument does not evaluate an unused default')
    add([{'f':declaration(0)}, {'f':declaration(2)}], direct(), [1],
        {'state':0,'input':1}, reference=1, purpose='Reference may occur after the earliest bad version')
    return answer


def truth_table_oracle(case, template_number):
    """No AST evaluation: six closed-form functions for the exhaustive grammar."""
    def run(state, x):
        dec = case['history'][state].get('f')
        if dec is None:
            return x if template_number == 3 else None
        f = lambda a: dec['table'][a]['value']
        if template_number in (0,3): return f(x)
        if template_number == 1: return f(0)
        if template_number == 2: return f(1)
        if template_number == 4: return f(f(x))
        return f(0) if x else f(1)
    region=[]; bad=[]
    for v in range(3):
        mismatch=[x for x in (0,1) if run(v,x) is None or run(v,x) != run(0,x)]
        if mismatch: bad.append({'state':v,'input':mismatch[0]})
        else: region.append(v)
    return {'region':region,'counterexamples':bad,
            'least_counterexample':bad[0] if bad else None}


def partitions(n):
    def extend(prefix):
        if len(prefix) == n:
            yield prefix
        else:
            for a in range(max(prefix)+2):
                yield from extend(prefix+[a])
    yield from extend([0])


def uniform_problems():
    for n in range(1,4):
        for m in range(1,4):
            for flat in product((0,1), repeat=n*m):
                rows=[[a for a in range(m) if flat[v*m+a]] for v in range(n)]
                for blocks in partitions(n):
                    yield {'choices':m, 'blocks':blocks, 'safe_choices':deepcopy(rows)}


def effect_declaration(profile):
    """Four deterministic Boolean APIs with value, body-effect, and default variation."""
    specifications = (
        (2, {'value': 0, 'trace': ['a']}, (('a',), ('b',))),
        (1, {'value': 1, 'trace': ['b']}, (('b',), ('a', 'b'))),
        (3, {'value': 0, 'trace': ['a', 'b']}, ((), ('a',))),
        (0, {'value': 1, 'trace': []}, (('b', 'a'), ())),
    )
    code, default, words = specifications[profile]
    return declaration(code=code, default=default, words=words)


EFFECT_TEMPLATE_NAMES = (
    'explicit_input',
    'omitted_default',
    'presence_guard_omitted_else_input',
    'input_branch_omitted_or_explicit',
    'two_call_default_then_explicit',
    'version_guard_omitted_or_explicit',
)


def effect_templates():
    """Six clients exercising defaults/effects; the largest syntax has two call sites."""
    return [
        call(arg=var()),
        call(),
        {'op': 'if_present', 'api': 'f', 'then': call(), 'else': ret()},
        {'op': 'if', 'cond': var(), 'then': call(), 'else': call(arg=var())},
        call(arg=None, name='y', body=call(arg=var('y'), name='z')),
        {'op': 'if_version', 'min': 2, 'then': call(), 'else': call(arg=var())},
    ]


def effect_history_cases():
    """Second exhaustive family: 4 reference profiles x 5 x 5 candidate profiles x 6 clients = 600."""
    number = 0
    for reference in range(4):
        for a, b in product(range(-1, 4), repeat=2):
            history = [{'f': effect_declaration(reference)}] + [
                ({} if c == -1 else {'f': effect_declaration(c)}) for c in (a, b)
            ]
            for client in effect_templates():
                number += 1
                yield {'id': f'E{number:04d}', 'reference': 0, 'inputs': [0, 1],
                       'trace_limit': 20, 'history': deepcopy(history), 'client': client}


def effect_oracle(case, template_number):
    """Closed-form oracle for ``effect_history_cases``; it never evaluates the AST."""
    def invoke(dec, argument, omitted):
        if dec is None:
            return None, (), 'missing_api'
        if omitted and dec['default'] is None:
            return None, (), 'missing_default'
        if omitted:
            argument = dec['default']['value']
            prefix = tuple(dec['default']['trace'])
        else:
            prefix = ()
        row = dec['table'][argument]
        return row['value'], prefix + tuple(row['trace']), None

    def run(state, x):
        dec = case['history'][state].get('f')
        if template_number == 0:
            return invoke(dec, x, False)
        if template_number == 1:
            return invoke(dec, None, True)
        if template_number == 2:
            return invoke(dec, None, True) if dec is not None else (x, (), None)
        if template_number == 3:
            return invoke(dec, None, True) if x else invoke(dec, x, False)
        if template_number == 4:
            first_value, first_trace, error = invoke(dec, None, True)
            if error is not None:
                return first_value, first_trace, error
            value, second_trace, error = invoke(dec, first_value, False)
            return value, first_trace + second_trace, error
        if state >= 2:
            return invoke(dec, None, True)
        return invoke(dec, x, False)

    reference = case['reference']
    region, counterexamples = [], []
    for state in range(len(case['history'])):
        first = None
        for x in case['inputs']:
            observed = run(state, x)
            expected = run(reference, x)
            if observed[2] is not None or observed != expected:
                first = x
                break
        if first is None:
            region.append(state)
        else:
            counterexamples.append({'state': state, 'input': first})
    return {'region': region, 'counterexamples': counterexamples,
            'least_counterexample': counterexamples[0] if counterexamples else None}
