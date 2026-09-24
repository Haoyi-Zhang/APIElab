import copy
import json
import tempfile
import unittest
from pathlib import Path
from compatibility.cases import (declaration, call, var, ret, const, controls,
                                 history_cases, effect_history_cases,
                                 truth_table_oracle, effect_oracle)
from compatibility.scholarly import scholarly_cases, source_records
from compatibility.infer import infer
from compatibility.model import validate, load_json, InvalidCase, BoundExceeded
from compatibility.replay import admit, check, read_json, Rejected
from compatibility.uniform import solve
from compatibility.uniform_check import check as check_uniform


def base():
    return {'id':'T001','reference':0,'inputs':[0,1],'trace_limit':20,
            'history':[{'f':declaration()},{'f':declaration(0)}], 'client':call(arg=var())}

class KernelTests(unittest.TestCase):
    def rejected_both(self,case):
        with self.assertRaises(InvalidCase): validate(case)
        with self.assertRaises(Rejected): admit(case)

    def test_reference_and_least_input(self):
        c=base(); cert,_=infer(c)
        self.assertEqual(cert['least_counterexample'],{'state':1,'input':1})
        check(c,cert)

    def test_unknown_field(self):
        c=base(); c['extra']=0; self.rejected_both(c)

    def test_bool_is_not_integer(self):
        for field in ('reference','trace_limit'):
            c=base(); c[field]=False; self.rejected_both(c)
        c=base(); c['inputs']=[False,1]; self.rejected_both(c)

    def test_non_boolean_result(self):
        c=base(); c['history'][0]['f']['table'][0]['value']=2; self.rejected_both(c)

    def test_undeclared_effect(self):
        c=base(); c['history'][0]['f']['table'][0]['trace']=['a']; self.rejected_both(c)

    def test_duplicate_effect(self):
        c=base(); c['history'][0]['f']['effects']=['a','a']; self.rejected_both(c)

    def test_duplicate_input(self):
        c=base(); c['inputs']=[0,0]; self.rejected_both(c)

    def test_unsorted_input(self):
        c=base(); c['inputs']=[1,0]; self.rejected_both(c)

    def test_unbound_variable(self):
        c=base(); c['client']['arg']=var('unbound'); self.rejected_both(c)

    def test_unreachable_branch_admission(self):
        c=base(); c['client']={'op':'if','cond':const(1),'then':ret(),'else':ret(var('bad'))}
        self.rejected_both(c)

    def test_shadowing(self):
        c=base(); c['client']['name']='x'; self.rejected_both(c)

    def test_history_bound(self):
        c=base(); c['history']=[{}]*33; self.rejected_both(c)

    def test_declaration_bound(self):
        c=base(); c['history']=[{f'f{i}':declaration() for i in range(65)}]; self.rejected_both(c)

    def test_type_restriction(self):
        c=base(); c['history'][0]['f']['type']='Int->Int'; self.rejected_both(c)

    def test_bad_reference(self):
        c=base(); c['history'][0]={}
        with self.assertRaises(InvalidCase): infer(c)
        dummy={'case_id':c['id'],'region':[],'rows':[{}]*4,'counterexamples':[],'least_counterexample':None}
        with self.assertRaises(Rejected): check(c,dummy)

    def test_trace_bound_is_rejection(self):
        c=base(); c['trace_limit']=0
        c['history'][1]['f']=declaration(words=(('a',),('a',)))
        with self.assertRaises(BoundExceeded): infer(c)
        with self.assertRaises(Rejected):
            check(c,{'case_id':c['id'],'region':[0],'rows':[{}]*4,'counterexamples':[],'least_counterexample':None})

    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'case.json'; p.write_text('{"a":1,"a":2}')
            with self.assertRaises(InvalidCase): load_json(p)
            with self.assertRaises(Rejected): read_json(p)

    def test_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'case.json'; p.write_text('{"a":NaN}')
            with self.assertRaises(InvalidCase): load_json(p)
            with self.assertRaises(Rejected): read_json(p)

    def test_json_byte_bound(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'case.json'; p.write_text(' '*100)
            with self.assertRaises(InvalidCase): load_json(p,cap=20)
            with self.assertRaises(Rejected): read_json(p,byte_limit=20)

    def test_nonminimal_witness(self):
        c=base(); c['history'][1]['f']=declaration(1)
        cert,_=infer(c)
        self.assertEqual(cert['least_counterexample']['input'],0)
        cert['least_counterexample']['input']=1
        cert['counterexamples'][0]['input']=1
        with self.assertRaises(Rejected): check(c,cert)

    def test_boolean_certificate_integer(self):
        c=base(); cert,_=infer(c); cert['region'][0]=False
        with self.assertRaises(Rejected): check(c,cert)

    def test_controls(self):
        for c,e in controls():
            cert,_=infer(c); check(c,cert)
            self.assertEqual(cert['region'],e['region'])
            self.assertEqual(cert['least_counterexample'],e['least_counterexample'])

    def test_campaign_cardinality_and_independent_oracles(self):
        truth=list(history_cases()); effects=list(effect_history_cases())
        scholarly=scholarly_cases()
        self.assertEqual((len(truth),len(effects),len(scholarly)),(600,600,30))
        self.assertEqual(len(truth)+len(effects)+len(scholarly),1230)
        for index,case in enumerate(truth):
            cert,_=infer(case)
            oracle=truth_table_oracle(case,index%6)
            self.assertTrue(all(cert[key]==value for key,value in oracle.items()))
        for index,case in enumerate(effects):
            cert,_=infer(case)
            oracle=effect_oracle(case,index%6)
            self.assertTrue(all(cert[key]==value for key,value in oracle.items()))
        for case,expected,metadata in scholarly:
            cert,_=infer(case); check(case,cert)
            self.assertEqual(cert['region'],expected['region'],metadata['id'])
            self.assertEqual(cert['least_counterexample'],expected['least_counterexample'],metadata['id'])
        self.assertEqual({record['key'] for record in source_records()},
                         {metadata['source_key'] for _,_,metadata in scholarly})

    def test_dimension_boundary(self):
        c=base(); c['history']=[{'f':declaration(words=(('a',),('a',))), 'g':declaration()} for _ in range(32)]
        body=ret(var('y23'))
        for i in reversed(range(24)):
            body=call('f' if i<20 else 'g',var('x' if i==0 else f'y{i-1}'),f'y{i}',body)
        c['client']=body
        cert,m=infer(c); check(c,cert)
        self.assertEqual(m['states'],32); self.assertEqual(m['declarations'],64)
        self.assertEqual(m['call_sites'],24); self.assertEqual(m['max_trace'],20)
        self.assertEqual(m['certificate_nodes'],1600)
        self.assertEqual(len(cert['region']),32)

    def test_call_site_bound(self):
        c=base(); body=ret(var('y24'))
        for i in reversed(range(25)):
            body=call('f',var('x' if i==0 else f'y{i-1}'),f'y{i}',body)
        c['client']=body; self.rejected_both(c)

    def test_uniform_pure_conflict(self):
        p={'choices':2,'blocks':[0,0],'safe_choices':[[0],[1]]}
        cert=solve(p); check_uniform(p,cert)
        self.assertIsNone(cert['greatest_region'])
        self.assertEqual(cert['obstruction']['states'],[0,1])

    def test_uniform_conflict_with_choice_independent_reference(self):
        root=Path(__file__).resolve().parent.parent
        supplied=load_json(root/'inputs'/'reference_choices.json')
        separate=read_json(root/'inputs'/'reference_choices.json')
        regions=[]
        for case,other in zip(supplied['cases'],separate['cases'],strict=True):
            certificate,_=infer(case);check(other,certificate)
            regions.append(certificate['region'])
            for row in certificate['rows']:
                if row['state']==0:
                    self.assertEqual(row['outcome'],{'value':0,'trace':[],'error':None})
        self.assertEqual(regions,[[0,1],[0,2]])
        expected_matrix={'choices':2,'blocks':[0,0,0],'safe_choices':[[0,1],[0],[1]]}
        derived={'choices':2,'blocks':[0,0,0],
                 'safe_choices':[[a for a,r in enumerate(regions) if v in r] for v in range(3)]}
        self.assertEqual(derived,expected_matrix)
        self.assertEqual(supplied['matrix'],expected_matrix)
        certificate=solve(supplied['matrix']);check_uniform(separate['matrix'],certificate)
        self.assertIsNone(certificate['greatest_region'])
        self.assertEqual(certificate['obstruction']['states'],[1,2])
        expected={'fixed_choice_regions':regions,'uniform_certificate':certificate,
                  'reference_observation':{'value':0,'trace':[]},'history_states':3,'conflict_states':2}
        canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
        self.assertEqual(canonical(expected),canonical(read_json(root/'results'/'reference_choices.json')))

    def test_uniform_observation_separates(self):
        p={'choices':2,'blocks':[0,1],'safe_choices':[[0],[1]]}
        cert=solve(p); check_uniform(p,cert)
        self.assertEqual(cert['greatest_region'],[0,1])

    def test_sharp_uniform_obstruction(self):
        for m in range(2,7):
            p={'choices':m,'blocks':[0]*m,'safe_choices':[[j for j in range(m) if j!=i] for i in range(m)]}
            cert=solve(p); check_uniform(p,cert)
            self.assertEqual(len(cert['obstruction']['states']),m)

    def test_no_supported_states(self):
        p={'choices':2,'blocks':[0,0],'safe_choices':[[],[]]}
        cert=solve(p); check_uniform(p,cert)
        self.assertEqual(cert['greatest_region'],[])

if __name__=='__main__': unittest.main()
