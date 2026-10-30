from pathlib import Path
import hashlib,json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path(__file__).resolve().parents[1];paper=root/'paper/manuscript'
paths=['results/public_comparison_v5/summary.json','results/route_comparison_v5/summary.json','data/bath_00621/provenance_v5.json']
pub,route,provenance=[json.loads((root/p).read_text()) for p in paths]
assert pub['solutions_validated'] and route['solutions_validated']
rows=[]
family={'grid':'Grid','modular':'Modular','smallworld':'Small-world','core64':'Core 64','core128':'Core 128'}
ordered=sorted(route['groups'],key=lambda g:({'grid':0,'modular':1,'smallworld':2,'core64':3,'core128':4}[g['key'][0]],g['n']))
for g in ordered+pub['groups']:
 name=family[g['key'][0]] if g['key'][0] in family else f"CAD {g['key'][0]}, {g['key'][1]} h"
 ms=[g['methods'][k] for k in ['FullCP','BARRCP','LRRepair']]
 k='--' if g['CP_region_fraction'] is None else f"{100*g['CP_region_fraction']:.1f}"
 times='/'.join(f"{m['median_s']:.4f}" if g['key'][0] not in family else f"{m['median_s']:.3f}" for m in ms)
 rows.append(f"{name} & {g['n']} & {g['CP_required']}/{g['cases']} & {k} & "+'/'.join(str(m['certified']) for m in ms)+f" & {times} & "+'/'.join(str(m['max_gap']) for m in ms)+r' \\')
(paper/'route_rows.tex').write_text('\n'.join(rows)+'\n')
s=(paper/'main.tex').read_text();replacement='% BEGIN GENERATED ROUTE ROWS\n'+'\n'.join(rows)+'\n% END GENERATED ROUTE ROWS'
s,count=re.subn(r'% BEGIN GENERATED ROUTE ROWS\n.*?% END GENERATED ROUTE ROWS',lambda _:replacement,s,flags=re.S);assert count==1
s=s.replace(r'\begin{tabular}{@{}lrrrrrrr@{}}',r'\begin{tabular}{@{}lrrrrrr@{}}')
results=r'''On 2,048-vertex modular graphs, 14/20 cases require CP; their median paired FullCP/BARRCP speed is 7.30, versus 7.67 in the earlier timing stage. All-case median times are 0.148/0.016 s. For the 64-core family at that size, both CP routes certify 5/5; fresh paired speed is 3.24 (earlier 2.86). LRRepair is faster at 0.173 s median but has maximum actual loss 12 against proved optima and certifies none. On 128-core cases it can lose 26 on the eight cases with a proved reference optimum. The reduced CP route certifies 4/5 per size in the fresh run, compared with 1/5 previously, illustrating wall-clock variability; a reduced core can still remain unresolved.

LRRepair matches 71/72 public optima and certifies 69/72; its worst actual public loss is one. It also matches every proved grid optimum, though some dual bounds remain open. On four censored 2,048-vertex small-world cases, LRRepair gives a better feasible objective than both CP routes (up to 417 lower); its maximum returned gap is 8 versus 418 for CP. Small-world reduction remains ineffective. Thus cut recovery can be preferable for fast feasible repair, while BARR helps exact certification on suitable structure; neither route dominates time, quality, and bound closure. Complete per-case values and previous stages remain available.'''
s=s.replace('ROUTERESULTS',results);(paper/'main.tex').write_text(s)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'savefig.dpi':320})
fig,axs=plt.subplots(1,3,figsize=(7.0,1.85),layout='constrained')
for ax,project in zip(axs,['A','B','C']):
 p=root/f'data/bath_00621/graphs/{project}_12h.json';graph=json.loads(p.read_text());paths.append(str(p.relative_to(root)))
 order=sorted(range(len(graph['vertices'])),key=lambda i:(graph['vertices'][i]['subsystem'],graph['vertices'][i]['id']))
 inverse={v:i for i,v in enumerate(order)};matrix=np.zeros((len(order),len(order)))
 for i,j,w in graph['edges']:matrix[inverse[i],inverse[j]]=matrix[inverse[j],inverse[i]]=w
 im=ax.imshow(matrix,cmap='Blues',vmin=0,vmax=8,interpolation='nearest')
 ax.set_title(f"Project {project}: {len(order)} files, {len(graph['edges'])} edges",fontsize=7.2)
 ax.set_xlabel('Files ordered by subsystem',fontsize=7);ax.set_xticks([]);ax.set_yticks([])
fig.colorbar(im,ax=axs,label='Association weight',shrink=.85,pad=.02)
fig.savefig(paper/'images/public_graphs_v5.png');plt.close(fig)
(paper/'asset_provenance_v5.json').write_text(json.dumps({'inputs':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
print('Built 16 comparison rows and public-source graph figure.')
