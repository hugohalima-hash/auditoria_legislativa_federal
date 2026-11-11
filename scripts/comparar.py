"""Triagem documental reproduzível; não emite conclusões jurídicas."""
import argparse
import gzip
import hashlib
import html
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ARTICLE = re.compile(r'^\s*(?:[#*>]+\s*)?(?:\*\*)?Art\.?\s*(\d+(?:[.\d]*\d)?(?:[º°o])?(?:\s*[-–]\s*[A-Z]+)?)(?=\W|$)', re.I)
STOP = set('a o as os de da do das dos em no na nos nas um uma e ou que para por com se ao aos sua seu suas seus artigo art lei será ser são não é fica ficam nos termos disposto desta deste pelo pela pelos pelas'.split())
CHECKS = ['identidade_e_versao', 'texto_oficial', 'vigencia_e_transicao', 'mesma_situacao_fatica', 'hierarquia', 'especialidade', 'cronologia', 'jurisprudencia', 'contrapontos']

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))

def tokens(text):
    stop = {normalized(x) for x in STOP}
    return set(w for w in re.findall(r'[a-z]{3,}', normalized(text)) if w not in stop)

def official_links(doc):
    domains = ('planalto.gov.br', 'camara.leg.br', 'senado.leg.br', 'in.gov.br', 'stf.jus.br', 'stj.jus.br')
    return [u for u in doc.get('links_no_documento', []) if any((urlsplit(u).hostname or '').lower() == d or (urlsplit(u).hostname or '').lower().endswith('.'+d) for d in domains)]

def segments(doc):
    lines = doc['texto'].splitlines()
    starts = [(i, m.group(1)) for i, line in enumerate(lines) if (m := ARTICLE.match(line))]
    for k, (start, number) in enumerate(starts):
        end = starts[k+1][0] if k+1 < len(starts) else len(lines)
        # Keep complete blocks, including paragraphs/incisos and surrounding notes.
        text = '\n'.join(lines[start:end]).strip()
        uid = hashlib.sha256(f"{doc['arquivo']}:{start+1}:{text}".encode()).hexdigest()
        yield {'id': uid, 'arquivo': doc['arquivo'], 'artigo': number, 'linha': start+1,
               'texto': text, 'url': doc['url_acervo'], 'sha256_documento': doc['sha256'],
               'links_oficiais_candidatos': official_links(doc), 'vigencia': 'nao_verificada'}

def signals(a, b):
    def modal(t):
        t = normalized(t)
        return bool(re.search(r'\b(?:vedad[oa]s?|proibid[oa]s?|nao podera)\b', t)), bool(re.search(r'\b(?:permitid[oa]s?|autorizad[oa]s?|podera)\b', re.sub('nao podera', '', t)))
    am, bm = modal(a), modal(b)
    result = ['proximidade_lexical']
    if (am[0] and bm[1]) or (bm[0] and am[1]): result.append('vocabulario_permissao_proibicao')
    if re.search(r'\d+\s*(?:dias|meses|anos|horas)', a, re.I) and re.search(r'\d+\s*(?:dias|meses|anos|horas)', b, re.I): result.append('prazos_a_conferir')
    return result

def review_valid(review, ids):
    if not review or not set(review.get('dispositivos', [])).issubset(ids) or len(set(review.get('dispositivos', []))) != 2:
        return False
    return (all(isinstance(review.get('verificacoes', {}).get(k), str) and review['verificacoes'][k].strip() for k in CHECKS)
            and bool(review.get('fontes_primarias')) and bool(review.get('fundamentacao'))
            and bool(review.get('responsavel')) and bool(review.get('data'))
            and review.get('classificacao') in {'conflito_confirmado', 'conflito_aparente', 'ambiguidade', 'redundancia', 'lacuna', 'opcao_legislativa', 'descartado'})

