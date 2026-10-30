"""Static sourced portfolio illustration; layout is manual, not an observation."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
portfolio = json.loads((root / 'results/ownership_case_v8_completed/portfolio.json').read_text())
pos = [(0.11, .72), (.43, .95), (.73, .71), (.10, .15), (.39, .04), (.87, .17), (.43, .40), (.91, .99)]
names = ['combobox', 'positioning', 'shared-contexts', 'table', 'tags', 'tree', 'utilities', 'storybook']
fig, ax = plt.subplots(figsize=(3.45, 1.95))
for i, j, _ in portfolio['edges']:
    ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]], color='.65', linewidth=.7, zorder=0)
for i, (x, y) in enumerate(pos):
    ax.scatter(x, y, s=92, facecolor='white', edgecolor='black', linewidth=.8, zorder=2)
    if i == 0:
        ax.scatter(x, y, s=160, facecolor='none', edgecolor='black', linewidth=.8, zorder=2)
    ax.text(x, y, str(i), ha='center', va='center', fontsize=6.5, zorder=3)
    ax.annotate(names[i], (x, y), xytext=(0, 7 if i not in (4, 6) else -12), textcoords='offset points',
                ha='center', va='bottom', fontsize=6.5)
ax.text(.02, 1.19, 'Public dependency structure; 0 is anchor and K for B=1', fontsize=6.4)
ax.set(xlim=(-.10, 1.13), ylim=(-.17, 1.29))
ax.axis('off')
fig.subplots_adjust(left=.01, right=.99, top=.98, bottom=.01)
out = root / 'paper/manuscript/images/ownership_case_v8.pdf'
fig.savefig(out, metadata={'CreationDate': None, 'ModDate': None})
fig.savefig(out.with_suffix('.png'), dpi=240)
print(out)
