"""Deterministic co-edit proxy graphs; source data are not ownership decisions."""
from bisect import bisect_left
from collections import Counter,defaultdict
from fractions import Fraction
import hashlib,json,sqlite3
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]

def seconds(text):
    match=re.fullmatch(r'(?:(\d+) days?, )?(\d+):(\d+):(\d+)(?:\.(\d+))?',text)
    if not match:raise ValueError(text)
    day,h,m,s,micro=match.groups()
    return int(day or 0)*86400+int(h)*3600+int(m)*60+int(s)+float('0.'+(micro or '0'))

def main():
    cfg=json.loads((root/'configs/public_comparison_v5.json').read_text())
    directory=root/'data/bath_00621';db=directory/'anon_cad_metadata.db'
    con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
    output=directory/'graphs';output.mkdir(exist_ok=False)
    reports=[]
    for project in cfg['projects']:
        raw=con.execute('SELECT id,type,subsystem,time_delta FROM metadata WHERE team=?',(project,)).fetchall()
        attributes={};times=defaultdict(set)
        for ident,kind,subsystem,t in raw:
            attributes.setdefault(ident,(kind,subsystem));assert attributes[ident]==(kind,subsystem)
            times[ident].add(seconds(t))
        ids=sorted(i for i in times if len(times[i])>=cfg['minimum_file_events'])
        pos={ident:i for i,ident in enumerate(ids)}
        events=sorted((t,pos[ident]) for ident in ids for t in times[ident]);timestamps=[t for t,i in events]
        for hours in cfg['windows_hours']:
            counts=Counter()
            for ident in ids:
                i=pos[ident];ts=sorted(times[ident])
                for k,t in enumerate(ts):
                    end=min(t+hours*3600,ts[k+1] if k+1<len(ts) else float('inf'))
                    a,b=bisect_left(timestamps,t),bisect_left(timestamps,end)
                    for j in {j for _,j in events[a:b] if j!=i}:counts[i,j]+=1
            edges=[];probabilities=[]
            for i in range(len(ids)):
                for j in range(i+1,len(ids)):
                    u=(Fraction(counts[i,j],len(times[ids[i]]))+Fraction(counts[j,i],len(times[ids[j]])))/2
                    assert 0<=u<=1
                    if u>=Fraction(cfg['edge_probability_threshold']):
                        v=u*cfg['edge_weight_scale'];w=(2*v.numerator+v.denominator)//(2*v.denominator)
                        edges.append((i,j,max(1,w)));probabilities.append([i,j,u.numerator,u.denominator])
            recourse=[1+int(len(times[i])>=10)+int(attributes[i][0]=='assembly') for i in ids]
            adj=[[] for _ in ids]
            for i,j,w in edges:adj[i].append(j);adj[j].append(i)
            unseen=set(range(len(ids)));sizes=[]
            while unseen:
                first=min(unseen);unseen.remove(first);stack=[first];size=0
                while stack:
                    i=stack.pop();size+=1
                    for j in adj[i]:
                        if j in unseen:unseen.remove(j);stack.append(j)
                sizes.append(size)
            graph={'source_doi':cfg['source_doi'],'project':project,'window_hours':hours,
                   'minimum_unique_file_events':cfg['minimum_file_events'],'threshold':cfg['edge_probability_threshold'],
                   'edge_weight_scale':cfg['edge_weight_scale'],'vertices':[{'id':i,'type':attributes[i][0],'subsystem':attributes[i][1],'unique_events':len(times[i])} for i in ids],
                   'edges':edges,'edge_probabilities':probabilities,'recourse':recourse,
                   'interpretation':'Symmetrized temporal co-edit association, not verified physical interface or causal dependency; responsibility pools/costs/perturbations are synthetic.'}
            file=output/f'{project}_{hours}h.json';file.write_text(json.dumps(graph,indent=2)+'\n')
            reports.append({'project':project,'hours':hours,'n':len(ids),'m':len(edges),'components':len(sizes),
                            'largest_component':max(sizes),'isolates':sum(not a for a in adj),'raw_events':len(raw),
                            'retained_unique_events':len(events),'graph_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    provenance={'source_url':'https://researchdata.bath.ac.uk/621/','doi':cfg['source_doi'],'access_date':'2026-10-28',
                'source_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()},
                'importer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'config_sha256':hashlib.sha256((root/'configs/public_comparison_v5.json').read_bytes()).hexdigest(),
                'construction':'Deduplicate file/timestamp pairs; >=5 events. For each source-file edit count each other file at most once until min(next same-file edit, t+window), inclusive start/exclusive end. Average conditional co-edit frequencies, threshold at 1/4, round 8*probability to integer. Keep every qualifying vertex, including isolates; do not fit windows/thresholds to repair outcomes.',
                'graphs':reports}
    (directory/'provenance_v5.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(provenance,indent=2))

if __name__=='__main__':main()
