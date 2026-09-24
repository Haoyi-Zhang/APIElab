"""Strict finite-circuit admission and construction tests."""
import unittest
from copy import deepcopy
from compatibility.succinct import construct,scalar_certificate
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

if __name__=='__main__':unittest.main()
