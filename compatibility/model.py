"""Strict input admission for a Boolean, loop-free API-client pilot.

This is not a parser for Java, Android bytecode, or an arbitrary API language.
Every declaration contains an exact two-row behavior table. All type checks are
for the single base type Bool; availability and absent defaults remain dynamic
errors. Bounds are rejection conditions, never a source of truncated successes.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

class InvalidCase(ValueError):
    pass

class BoundExceeded(ValueError):
    pass

NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")

def load_json(path: str | Path, cap: int = 2_000_000) -> Any:
    with Path(path).open('rb') as f:
        raw = f.read(cap + 1)
    if len(raw) > cap:
        raise InvalidCase('JSON input exceeds the byte cap')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise InvalidCase('duplicate JSON object key')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              InvalidCase('non-finite JSON number')))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as e:
        raise InvalidCase('invalid JSON') from e

def _keys(obj: Any, keys: set[str]) -> None:
    if type(obj) is not dict or set(obj) != keys:
        raise InvalidCase('unexpected or missing object fields')

def _integer(x: Any, lo: int, hi: int) -> bool:
    return type(x) is int and lo <= x <= hi

def _word(w: Any) -> None:
    if type(w) is not list or len(w) > 20 or any(type(a) is not str or a not in ('a','b') for a in w):
        raise InvalidCase('invalid trace word')

def _behavior(row: Any, effects: list[str]) -> None:
    _keys(row, {'value','trace'})
    if not _integer(row['value'], 0, 1):
        raise InvalidCase('a result must be a Bool encoded as integer 0 or 1')
    _word(row['trace'])
    if not set(row['trace']) <= set(effects):
        raise InvalidCase('behavior exceeds its declared effect row')

def validate(case: Any) -> dict[str, int]:
    _keys(case, {'id','reference','inputs','trace_limit','history','client'})
    if type(case['id']) is not str or not NAME.fullmatch(case['id']):
        raise InvalidCase('invalid neutral case identifier')
    hist = case['history']
    if type(hist) is not list or not 1 <= len(hist) <= 32:
        raise InvalidCase('history must contain 1..32 states')
    if not _integer(case['reference'], 0, len(hist)-1):
        raise InvalidCase('invalid reference state')
    inp = case['inputs']
    if type(inp) is not list or not inp or any(not _integer(x,0,1) for x in inp) or inp != sorted(set(inp)):
        raise InvalidCase('inputs must be a nonempty ordered subset of {0,1}')
    if not _integer(case['trace_limit'], 0, 20):
        raise InvalidCase('trace bound is outside 0..20')
    decls = 0
    for state in hist:
        if type(state) is not dict:
            raise InvalidCase('state is not a declaration map')
        decls += len(state)
        for name, dec in state.items():
            if type(name) is not str or not NAME.fullmatch(name):
                raise InvalidCase('invalid API name')
            _keys(dec, {'type','effects','default','table'})
            if dec['type'] != 'Bool->Bool':
                raise InvalidCase('unsupported type')
            eff = dec['effects']
            if type(eff) is not list or any(type(a) is not str or a not in ('a','b') for a in eff) or eff != sorted(set(eff)):
                raise InvalidCase('effect row must be a sorted set of event labels')
            if type(dec['table']) is not list or len(dec['table']) != 2:
                raise InvalidCase('a Boolean function needs exactly two behavior rows')
            for row in dec['table']:
                _behavior(row, eff)
            if dec['default'] is not None:
                _behavior(dec['default'], eff)
    if decls > 64:
        raise InvalidCase('more than 64 declarations across the history')
    counts = {'ast_nodes':0,'call_sites':0,'declarations':decls,'states':len(hist)}
    def tick(depth):
        counts['ast_nodes'] += 1
        if depth > 40 or counts['ast_nodes'] > 256:
            raise InvalidCase('syntax size/depth bound exceeded')
    def expr(e, env, depth):
        tick(depth)
        if type(e) is not dict or len(e) != 1:
            raise InvalidCase('invalid expression')
        if 'const' in e:
            if not _integer(e['const'],0,1): raise InvalidCase('invalid Boolean literal')
        elif 'var' in e:
            if type(e['var']) is not str or e['var'] not in env: raise InvalidCase('unbound variable')
        elif 'not' in e:
            expr(e['not'],env,depth+1)
        else:
            raise InvalidCase('unknown expression')
    def term(t, env, depth):
        tick(depth)
        if type(t) is not dict: raise InvalidCase('invalid term')
        op = t.get('op')
        if op == 'return':
            _keys(t,{'op','value'}); expr(t['value'],env,depth+1)
        elif op == 'let':
            _keys(t,{'op','name','api','arg','body'})
            if type(t['name']) is not str or not NAME.fullmatch(t['name']) or t['name'] in env:
                raise InvalidCase('invalid or shadowed binding')
            if type(t['api']) is not str or not NAME.fullmatch(t['api']): raise InvalidCase('invalid API name')
            if t['arg'] is not None: expr(t['arg'],env,depth+1)
            counts['call_sites'] += 1
            term(t['body'],env | {t['name']},depth+1)
        elif op == 'if':
            _keys(t,{'op','cond','then','else'}); expr(t['cond'],env,depth+1)
            term(t['then'],env,depth+1); term(t['else'],env,depth+1)
        elif op == 'if_present':
            _keys(t,{'op','api','then','else'})
            if type(t['api']) is not str or not NAME.fullmatch(t['api']): raise InvalidCase('invalid API name')
            term(t['then'],env,depth+1); term(t['else'],env,depth+1)
        elif op == 'if_version':
            _keys(t,{'op','min','then','else'})
            if not _integer(t['min'],0,len(hist)): raise InvalidCase('invalid guard threshold')
            term(t['then'],env,depth+1); term(t['else'],env,depth+1)
        else:
            raise InvalidCase('unknown term constructor')
    term(case['client'],{'x'},0)
    if counts['call_sites'] > 24: raise InvalidCase('more than 24 call sites')
    return counts
