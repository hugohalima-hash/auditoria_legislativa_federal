import concurrent.futures, gzip, hashlib, json, os, re, time
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
def main():
    out=Path('resultados'); out.mkdir(exist_ok=True)
    entries=[]
    for e in tree(REF)['tree']:
        if e['path']=='constituicao.md': entries.append(e)
        elif e['path'] in {'federal','reguladores','tratados'}: entries.extend(walk(e['sha'],e['path']+'/'))
    entries.sort(key=lambda e:e['path'])
    with gzip.open(out/'manifesto.jsonl.gz','wt',encoding='utf-8') as f:
        for e in entries: f.write(json.dumps(e,ensure_ascii=False)+'\n')
    docs=[e for e in entries if selected(e['path'])]
    status={'commit_fonte':REF,'arquivos_catalogados':len(entries),'documentos_candidatos':len(docs),'textos_verificados':0,'falhas':0,'cobertura_legislacao_brasileira':'nao_determinada','analise_juridica':'pendente'}
    def save(): (out/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    with gzip.open(out/'documentos.jsonl.gz','wt',encoding='utf-8') as good, open(out/'falhas.jsonl','w',encoding='utf-8') as bad, concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for offset in range(0,len(docs),64):
            futures=[(e,pool.submit(extract,e)) for e in docs[offset:offset+64]]
            for e,f in futures:
                try:
                    good.write(json.dumps(f.result(),ensure_ascii=False)+'\n'); status['textos_verificados']+=1
                except Exception as exc:
                    bad.write(json.dumps({'arquivo':e['path'],'erro':str(exc)},ensure_ascii=False)+'\n'); status['falhas']+=1
            good.flush(); bad.flush(); save(); print(json.dumps(status),flush=True)
    if status['falhas']: raise SystemExit('Downloads com falha: consultar falhas.jsonl')
if __name__=='__main__': main()
