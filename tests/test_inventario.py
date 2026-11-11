import unittest
from unittest.mock import patch
from scripts import inventariar as m
class InventoryTest(unittest.TestCase):
    def test_auxiliary_not_norm(self):
        self.assertFalse(m.selected('federal/_historico/lei.md'))
        self.assertFalse(m.selected('federal/README.md'))
        self.assertTrue(m.selected('federal/leis-complementares/1962/lcp1.md'))
    def test_truncated_recurses_without_using_partial_result(self):
        responses = [{'truncated':True,'tree':[{'type':'blob','path':'incomplete'}]}, {'tree':[{'type':'tree','path':'ano','sha':'child'}]}, {'truncated':False,'tree':[{'type':'blob','path':'lei.md','sha':'abc'}]}]
        with patch.object(m,'tree',side_effect=responses):
            self.assertEqual(list(m.walk('root','federal/')), [{'type':'blob','path':'federal/ano/lei.md','sha':'abc'}])
    def test_hash_mismatch_rejected(self):
        with patch.object(m,'get',return_value=b'alterado'):
            with self.assertRaises(ValueError): m.extract({'path':'lei.md','sha':'errado'})
