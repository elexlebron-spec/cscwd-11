"""Add the prespecified repeated-core evidence, leaving the proof unchanged."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];paper=ROOT/'paper/manuscript'
s=json.loads((ROOT/'results/core_repeats_v6_completed/summary.json').read_text());assert s['calls']==400 and s['solutions_validated'] and s['clock_audit_passed'] and s['no_pause_during_logged_queries']
groups={(g['n'],g['core_size'],g['method']):g for g in s['groups']}
def t(g):
 v=g['query_seconds'];return f"{v['median']:.3f} [{v['q1']:.3f},{v['q3']:.3f}]"
rows=[]
for q in [64,128]:
 for n in [1024,2048]:
  a,b=groups[n,q,'FullCP'],groups[n,q,'BARRCP']
  rr=lambda g:f"{g['per_instance_closed_min']}--{g['per_instance_closed_max']}"
  rows.append(f"{q} & {n} & {a['closed']}/{b['closed']} & {rr(a)}/{rr(b)} & {t(a)} / {t(b)} & {a['median_within_case_relative_iqr_percent']:.1f}/{b['median_within_case_relative_iqr_percent']:.1f} & {a['gap_max']}/{b['gap_max']} \\\\")
body='\n'.join(rows);(paper/'repeat_rows.tex').write_text(body+'\n')
text=(paper/'main.tex').read_text()
assert 'tab:repeat' not in text,'Apply this manuscript edit once'
old='Anonymous code, source attribution, inputs, and all saved outcomes are packaged for supplementary submission; the public mirror is \\url{https://barr-review-materials-v5.sagelemur512.chatgpt.site}.'
assert old in text
text=text.replace(old,'Anonymous supplementary materials contain code, source attribution, fixed inputs, all saved outcomes, and file hashes.')
old='The reduced CP route certifies 4/5 per size in the fresh run, compared with 1/5 previously, illustrating wall-clock variability; a reduced core can still remain unresolved.'
assert old in text
text=text.replace(old,'The reduced CP route certifies 4/5 per size in this single run, versus 1/5 previously. These separate observations motivate the repeated-query check below; they do not establish a stable success probability or its cause.')
insert=r'''
\subsection{Repeatability of Difficult Core Queries}
We repeat all 20 saved core inputs ten times per CP route (400 calls), with the same five-second target, formulation, search settings and one worker. The frozen protocol fixes the original solver seed, shuffles case order by round, and alternates method order. Preliminary attempts exposed suspend-related timing discrepancies; all diagnostic calls are archived separately. We use macOS continuous monotonic time for accounting/deadlines, keep the laptop awake, and abort on a clock mismatch or pause delta above 0.1 s. The run is completed in two execution segments after a tool interruption; saved queries are not rerun. All 400 logged calls pass these checks. We launched no concurrent benchmark or document build.

\begin{table*}[t]
\caption{Repeated core queries: five fixed instances per row, ten repeats per method. F/R = FullCP/BARRCP. Closed counts are out of 50 calls; ranges give per-instance counts out of ten. Time is median [Q1,Q3] of all query totals, including incomplete calls, not uncensored time-to-optimum. Rel.~IQR is the median across instances of each instance's (Q3--Q1)/median time (\%). These are descriptive repeats, not 50 independent instances.}\label{tab:repeat}
\centering\footnotesize\setlength{\tabcolsep}{2pt}
\begin{tabular}{@{}rrrrlrr@{}}
\toprule $q$ & $n$ & Closed F/R & Per-case F/R & Query time F / R (s) & Rel.~IQR F/R & Max gap F/R\\\midrule
% BEGIN GENERATED REPEAT ROWS
ROWS_PLACEHOLDER
% END GENERATED REPEAT ROWS
\bottomrule\end{tabular}
\end{table*}

Table~\ref{tab:repeat} retains every incomplete query. The archive supplies each instance's ten outcomes, residual gaps, and timing components. Small time dispersion at the cap reflects censoring, not reliable time-to-optimum. Background load and power mode are not controlled. Fixed-seed repeats on one laptop characterize these two execution segments only; they do not establish cross-session or hardware reliability. Bound closure is counted from each call's own returned interval, even when another call establishes the optimum. We report no speed ratio for unresolved cores and no independent-trial confidence interval.
'''.replace('ROWS_PLACEHOLDER',body)
text=text.replace('\\section{Discussion and Limitations}',insert+'\n\\section{Discussion and Limitations}')
text=text.replace('New comparisons have single timings on one machine; wall-clock solved counts vary. We retain previous runs separately rather than selecting the better outcome.','The three-route comparison has single timings; the repeated-core stage tests repeat variability in two execution segments on the same machine. Neither stage establishes cross-machine stability. Previous runs are retained separately.')
(paper/'main.tex').write_text(text)
print(body)
