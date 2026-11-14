import gzip
import json
import tempfile
import unittest
from pathlib import Path
from scripts.comparar import segments, official_links, run, review_valid

def doc(name,text):
    return dict(arquivo=name,texto=text,url_acervo='https://example.org/'+name,sha256='fixture',links_no_documento=[])

class ComparisonTest(unittest.TestCase):
    def test_complete_article_with_paragraphs(self):
        blocks=list(segments(doc('a','Título\n**Art. 1º** Regra\n§ 1º Exceção\nI - item\n**Art. 2º** Outra regra')))
        self.assertEqual(len(blocks),2)
        self.assertIn('§ 1º Exceção\nI - item',blocks[0]['texto'])
        self.assertEqual(blocks[1]['linha'],5)
    def test_repeated_articles_have_distinct_ids(self):
        blocks=list(segments(doc('a','Art. 1º regra\nADCT\nArt. 1º regra')))
        self.assertNotEqual(blocks[0]['id'],blocks[1]['id'])
    def test_official_link_hostname(self):
        d=doc('a',''); d['links_no_documento']=['https://www.planalto.gov.br/x','https://planalto.gov.br.evil.org/x']
        self.assertEqual(official_links(d),d['links_no_documento'][:1])
    def test_no_confirmed_conflicts_from_lexical_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'input.gz'
            with gzip.open(source,'wt') as f:
                for name,text in [('a','Art. 1º É permitido transportar animais domésticos em veículos públicos municipais.'),('b','Art. 1º É proibido transportar animais domésticos em veículos públicos municipais.'),('c','Documento sem marcadores')]:
                    f.write(json.dumps(doc(name,text))+'\n')
            summary=run(source,root/'out')
            self.assertEqual(summary['conflitos_confirmados'],0)
            self.assertEqual(summary['candidatos'],1)
            self.assertEqual(summary['documentos_sem_artigos'],1)
            result=json.loads((root/'out/candidatos.jsonl').read_text())
            self.assertIsNone(result['conclusao'])
            self.assertIn('vocabulario_permissao_proibicao',result['sinais'])
    def test_missing_evidence_rejected(self):
        self.assertFalse(review_valid({'classificacao':'conflito_confirmado','dispositivos':['a','b']},{'a','b'}))

if __name__=='__main__': unittest.main()

class InvalidLinksTest(unittest.TestCase):
    def test_bad_ipv6_does_not_drop_article(self):
        d=doc('a','Art. 1º É permitido transportar animais domésticos em veículos públicos municipais.')
        d['links_no_documento']=['https://[invalido','https://www.planalto.gov.br/lei.htm']
        blocks=list(segments(d))
        self.assertEqual(len(blocks),1)
        self.assertEqual(blocks[0]['texto'],d['texto'])
        self.assertEqual(blocks[0]['links_oficiais_candidatos'],d['links_no_documento'][1:])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'input.gz'
            with gzip.open(source,'wt') as f: f.write(json.dumps(d)+'\n')
            summary=run(source,root/'out')
            self.assertEqual(summary['documentos'],1)
            self.assertEqual(summary['artigos'],1)
            self.assertEqual(summary['links_invalidos'],1)
            issue=json.loads((root/'out/links_invalidos.jsonl').read_text())
            self.assertEqual(issue['url'],'https://[invalido')
    def test_invalid_link_shapes(self):
        d=doc('a','')
        d['links_no_documento']=[None, 12, 'https:///sem-host', 'javascript:alert(1)', 'https://planalto.gov.br.evil.org/a']
        self.assertEqual(official_links(d),[])
