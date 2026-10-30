"""Build paper tables/plots strictly from validated saved summaries."""
import hashlib
import json
import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
out = root / 'paper/manuscript'
(out / 'images').mkdir(exist_ok=True)
sources = ['results/gate_combined_v2/summary.json', 'results/ablation_weighted_v3/summary.json',
           'results/ablation_weighted_v3/case_summary.json', 'results/epsilon_v2/case_summary.json']
main, abl, cases, eps = [json.loads((root / p).read_text()) for p in sources]
assert main['all_exact_pairs'] and abl['all_three_way_exact']
labels = {'grid': 'Grid', 'modular': 'Modular', 'smallworld': 'Small-world'}
lines = []
for g in main['groups']:
    lines.append(f"{labels[g['topology']]} & {g['n']} & {g['nontrivial_equal_optimum_cases']}/{g['all_cases']} & {g['median_ratio_nontrivial']:.2f} & {g['median_ratio_all_cases']:.2f} \\\\")
(out / 'main_rows.tex').write_text('\n'.join(lines)+'\n')
lines = []
for g in abl['groups']:
    e = g['estimates']['hop_over_barr']
    lines.append(f"{labels[g['topology']]} & {g['active_exact']}/{g['cases']} & {100*g['median_hop_region_ratio']:.1f} & {100*g['median_weighted_region_ratio']:.1f} & {e['active_median']:.2f} & {e['all_median']:.2f} \\\\")
(out / 'ablation_rows.tex').write_text('\n'.join(lines)+'\n')
manuscript = out / 'main.tex'
if manuscript.exists():
    text = manuscript.read_text()
    for name, token in [('main_rows', 'MAIN'), ('ablation_rows', 'ABLATION')]:
        rows = (out / (name + '.tex')).read_text().strip()
        pattern = r'% BEGIN GENERATED ' + token + r' ROWS\n.*?\n% END GENERATED ' + token + r' ROWS'
        replacement = '% BEGIN GENERATED ' + token + ' ROWS\n' + rows + '\n% END GENERATED ' + token + ' ROWS'
        text = re.sub(pattern, lambda _: replacement, text, flags=re.S)
    manuscript.write_text(text)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.labelsize': 8,
                     'axes.titlesize': 8, 'legend.fontsize': 7, 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.dpi': 140, 'savefig.dpi': 320})
fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.15), layout='constrained')
topos = ['modular', 'grid', 'smallworld']
x = np.arange(3)
for k, (field, label, color) in enumerate([('hop_region_ratio','HopCP','#aaaaaa'),('weighted_region_ratio','BARRCP','#28638c')]):
    values = [np.median([c[field] for c in cases if c['topology']==t and c['nontrivial']]) for t in topos]
    axes[0].bar(x+(k-.5)*.33, np.array(values)*100, width=.32, label=label, color=color)
axes[0].set_xticks(x, [labels[t] for t in topos])
axes[0].set_ylabel('Median retained vertices (%)')
axes[0].set_ylim(0, 110)
axes[0].legend(frameon=False, loc='upper left')
axes[0].set_title('(a) Region size, CP-required cases')
values=[]; lows=[]; highs=[]
for t in topos:
    g=next(g for g in abl['groups'] if g['topology']==t)
    e=g['estimates']['hop_over_barr']
    values.append(e['active_median'])
    lows.append(e['active_cluster_bootstrap_95'][0])
    highs.append(e['active_cluster_bootstrap_95'][1])
axes[1].errorbar(x, values, yerr=[np.array(values)-lows, np.array(highs)-values],
                 fmt='o', color='#28638c', capsize=4, lw=1.2)
axes[1].axhline(1, color='#888888', lw=.8, ls='--')
axes[1].set_xticks(x, [labels[t] for t in topos])
axes[1].set_ylabel('HopCP time / BARRCP time')
axes[1].set_ylim(.8, 3)
axes[1].set_title('(b) Paired speed, seed-cluster 95% CI')
fig.savefig(out/'images/weighted_ablation.png')
plt.close(fig)
fig, ax=plt.subplots(figsize=(3.45, 2.05), layout='constrained')
for t,marker,color in [('modular','o','#28638c'),('grid','s','#b86b25')]:
    selected=[c for c in eps if c['topology']==t]
    ax.scatter([c['old_epsilon'] for c in selected], [c['actual_loss'] for c in selected],
               s=25, marker=marker, edgecolor=color, facecolor='none', alpha=.8, label=labels[t])
ax.plot([0,110],[0,110], color='#777777', ls='--', lw=.8, label='Certificate limit')
ax.set_xlim(0,110); ax.set_ylim(-4,110)
ax.set_xlabel('Old-plan gap $\\epsilon$')
ax.set_ylabel('Actual objective loss')
ax.legend(frameon=False, loc='upper left')
fig.savefig(out/'images/epsilon_certificate.png')
plt.close(fig)
(out/'asset_provenance.json').write_text(json.dumps({
    'inputs': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources},
    'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'note': 'Tables/plots derive from saved validated results. Active stratum excludes only the shared proven-optimal shortcut; all-case timing estimates reported separately.'},indent=2))
print('Generated tables, two plots and source hashes.')
