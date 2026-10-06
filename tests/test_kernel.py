import copy
import json
import unittest
from pathlib import Path
from itertools import product
from tests.fixtures import temporary_directory
from compatibility.cases import (declaration, call, var, ret, const, controls,
                                 history_cases, effect_history_cases,
                                 truth_table_oracle, effect_oracle,
                                 TRUTH_TEMPLATE_NAMES, EFFECT_TEMPLATE_NAMES)
from compatibility.scholarly import scholarly_cases, source_records
from compatibility.infer import infer
from compatibility.model import validate, load_json, InvalidCase, BoundExceeded
from compatibility.replay import admit, check, read_json, Rejected
from compatibility.uniform import solve
from compatibility.uniform_check import (check as check_uniform, enumerate_supports,
                                            is_refinement)
from compatibility.guards import (endpoint_union_masks, greatest_sound_by_endpoints,
                                  component_oracle, component_count)


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

    def test_reference_missing_api_is_rejected(self):
        c=base(); c['history'][0]={}
        with self.assertRaises(InvalidCase): infer(c)
        dummy={'case_id':c['id'],'region':[],'rows':[{}]*4,'counterexamples':[],'least_counterexample':None}
        with self.assertRaises(Rejected): check(c,dummy)

    def test_reference_missing_default_is_rejected(self):
        c=base(); c['client']=call(); c['history'][0]['f']['default']=None
        with self.assertRaises(InvalidCase): infer(c)
        dummy={'case_id':c['id'],'region':[],'rows':[{}]*4,'counterexamples':[],'least_counterexample':None}
        with self.assertRaises(Rejected): check(c,dummy)

    def test_candidate_faults_are_prefix_preserving_witnesses(self):
        # missing_api after one successful effectful call
        c=base(); c['history'][0]={'f':declaration(words=(('a',),('a',))), 'g':declaration()}
        c['history'][1]={'f':declaration(words=(('a',),('a',)))}
        c['client']=call('f',var(),'y',call('g',var('y'),'z',ret(var('z'))))
        cert,_=infer(c); check(c,cert)
        row=next(r for r in cert['rows'] if r['state']==1 and r['input']==0)
        self.assertEqual(row['outcome'],{'value':None,'trace':['a'],'error':'missing_api'})
        self.assertEqual([entry['error'] for entry in row['calls']],[None,'missing_api'])
        self.assertEqual(cert['least_counterexample'],{'state':1,'input':0})

        # missing_default after the same successful prefix
        c=base(); c['history'][0]={'f':declaration(words=(('a',),('a',))), 'g':declaration(default={'value':0,'trace':[]})}
        c['history'][1]={'f':declaration(words=(('a',),('a',))), 'g':declaration(default=None)}
        c['client']=call('f',var(),'y',call('g',None,'z',ret(var('z'))))
        cert,_=infer(c); check(c,cert)
        row=next(r for r in cert['rows'] if r['state']==1 and r['input']==0)
        self.assertEqual(row['outcome'],{'value':None,'trace':['a'],'error':'missing_default'})
        self.assertEqual([entry['error'] for entry in row['calls']],[None,'missing_default'])
        self.assertEqual(cert['least_counterexample'],{'state':1,'input':0})

    def test_nonempty_input_subset_controls_row_count(self):
        for inputs in ([0],[1],[0,1]):
            with self.subTest(inputs=inputs):
                c=base(); c['inputs']=inputs
                cert,metrics=infer(c); check(c,cert)
                expected=[(state,x) for state in range(len(c['history'])) for x in inputs]
                self.assertEqual(len(cert['rows']),len(c['history'])*len(inputs))
                self.assertEqual(metrics['executions'],len(c['history'])*len(inputs))
                self.assertEqual([(r['state'],r['input']) for r in cert['rows']],expected)

    def test_trace_bound_is_rejection(self):
        c=base(); c['trace_limit']=0
        c['history'][1]['f']=declaration(words=(('a',),('a',)))
        with self.assertRaises(BoundExceeded): infer(c)
        with self.assertRaises(Rejected):
            check(c,{'case_id':c['id'],'region':[0],'rows':[{}]*4,'counterexamples':[],'least_counterexample':None})

    def test_duplicate_json_keys(self):
        with temporary_directory() as d:
            p=Path(d)/'case.json'; p.write_text('{"a":1,"a":2}')
            with self.assertRaises(InvalidCase): load_json(p)
            with self.assertRaises(Rejected): read_json(p)

    def test_nonfinite_json(self):
        with temporary_directory() as d:
            p=Path(d)/'case.json'; p.write_text('{"a":NaN}')
            with self.assertRaises(InvalidCase): load_json(p)
            with self.assertRaises(Rejected): read_json(p)

    def test_json_byte_bound(self):
        with temporary_directory() as d:
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

    def test_frozen_family_template_contract(self):
        truth=list(history_cases()); effects=list(effect_history_cases()); scholarly=scholarly_cases()
        self.assertEqual((len(truth),len(effects)),(4*5*5*6,4*5*5*6))
        def has_op(term,wanted):
            if term['op']==wanted: return True
            if term['op']=='let': return has_op(term['body'],wanted)
            if term['op'] in ('if','if_present','if_version'):
                return has_op(term['then'],wanted) or has_op(term['else'],wanted)
            return False
        self.assertTrue(all(not has_op(case['client'],'if_version') for case in truth))
        self.assertEqual(max(validate(case)['call_sites'] for case in truth),2)
        self.assertEqual(max(validate(case)['call_sites'] for case in effects),2)
        self.assertEqual(max(validate(case)['call_sites'] for case,_,_ in scholarly),3)
        self.assertEqual(len(TRUTH_TEMPLATE_NAMES),6)
        self.assertEqual(len(EFFECT_TEMPLATE_NAMES),6)
        self.assertEqual([sum(i%6==j for i in range(len(truth))) for j in range(6)],[100]*6)
        self.assertEqual([sum(i%6==j for i in range(len(effects))) for j in range(6)],[100]*6)

    def test_guard_endpoint_enumerator_against_component_oracle(self):
        counts={'exists':0,'absent':0}; queries=0
        for n in range(1,7):
            for safe in range(1<<n):
                for k in (1,2,3):
                    queries+=1
                    got=greatest_sound_by_endpoints(safe,n,k)
                    expected=component_oracle(safe,n,k)
                    self.assertEqual(got,expected)
                    counts['exists' if got is not None else 'absent']+=1
        self.assertEqual((queries,counts['exists'],counts['absent']),(378,306,72))
        self.assertIn(0b0110,endpoint_union_masks(4,1))
        self.assertEqual(component_count(0b0110,4),1)

    def test_partition_refinement_preserves_policy_supports(self):
        coarse={'choices':2,'blocks':[0,0],'safe_choices':[[0],[1]]}
        fine={'choices':2,'blocks':[0,1],'safe_choices':[[0],[1]]}
        self.assertTrue(is_refinement(fine['blocks'],coarse['blocks']))
        self.assertTrue(enumerate_supports(coarse) <= enumerate_supports(fine))

    def test_composition_false_acceptance_depends_on_input_domain(self):
        functions = [(0, 0), (1, 0), (0, 1), (1, 1)]
        accepted = singleton_errors = full_domain_errors = 0
        for f0, f1, g0, g1 in product(functions, repeat=4):
            local = f0[0] == f1[0] and g0[0] == g1[0]
            if local:
                accepted += 1
                singleton_errors += g0[f0[0]] != g1[f1[0]]
                full_domain_errors += any(g0[f0[x]] != g1[f1[x]] for x in (0, 1))
        self.assertEqual((accepted, singleton_errors, full_domain_errors), (64, 16, 32))

    def test_uniform_checker_accepts_noncanonical_valid_certificates(self):
        positive={'choices':2,'blocks':[0,0],'safe_choices':[[0,1],[0,1]]}
        alternative={'greatest_region':[0,1],'policy':[1],'obstruction':None}
        check_uniform(positive,alternative)
        negative={'choices':2,'blocks':[0,0,0,0],
                  'safe_choices':[[0],[1],[0],[1]]}
        alternative={'greatest_region':None,'policy':None,
            'obstruction':{'block':0,'states':[0,1],
              'choice_rejections':[{'choice':0,'state':1},{'choice':1,'state':0}],
              'deletion_witnesses':[{'removed_state':0,'choice':1},
                                    {'removed_state':1,'choice':0}]}}
        check_uniform(negative,alternative)
        self.assertNotEqual(solve(negative),alternative)

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
