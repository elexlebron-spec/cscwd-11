"""Build the illustrative design figure and large/stress table from saved evidence."""
from pathlib import Path
import hashlib
import json
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

root=Path(__file__).resolve().parents[1];out=root/'paper/manuscript'
paths=['results/design_case_v4/case.json','results/scale_holdout_v4/summary.json','results/core_holdout_v4/summary.json']
case,scale,stress=[json.loads((root/p).read_text()) for p in paths]
assert scale['solutions_validated'] and stress['solutions_validated']
rows=[]
groups=scale['groups']+sorted(stress['groups'],key=lambda g:(int(g['family'][4:]),g['n']))
label={'grid':'Grid','modular':'Modular','smallworld':'Small-world','core64':'Core 64','core128':'Core 128'}
for g in groups:
    speed='-- (0)' if g['exact_CP_median_speed'] is None else f"{g['exact_CP_median_speed']:.2f} ({g['exact_CP_pairs']})"
    rows.append(f"{label[g['family']]} & {g['n']} & {g['CP_required']}/{g['cases']} & {100*g['CP_median_region_fraction']:.1f} & {g['full_solved']}/{g['barr_solved']} & {g['all_median_full_s']:.3f}/{g['all_median_barr_s']:.3f} & {g['full_max_gap']}/{g['barr_max_gap']} & {speed} \\\\")
(out/'scale_rows.tex').write_text('\n'.join(rows)+'\n')
source=out/'main.tex';text=source.read_text()
pattern=r'% BEGIN GENERATED SCALE ROWS\n.*?% END GENERATED SCALE ROWS'
replacement='% BEGIN GENERATED SCALE ROWS\n'+'\n'.join(rows)+'\n% END GENERATED SCALE ROWS'
text,count=re.subn(pattern,lambda _:replacement,text,flags=re.S)
assert count==1, 'Expected exactly one follow-up table marker pair'
assert replacement in text
source.write_text(text)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'savefig.dpi':320})
fig,ax=plt.subplots(figsize=(7.05,1.95),layout='constrained')
positions={0:(0,0),1:(.8,.5),2:(.8,-.5),3:(1.9,-.5),4:(2.9,-.5),5:(3.9,-.5),
           6:(4.9,-.5),7:(5.7,0),8:(5.7,-1),9:(6.7,-1),10:(7.7,-1),11:(8.7,-1)}
for i,j,w in case['old']['edges']:
    a,b=positions[i],positions[j]
    ax.plot([a[0],b[0]],[a[1],b[1]],color='#777777',lw=1,zorder=1)
    ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.08,str(w),fontsize=6,ha='center',
            bbox={'facecolor':'white','edgecolor':'none','pad':.1})
ax.add_patch(Ellipse((.43,0),1.65,1.7,facecolor='#eef3f7',edgecolor='#aa4242',ls='--',lw=1,zorder=0))
colors=['#24668b','#d0893b']
for i,(x,y) in positions.items():
    old=case['old']['x0'][i];new=case['budget_optimum']['x'][i]
    ax.scatter([x],[y],s=235,c=[colors[new]],edgecolors=[colors[old]],linewidths=3,zorder=3)
    ax.text(x,y,str(i),ha='center',va='center',color='white',fontsize=7,zorder=4)
    ax.text(x,y+(.28 if i not in (0,2,8) else -.30),case['names'][i],ha='center',fontsize=6.2)
ax.annotate('A={0}: cost of A-team label 0 -> 40',xy=(0,.12),xytext=(1.65,.95),
            fontsize=7,ha='left',arrowprops={'arrowstyle':'->','color':'#aa4242','lw':.8})
ax.text(-.3,-1.3,'Dashed region K={0,1,2}; handoff costs (2,1,2); total 5 = B',fontsize=7)
ax.text(1.9,-.87,'r3=2',ha='center',fontsize=6.5)
ax.text(3.65,.6,'Ring: old team; fill: repaired team\nBlue: team A; ochre: qualified team B',fontsize=7,
        bbox={'facecolor':'white','edgecolor':'none','pad':0})
ax.text(5.0,-1.55,'All costs and packages are illustrative',fontsize=6.5,color='#555555')
ax.set_xlim(-.5,9.2);ax.set_ylim(-1.7,1.2);ax.axis('off')
fig.savefig(out/'images/design_case_v4.png');plt.close(fig)
(out/'followup_asset_provenance.json').write_text(json.dumps({'inputs':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
    'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'case_scope':'fully synthetic example, not semi-synthetic or measured industry data'},indent=2))
print('Built 10-row follow-up table and illustrative figure.')
