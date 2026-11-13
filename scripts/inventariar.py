import argparse, concurrent.futures, gzip, hashlib, json, os, re, sqlite3, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
REF='c9f21b4ab11aa0d7ca6fe861d75028e94219c2d6'
REPO='ctresb/leis'
def get(url,api=False):
    headers={'User-Agent':'inventario-legislativo'}
    if api and os.getenv('GH_TOKEN'): headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    for attempt in range(5):
        try:
            with urlopen(Request(url,headers=headers),timeout=90) as r: return r.read()
        except Exception:
            if attempt==4: raise
            time.sleep(2**attempt)
def tree(sha,recursive=False):
    return json.loads(get(f'https://api.github.com/repos/{REPO}/git/trees/{sha}'+('?recursive=1' if recursive else ''),True))
def walk(sha,prefix):
    data=tree(sha,True)
    if data.get('truncated'):
        data=tree(sha)
        if data.get('truncated'): raise ValueError('Arvore truncada: '+prefix)
        for e in data['tree']:
            if e['type']=='tree': yield from walk(e['sha'],prefix+e['path']+'/')
            elif e['type']=='blob': yield dict(e,path=prefix+e['path'])
    else:
        for e in data['tree']:
            if e['type']=='blob': yield dict(e,path=prefix+e['path'])
def selected(path):
    return path.endswith('.md') and not any(p.startswith(('_','.')) for p in path.split('/')) and path.split('/')[-1].lower() not in {'readme.md','cobertura.md','progresso.md'}
def extract(e):
    url=f'https://raw.githubusercontent.com/{REPO}/{REF}/'+quote(e['path'])
    raw=get(url)
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=e['sha']: raise ValueError('Hash divergente')
    text=raw.decode('utf-8')
    return {'arquivo':e['path'],'git_blob':blob,'sha256':hashlib.sha256(raw).hexdigest(),'url_acervo':url,'texto':text,'links_no_documento':sorted(set(re.findall(r'https?://[^\s<>\)\]]+',text))),'marcadores_artigos':[{'linha':i,'texto':line} for i,line in enumerate(text.splitlines(),1) if re.match(r'^\s*(?:[#*>]+\s*)?(?:\*\*)?Art\.?\s*\d',line,re.I)],'vigencia':'nao_verificada','fonte_primaria':'pendente'}
def catalog():
    """Prune auxiliary directories before recursive tree requests."""
    entries=[]
    for e in tree(REF)['tree']:
        if e['path']=='constituicao.md': entries.append(e)
        elif e['path'] in {'federal','reguladores','tratados'}:
            prefix=e['path']+'/'
            data=tree(e['sha'])
            if data.get('truncated'): raise ValueError('Arvore truncada: '+prefix)
            for child in data['tree']:
                if child['path'].startswith(('_','.')): continue
                if child['type']=='tree':
                    entries.extend(x for x in walk(child['sha'],prefix+child['path']+'/') if selected(x['path']))
                elif child['type']=='blob' and selected(prefix+child['path']):
                    entries.append(dict(child,path=prefix+child['path']))
            print(json.dumps({'fase':'catalogacao','grupo':e['path'],'documentos':len(entries)}),flush=True)
    return sorted(entries,key=lambda e:(e['path']!='constituicao.md',e['path']))

def collect(out, max_documents=0):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    status={'commit_fonte':REF,'fase':'catalogacao','analise_juridica':'pendente','cobertura_legislacao_brasileira':'nao_determinada'}
    def save():
        tmp=out/'status.json.tmp'; tmp.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(out/'status.json')
    save()
    manifest=out/'catalogo.json'
    if manifest.exists():
        cached=json.loads(manifest.read_text(encoding='utf-8'))
        if cached['commit_fonte']!=REF: raise ValueError('Catalogo de outra versao')
        docs=cached['documentos']
    else:
        docs=catalog()
        temp=out/'catalogo.json.tmp'
        temp.write_text(json.dumps({'commit_fonte':REF,'documentos':docs},ensure_ascii=False),encoding='utf-8'); temp.replace(manifest)
    with gzip.open(out/'manifesto.jsonl.gz','wt',encoding='utf-8') as f:
        for e in docs: f.write(json.dumps(e,ensure_ascii=False)+'\n')
    db=sqlite3.connect(out/'coleta.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS documentos (arquivo TEXT PRIMARY KEY, blob TEXT, payload TEXT)')
    pending=[]; verified=0
    for e in docs:
        row=db.execute('SELECT blob,payload FROM documentos WHERE arquivo=?',(e['path'],)).fetchone()
        valid=False
        if row and row[0]==e['sha']:
            d=json.loads(row[1]); raw=d['texto'].encode('utf-8')
            valid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha']
        if valid: verified+=1
        else:
            db.execute('DELETE FROM documentos WHERE arquivo=?',(e['path'],))
            pending.append(e)
    selected_batch=pending[:max_documents] if max_documents else pending
    status.update(fase='coleta',documentos_candidatos=len(docs),textos_verificados=verified,reutilizados=verified,pendentes=len(pending),falhas=0)
    save()
    with open(out/'falhas.jsonl','w',encoding='utf-8') as bad, concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for offset in range(0,len(selected_batch),32):
            futures=[(e,pool.submit(extract,e)) for e in selected_batch[offset:offset+32]]
            for e,f in futures:
                try:
                    document=f.result()
                    db.execute('INSERT OR REPLACE INTO documentos VALUES (?,?,?)',(e['path'],e['sha'],json.dumps(document,ensure_ascii=False)))
                    status['textos_verificados']+=1
                except Exception as exc:
                    bad.write(json.dumps({'arquivo':e['path'],'erro':str(exc)},ensure_ascii=False)+'\n'); status['falhas']+=1
            db.commit(); bad.flush()
            status['pendentes']=len(docs)-status['textos_verificados']; save(); print(json.dumps(status),flush=True)
    # Complete gzip export only after the checkpoint transaction is durable.
    with gzip.open(out/'documentos.jsonl.gz.tmp','wt',encoding='utf-8') as f:
        for e in docs:
            row=db.execute('SELECT payload FROM documentos WHERE arquivo=? AND blob=?',(e['path'],e['sha'])).fetchone()
            if row: f.write(row[0]+'\n')
    (out/'documentos.jsonl.gz.tmp').replace(out/'documentos.jsonl.gz')
    db.close()
    status['fase']='concluida' if status['pendentes']==0 else 'parcial'; save()
    return status

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--saida',default='resultados')
    parser.add_argument('--max-documentos',type=int,default=0,help='0 coleta todos; limite positivo preserva checkpoint parcial')
    args=parser.parse_args()
    if args.max_documentos<0: parser.error('Limite deve ser nao negativo')
    status=collect(args.saida,args.max_documentos)
    if status['pendentes']: raise SystemExit('Coleta parcial: retomar com o mesmo diretorio de saida')
if __name__=='__main__': main()
