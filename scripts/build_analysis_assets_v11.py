"""Plot read-only v11 analyses and annotate the preserved CAD matrix asset."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results/certificate_analysis_v11'
OUT = ROOT / 'paper/manuscript/images'
COLORS = {'grid': '#2475AF', 'modular': '#C66A20', 'smallworld': '#548240'}


def save(fig, name):
    fig.savefig(OUT / (name + '.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(OUT / (name + '.png'), dpi=300)
    plt.close(fig)


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'pdf.fonttype': 42})
    with (DATA / 'geometry_cases.csv').open() as f:
        rows = list(csv.DictReader(f))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.25), sharey=True)
    for ax, family in zip(axes, COLORS):
        group = [r for r in rows if r['topology'] == family]
        for shortcut in [False, True]:
            for n in [128, 512]:
                selected = [r for r in group if (r['shortcut'] == 'True') == shortcut and int(r['n']) == n]
                ax.scatter([(118 if n == 128 else 123) if shortcut else 100*float(r['plot_node_fraction']) for r in selected],
                           [float(r['paired_speed']) for r in selected], s=12 if n == 128 else 26,
                           facecolors='none' if shortcut else COLORS[family],
                           edgecolors='#7A7A7A' if shortcut else COLORS[family],
                           linewidths=.6, alpha=.45 if shortcut else .6, zorder=2)
        ax.axvspan(108, 128, color='#EEEEEE', zorder=0)
        ax.axvline(108, color='#999999', linewidth=.6)
        ax.set_xticks([0, 50, 100, 120], ['0', '50', '100', 'Cut'])
        ax.axhline(1, color='black', linestyle='--', linewidth=.8)
        ax.set_title(family.replace('smallworld', 'Small-world').capitalize())
        ax.set(xlim=(-3, 128), yscale='log', xlabel='Retained vertices (%) | shortcut')
        ax.grid(alpha=.18)
    axes[0].set_ylabel('Paired FullCP / BARRCP time')
    legend = [Line2D([], [], marker='o', linestyle='none', color='black', markersize=4, label='n=128'),
              Line2D([], [], marker='o', linestyle='none', color='black', markersize=6, label='n=512'),
              Line2D([], [], marker='o', linestyle='none', markerfacecolor='none', color='#777777',
                     markersize=5, label='Shared shortcut: separate band; no region built')]
    fig.legend(handles=legend, loc='lower center', ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(.5, -.01))
    fig.text(.5, .975, '480 matched certified optima; 318 non-shortcut queries, 162 shortcuts; no censored points in this cohort',
             ha='center', va='top', fontsize=7)
    fig.subplots_adjust(left=.13, right=.99, top=.82, bottom=.28, wspace=.12)
    save(fig, 'region_speed_v11')
    with (DATA / 'epsilon_cases.csv').open() as f:
        eps = list(csv.DictReader(f))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.55))
    for family in ['grid', 'modular']:
        counts = Counter((int(r['epsilon']), int(r['delta'])) for r in eps if r['topology'] == family)
        axes[0].scatter([p[0] for p in counts], [p[1] for p in counts],
                        s=[24*counts[p] for p in counts], alpha=.65,
                        edgecolors='white', linewidths=.4, color=COLORS[family], label=family.capitalize())
    axes[0].plot([0, 110], [0, 110], color='black', linestyle='--', linewidth=.8, label='Delta = epsilon')
    axes[0].set(xlim=(18, 110), ylim=(-5, 112), xlabel='Old-objective certificate epsilon',
                ylabel='Actual loss Delta', title='Both full and restricted optima proved')
    axes[0].legend(fontsize=6.7, frameon=False, loc='upper left')
    values = [float(r['delta_over_epsilon']) for r in eps]
    counts, bins, _ = axes[1].hist(values, bins=np.linspace(0, 1, 11), color='#467DA1', edgecolor='white')
    axes[1].set(xlim=(-.02, 1.02), ylim=(0, 25), xlabel='Delta / epsilon', ylabel='Cases',
                title='Tightness, not operational acceptability')
    axes[1].text(.98, .95, '22/32 zero loss (68.75%)\n10 positive; 3 tight\nmax absolute loss = 67',
                 transform=axes[1].transAxes, va='top', ha='right', fontsize=7)
    for ax in axes: ax.grid(alpha=.18)
    fig.text(.03, .02, 'Scatter marker area counts duplicate (epsilon, Delta) pairs. All 32 certificates are positive.', fontsize=7)
    fig.subplots_adjust(left=.075, right=.99, top=.86, bottom=.25, wspace=.30)
    save(fig, 'epsilon_tightness_v11')
    original = ROOT / 'paper/manuscript/images/public_graphs_v5.png'
    image = Image.open(original).convert('RGB')
    assert hashlib.sha256(original.read_bytes()).hexdigest() == 'afbf685f66ee8e98b3df738c2b3bfed5830b61dd3a9dfadbbfc637e9198e7cd5'
    public = json.loads((ROOT / 'results/public_comparison_v5/summary.json').read_text())
    groups = {g['key'][0]: g for g in public['groups'] if g['key'][1] == 12}
    canvas = Image.new('RGB', (image.width, image.height + 56), 'white')
    canvas.paste(image, (0, 56)); draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / 'fonts/ttf/DejaVuSans-Bold.ttf'), 27)
    labels = {}
    for project, x in zip(['A', 'B', 'C'], [445, 1134, 1823]):
        g = groups[project]
        k = '--' if g['CP_region_fraction'] is None else f"{100*g['CP_region_fraction']:.1f}%"
        label = f"N {g['CP_required']}/{g['cases']}  |  median K {k}"
        draw.text((x, 11), label, font=font, fill='#244F72', anchor='mt')
        labels[project] = label
    assert canvas.crop((0, 56, image.width, image.height + 56)).tobytes() == image.tobytes()
    target = OUT / 'public_graphs_v11.png'; canvas.save(target)
    record = {'original_image_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
              'annotated_image_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'original_pixels_preserved_below_56px_annotation': True,
              'window_hours': 12, 'annotations': labels,
              'region_statistic': 'N denotes queries not resolved by the shared cut shortcut; median retained vertex percentage undefined if N=0',
              'analysis_summary_sha256': hashlib.sha256((DATA / 'summary.json').read_bytes()).hexdigest(),
              'plots': {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in
                        ['region_speed_v11.pdf', 'region_speed_v11.png', 'epsilon_tightness_v11.pdf', 'epsilon_tightness_v11.png']},
              'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT / 'paper/manuscript/analysis_assets_v11.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
