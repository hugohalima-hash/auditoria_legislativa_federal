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

class ResumeTest(unittest.TestCase):
    def test_resume_only_missing_documents(self):
        import tempfile, hashlib, json, gzip
        raw=b'Art. 1 Regra.'
        sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        entries=[{'path':f'federal/{n}.md','sha':sha} for n in (1,2)]
        with tempfile.TemporaryDirectory() as folder, patch.object(m,'catalog',return_value=entries), patch.object(m,'get',return_value=raw) as network:
            first=m.collect(folder,1)
            self.assertEqual(first['pendentes'],1)
            second=m.collect(folder)
            self.assertEqual(second['reutilizados'],1)
            self.assertEqual(second['pendentes'],0)
            self.assertEqual(network.call_count,2)
            with gzip.open(m.Path(folder)/'documentos.jsonl.gz','rt') as f:
                self.assertEqual(len(list(f)),2)
    def test_corrupted_checkpoint_not_exported_on_fetch_failure(self):
        import tempfile, hashlib, sqlite3, json, gzip
        raw=b'Art. 1 Regra.'
        sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        entries=[{'path':'federal/1.md','sha':sha}]
        with tempfile.TemporaryDirectory() as folder, patch.object(m,'catalog',return_value=entries), patch.object(m,'get',return_value=raw):
            m.collect(folder)
            db=sqlite3.connect(m.Path(folder)/'coleta.sqlite')
            db.execute('UPDATE documentos SET payload=?',(json.dumps({'texto':'alterado'}),)); db.commit(); db.close()
            with patch.object(m,'extract',side_effect=ValueError('indisponivel')):
                result=m.collect(folder)
            self.assertEqual(result['pendentes'],1)
            with gzip.open(m.Path(folder)/'documentos.jsonl.gz','rt') as f:
                self.assertEqual(f.read(),'')
    def test_catalog_prunes_auxiliary_trees(self):
        with patch.object(m,'tree',side_effect=[{'tree':[{'path':'federal','sha':'f'}]}, {'tree':[{'path':'_backup','type':'tree','sha':'b'},{'path':'leis','type':'tree','sha':'l'}]}]), patch.object(m,'walk',return_value=[]) as walk:
            m.catalog()
            walk.assert_called_once_with('l','federal/leis/')
