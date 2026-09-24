"""Separately implemented, iterative certificate replay.

This module intentionally imports neither the producer nor its validator. Its
trusted inputs are the schema below, Python/JSON, and the supplied behavior
maps. It is not an independent human review or a proof-assistant kernel.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

class Rejected(ValueError):
    pass


def read_json(path: str | Path, byte_limit: int = 2_000_000):
    with Path(path).open('rb') as f:
        raw = f.read(byte_limit + 1)
    if len(raw) > byte_limit:
        raise Rejected('input byte limit')
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise Rejected('duplicate key')
            result[key] = value
        return result
    def constant(_):
        raise Rejected('non-finite number')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as e:
        raise Rejected('invalid JSON input') from e


def _object(item, fields):
    if type(item) is not dict or set(item) != set(fields.split()):
        raise Rejected('schema fields')


def _nat(item, maximum):
    return type(item) is int and 0 <= item <= maximum


def _name(item):
    return type(item) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', item) is not None


def _row(item, labels):
    _object(item, 'value trace')
    if not _nat(item['value'], 1):
        raise Rejected('non-Boolean result')
    word = item['trace']
    if type(word) is not list or len(word) > 20:
        raise Rejected('event word')
    if any(type(a) is not str or a not in ('a', 'b') or a not in labels for a in word):
        raise Rejected('event not declared')


def admit(case):
    """Iterative independent syntax admission, including unreachable branches."""
    _object(case, 'id reference inputs trace_limit history client')
    if not _name(case['id']):
        raise Rejected('case identity')
    history = case['history']
    if type(history) is not list or not 1 <= len(history) <= 32:
        raise Rejected('history size')
    if not _nat(case['reference'], len(history) - 1) or not _nat(case['trace_limit'], 20):
        raise Rejected('reference or trace limit')
    inputs = case['inputs']
    if type(inputs) is not list or not inputs or any(not _nat(x, 1) for x in inputs):
        raise Rejected('input domain')
    if inputs != sorted(set(inputs)):
        raise Rejected('input order or duplication')
    declarations = 0
    for state in history:
        if type(state) is not dict:
            raise Rejected('declaration map')
        declarations += len(state)
        for name, decl in state.items():
            if not _name(name):
                raise Rejected('API identifier')
            _object(decl, 'type effects default table')
            if type(decl['type']) is not str or decl['type'] != 'Bool->Bool':
                raise Rejected('API type')
            labels = decl['effects']
            if type(labels) is not list or any(type(a) is not str or a not in ('a', 'b') for a in labels):
                raise Rejected('effect row')
            if labels != sorted(set(labels)):
                raise Rejected('effect row order')
            table = decl['table']
            if type(table) is not list or len(table) != 2:
                raise Rejected('behavior table')
            for row in table:
                _row(row, labels)
            if decl['default'] is not None:
                _row(decl['default'], labels)
    if declarations > 64:
        raise Rejected('declaration bound')
    # An explicit syntax stack avoids using the producer's recursive traversal.
    stack = [('term', case['client'], frozenset({'x'}), 0)]
    nodes = calls = 0
    while stack:
        kind, item, env, depth = stack.pop()
        nodes += 1
        if nodes > 256 or depth > 40 or type(item) is not dict:
            raise Rejected('syntax bound or object')
        if kind == 'expr':
            if len(item) != 1:
                raise Rejected('expression arity')
            if 'const' in item:
                if not _nat(item['const'], 1):
                    raise Rejected('literal')
            elif 'var' in item:
                if type(item['var']) is not str or item['var'] not in env:
                    raise Rejected('unbound variable')
            elif 'not' in item:
                stack.append(('expr', item['not'], env, depth + 1))
            else:
                raise Rejected('expression constructor')
            continue
        op = item.get('op')
        if op == 'return':
            _object(item, 'op value')
            stack.append(('expr', item['value'], env, depth + 1))
        elif op == 'let':
            _object(item, 'op name api arg body')
            if not _name(item['name']) or item['name'] in env or not _name(item['api']):
                raise Rejected('binding or API name')
            calls += 1
            if calls > 24:
                raise Rejected('call-site bound')
            if item['arg'] is not None:
                stack.append(('expr', item['arg'], env, depth + 1))
            stack.append(('term', item['body'], env | {item['name']}, depth + 1))
        elif op in ('if', 'if_present', 'if_version'):
            field = {'if': 'cond', 'if_present': 'api', 'if_version': 'min'}[op]
            _object(item, 'op then else ' + field)
            if op == 'if':
                stack.append(('expr', item['cond'], env, depth + 1))
            elif op == 'if_present':
                if not _name(item['api']):
                    raise Rejected('presence guard')
            elif not _nat(item['min'], len(history)):
                raise Rejected('version guard')
            stack.append(('term', item['then'], env, depth + 1))
            stack.append(('term', item['else'], env, depth + 1))
        else:
            raise Rejected('term constructor')
    return {'ast_nodes': nodes, 'call_sites': calls, 'declarations': declarations,
            'states': len(history)}


def execute(case, state_number, input_value):
    state = case['history'][state_number]
    env = {'x': input_value}
    cursor = case['client']
    trace, calls = [], []
    steps = 0
    def expression(node):
        nonlocal steps
        negate = 0
        while 'not' in node:
            steps += 1
            negate ^= 1
            node = node['not']
        steps += 1
        value = node['const'] if 'const' in node else env[node['var']]
        return value ^ negate
    while True:
        steps += 1
        op = cursor['op']
        if op == 'return':
            result = expression(cursor['value'])
            return {'value': result, 'trace': trace, 'error': None}, calls, steps
        if op in ('if', 'if_present', 'if_version'):
            if op == 'if': take = bool(expression(cursor['cond']))
            elif op == 'if_present': take = cursor['api'] in state
            else: take = state_number >= cursor['min']
            cursor = cursor['then'] if take else cursor['else']
            continue
        name = cursor['api']
        decl = state.get(name)
        omitted = cursor['arg'] is None
        if decl is None or (omitted and decl['default'] is None):
            reason = 'missing_api' if decl is None else 'missing_default'
            calls.append({'api': name, 'argument': None,
                          'default_used': False if decl is None else True,
                          'default_trace': [], 'body_trace': [],
                          'result': None, 'error': reason})
            return {'value': None, 'trace': trace, 'error': reason}, calls, steps
        if omitted:
            argument = decl['default']['value']
            default_trace = list(decl['default']['trace'])
        else:
            argument = expression(cursor['arg'])
            default_trace = []
        result = decl['table'][argument]['value']
        body_trace = list(decl['table'][argument]['trace'])
        steps += 1
        trace.extend(default_trace)
        trace.extend(body_trace)
        if len(trace) > case['trace_limit']:
            raise Rejected('trace bound exhausted: no conclusion')
        calls.append({'api': name, 'argument': argument, 'default_used': omitted,
                      'default_trace': default_trace, 'body_trace': body_trace,
                      'result': result, 'error': None})
        env[cursor['name']] = result
        cursor = cursor['body']


def _canonical(value):
    """JSON comparison distinguishes true from 1 (Python equality does not)."""
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise Rejected('non-JSON certificate') from exc


def check(case, certificate, accounting=None):
    dimensions = admit(case)
    _object(certificate, 'case_id region rows counterexamples least_counterexample')
    if type(certificate['rows']) is not list:
        raise Rejected('certificate rows')
    expected_count = len(case['history']) * len(case['inputs'])
    if len(certificate['rows']) != expected_count:
        raise Rejected('incomplete or duplicate coverage')
    if len(_canonical(certificate).encode('utf-8')) > 2_000_000:
        raise Rejected('certificate byte bound')
    results = {}
    expected_rows = []
    total_steps = nodes = 0
    for version in range(len(case['history'])):
        for x in case['inputs']:
            out, events, count = execute(case, version, x)
            total_steps += count
            if accounting is not None:
                accounting['replay_evaluation_steps'] = accounting.get('replay_evaluation_steps', 0) + count
                accounting['replay_executions'] = accounting.get('replay_executions', 0) + 1
            nodes += 1 + len(events)
            results[version, x] = out
            expected_rows.append({'state': version, 'input': x, 'outcome': out, 'calls': events})
    if nodes > 6000:
        raise Rejected('certificate node bound')
    ref = case['reference']
    if any(results[ref, x]['error'] is not None for x in case['inputs']):
        raise Rejected('reference must succeed')
    accepted = []
    failures = []
    for version in range(len(case['history'])):
        first = None
        for x in case['inputs']:
            observed = results[version, x]
            if observed['error'] is not None or observed != results[ref, x]:
                first = x
                break
        if first is None:
            accepted.append(version)
        else:
            failures.append({'state': version, 'input': first})
    expected = {'case_id': case['id'], 'region': accepted, 'rows': expected_rows,
                'counterexamples': failures,
                'least_counterexample': failures[0] if failures else None}
    if _canonical(certificate) != _canonical(expected):
        raise Rejected('certificate disagrees with complete semantic replay')
    return dict(dimensions, checker_steps=total_steps, certificate_nodes=nodes,
                executions=expected_count)