def run(source, out, limit=12, threshold=.28):
    out.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(out/'comparacao.sqlite')
    db.executescript('DROP TABLE IF EXISTS artigos; DROP TABLE IF EXISTS busca; CREATE TABLE artigos (id INTEGER PRIMARY KEY, arquivo TEXT, payload TEXT); CREATE VIRTUAL TABLE busca USING fts5(termos);')
    counts = Counter(documentos=0, artigos=0, documentos_sem_artigos=0, pares_recuperados=0, candidatos=0, consultas_saturadas=0, consultas=0)
    df = Counter()
    with gzip.open(source, 'rt', encoding='utf-8') as handle, open(out/'segmentacao_pendencias.jsonl','w',encoding='utf-8') as pending:
        for line in handle:
            doc = json.loads(line); counts['documentos'] += 1
            blocks = list(segments(doc))
            if not blocks:
                counts['documentos_sem_artigos'] += 1
                pending.write(json.dumps({'arquivo':doc['arquivo'], 'motivo':'nenhum_artigo_reconhecido'},ensure_ascii=False)+'\n')
            for block in blocks:
                terms = tokens(block['texto']); df.update(terms)
                row = db.execute('INSERT INTO artigos(arquivo,payload) VALUES (?,?)', (block['arquivo'], json.dumps(block, ensure_ascii=False))).lastrowid
                db.execute('INSERT INTO busca(rowid,termos) VALUES (?,?)', (row, ' '.join(sorted(terms))))
                counts['artigos'] += 1
    db.commit()
    db.execute('CREATE TABLE IF NOT EXISTS pares (a INTEGER, b INTEGER, PRIMARY KEY(a,b))')
    db.execute('DELETE FROM pares')
    with open(out/'candidatos.jsonl','w',encoding='utf-8') as output, open(out/'comparativo.html','w',encoding='utf-8') as page:
        page.write('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Comparativo documental</title><style>body{font:16px system-ui;max-width:1400px;margin:32px auto;padding:20px}table{width:100%;table-layout:fixed}td{vertical-align:top;border:1px solid #ccc;padding:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:20px 0}a{overflow-wrap:anywhere}</style><h1>Comparativo documental — triagem preliminar</h1><p>Os pares abaixo são candidatos à revisão. Similaridade, prazos diferentes e vocabulário oposto não demonstram conflito jurídico. Textos vêm de acervo secundário; vigência e autenticidade oficial pendentes. A busca é limitada e não cobre todas as combinações ou conflitos sem semelhança textual.</p>')
        for row, raw in db.execute('SELECT id,payload FROM artigos ORDER BY id'):
            a = json.loads(raw); at = tokens(a['texto'])
            if len(at) < 5: continue
            terms = sorted(at, key=lambda w:(df[w], w))[:8]
            query = ' OR '.join('"'+w+'"' for w in terms)
            # Exclude same file before LIMIT. Search both directions; deduplicate pairs below.
            matches = db.execute('SELECT artigos.id, artigos.payload FROM busca JOIN artigos ON artigos.id=busca.rowid WHERE busca MATCH ? AND artigos.arquivo != ? ORDER BY rank, artigos.id LIMIT ?', (query,a['arquivo'],limit+1)).fetchall()
            counts['consultas'] += 1
            counts['consultas_saturadas'] += len(matches) > limit
            for other, braw in matches[:limit]:
                key = tuple(sorted((row, other)))
                if db.execute('INSERT OR IGNORE INTO pares VALUES (?,?)',key).rowcount == 0: continue
                counts['pares_recuperados'] += 1
                b = json.loads(braw); bt = tokens(b['texto'])
                score = len(at & bt) / max(1,len(at | bt))
                if score < threshold: continue
                cid = hashlib.sha256('|'.join(sorted([a['id'],b['id']])).encode()).hexdigest()
                candidate = {'id':cid,'a':a,'b':b,'similaridade_jaccard':round(score,4),'sinais':signals(a['texto'],b['texto']),'status':'pendente_revisao','conclusao':None,'verificacoes_pendentes':CHECKS}
                output.write(json.dumps(candidate,ensure_ascii=False)+'\n'); counts['candidatos'] += 1
                page.write('<details><summary>'+html.escape(', '.join(candidate['sinais']))+f' — similaridade {score:.2f}</summary><p>ID: {cid}</p><table><tr>')
                for block in (a,b):
                    page.write('<td><strong>'+html.escape(block['arquivo']+' — Art. '+block['artigo'])+'</strong><p><a href="'+html.escape(block['url'],quote=True)+'">Documento do acervo</a> • linha '+str(block['linha'])+'</p><pre>'+html.escape(block['texto'])+'</pre></td>')
                page.write('</tr></table><p>Pendente: '+html.escape(', '.join(CHECKS))+'</p></details>')
        counts['pares_possiveis_entre_arquivos'] = (counts['artigos']*(counts['artigos']-1)//2 - sum(n*(n-1)//2 for (n,) in db.execute('SELECT COUNT(*) FROM artigos GROUP BY arquivo')))
        summary = dict(counts, conflitos_confirmados=0, cobertura_juridica='nao_determinada', escopo='triagem_lexical_de_artigos_do_acervo', limite_vizinhos=limit, limiar=threshold, analise_juridica='pendente')
        page.write('<h2>Cobertura desta execução</h2><pre>'+html.escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre></html>')
    (out/'cobertura_comparacao.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    db.commit(); db.close()
    return summary

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--entrada', type=Path, default=Path('resultados/documentos.jsonl.gz'))
    parser.add_argument('--saida', type=Path, default=Path('resultados/comparacao'))
    args = parser.parse_args()
    print(json.dumps(run(args.entrada,args.saida),ensure_ascii=False))
