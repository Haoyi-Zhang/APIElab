"""Strict finite-circuit admission and construction tests."""
import unittest
from copy import deepcopy
from compatibility.succinct import construct,scalar_certificate,evaluate_nodes
from compatibility.succinct_check import check,admit,Rejected
from compatibility.succinct_campaign import oracle

class CircuitTests(unittest.TestCase):
    def setUp(self):
        self.case={'id':'T001','quantified':True,'queries':[10,5],'post_table':6}
        self.c=construct(self.case);self.p=scalar_certificate(self.c)
    def test_complete(self): self.assertTrue(check(self.c,self.p))
    def test_scalar_and_direct(self): self.assertEqual(self.p['policy_supports'],oracle(self.case)[3])
    def test_cycle(self):
        self.c['nodes'][0]=['not',0]
        with self.assertRaises(Rejected):admit(self.c)
    def test_negative_reference(self):
        self.c['nodes'][0]=['not',-1]
        with self.assertRaises(Rejected):admit(self.c)
    def test_boolean_index(self):
        self.c['outputs'][0]=False
        with self.assertRaises(Rejected):admit(self.c)
    def test_unknown_gate(self):
        self.c['nodes'][0]=['call',0]
        with self.assertRaises(Rejected):admit(self.c)
    def test_bad_arity(self):
        self.c['nodes'][0]=['const',1,1]
        with self.assertRaises(Rejected):admit(self.c)
    def test_nonbinary(self):
        self.c['nodes'][0]=['const',2]
        with self.assertRaises(Rejected):admit(self.c)
    def test_width_cap(self):
        self.c['a_bits']=9
        with self.assertRaises(Rejected):admit(self.c)
    def test_output_cap(self):
        self.c['outputs']=[0]*33
        with self.assertRaises(Rejected):admit(self.c)
    def test_omitted_policy(self):
        self.p['policy_supports'].pop()
        with self.assertRaises(Rejected):check(self.c,self.p)
    def test_bool_policy(self):
        self.p['policy_supports'][0][0]=False
        with self.assertRaises(Rejected):check(self.c,self.p)
    def test_flipped_conclusion(self):
        self.p['greatest_exists']=not self.p['greatest_exists']
        with self.assertRaises(Rejected):check(self.c,self.p)
    def test_bad_semantics(self):
        self.c['nodes'][self.c['outputs'][0]]=['const',0]
        with self.assertRaises(Rejected):check(self.c,self.p)
    def test_negative_controls(self):
        c={'id':'T002','quantified':False,'queries':[1],'post_table':0}
        self.assertFalse(scalar_certificate(construct(c))['greatest_exists'])
        c['post_table']=3
        self.assertTrue(scalar_certificate(construct(c))['greatest_exists'])

    def test_fixed_selection_precedes_universal_input(self):
        rows=[{'x':x,'C1':x,'C2':1-x} for x in (0,1)]
        u=sum(all(row[name] for row in rows) for name in ('C1','C2'))
        s=max(sum(all(row[name] for row in rows) for name in ('C1','C2')) for _a in (0,1))
        self.assertEqual((u,s),(0,0))

    def test_threshold_sentinel_and_endpoint_supports(self):
        for q in (1,2):
            cases=[({'id':f'L{q}','quantified':False,'queries':[0]*q,'post_table':1},0),
                   ({'id':f'H{q}','quantified':False,'queries':[1]*q,'post_table':0},2*q+1)]
            for case,k in cases:
                circuit,layout=construct(case,with_layout=True)
                self.assertEqual(len(circuit['outputs']),2*q+3)
                self.assertTrue(all(evaluate_nodes(circuit,a,0)[layout['sentinel']]==0
                                    for a in range(1<<circuit['a_bits'])))
                proof=scalar_certificate(circuit)
                self.assertEqual(proof['support'],list(range(k+2)))
                self.assertEqual(proof['greatest_exists'],k%2==0)

if __name__=='__main__':unittest.main()
