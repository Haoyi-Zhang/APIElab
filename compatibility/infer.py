"""Recursive evaluator and full finite evaluation certificates.

A successful run compares ordered event words and final Boolean results.
Missing API/default errors are never compatible, including against an error.
The reference must succeed on every declared input before a region is admitted.
"""
from __future__ import annotations
from typing import Any
from .model import validate, InvalidCase, BoundExceeded


def evaluate(case: dict, state: int, value: int) -> tuple[dict,list,int]:
    declarations = case['history'][state]
    steps = 0
    def expr(e, env):
        nonlocal steps
        steps += 1
        if 'const' in e: return e['const']
        if 'var' in e: return env[e['var']]
        return 1 - expr(e['not'],env)
    def visit(t, env):
        nonlocal steps
        steps += 1
        op=t['op']
        if op == 'return': return {'value':expr(t['value'],env),'trace':[],'error':None}, []
        if op == 'if': return visit(t['then'] if expr(t['cond'],env) else t['else'],env)
        if op == 'if_present': return visit(t['then'] if t['api'] in declarations else t['else'],env)
        if op == 'if_version': return visit(t['then'] if state >= t['min'] else t['else'],env)
        name = t['api']; d = declarations.get(name)
        if d is None:
            event={'api':name,'argument':None,'default_used':False,'default_trace':[],'body_trace':[],'result':None,'error':'missing_api'}
            return {'value':None,'trace':[],'error':'missing_api'},[event]
        omitted=t['arg'] is None
        if omitted and d['default'] is None:
            event={'api':name,'argument':None,'default_used':True,'default_trace':[],'body_trace':[],'result':None,'error':'missing_default'}
            return {'value':None,'trace':[],'error':'missing_default'},[event]
        argument=d['default']['value'] if omitted else expr(t['arg'],env)
        dw=list(d['default']['trace']) if omitted else []
        row=d['table'][argument]; bw=list(row['trace'])
        steps += 1
        rest, log=visit(t['body'],dict(env,**{t['name']:row['value']}))
        word=dw+bw+rest['trace']
        if len(word) > case['trace_limit']: raise BoundExceeded('trace budget exhausted; case rejected, not classified')
        event={'api':name,'argument':argument,'default_used':omitted,'default_trace':dw,'body_trace':bw,'result':row['value'],'error':None}
        return {'value':rest['value'],'trace':word,'error':rest['error']},[event]+log
    outcome, calls=visit(case['client'],{'x':value})
    return outcome,calls,steps


def infer(case: dict) -> tuple[dict,dict]:
    dimensions=validate(case)
    rows=[]; results={}; total_steps=0; proof_nodes=0; max_trace=0
    for state in range(len(case['history'])):
        for x in case['inputs']:
            out,calls,steps=evaluate(case,state,x)
            rows.append({'state':state,'input':x,'outcome':out,'calls':calls})
            results[state,x]=out
            total_steps += steps; proof_nodes += 1+len(calls)
            max_trace=max(max_trace,len(out['trace']))
    if proof_nodes > 6000: raise BoundExceeded('certificate node budget exceeded')
    ref=case['reference']
    if any(results[ref,x]['error'] is not None for x in case['inputs']):
        raise InvalidCase('reference faults on a declared input')
    region=[]; witnesses=[]
    for state in range(len(case['history'])):
        bad=[x for x in case['inputs'] if results[state,x]['error'] is not None or results[state,x] != results[ref,x]]
        if bad: witnesses.append({'state':state,'input':bad[0]})
        else: region.append(state)
    cert={'case_id':case['id'],'region':region,'rows':rows,'counterexamples':witnesses,
          'least_counterexample':witnesses[0] if witnesses else None}
    return cert,dict(dimensions,evaluation_steps=total_steps,certificate_nodes=proof_nodes,
                     executions=len(rows),max_trace=max_trace)
