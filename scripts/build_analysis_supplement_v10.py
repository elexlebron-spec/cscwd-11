"""Build S1--S3 from frozen/derived records; no benchmark is rerun."""
from pathlib import Path
from xml.sax.saxutils import escape
import hashlib, json
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/supplementary'
BLUE = colors.HexColor('#244F72')


def main():
    data = json.loads((ROOT / 'results/certificate_analysis_v10/summary.json').read_text())
    groups = data['groups']; eps = data['epsilon']
    fontdir = Path(reportlab.__file__).resolve().parent / 'fonts'
    for name, filename in [('Vera', 'Vera.ttf'), ('VeraBold', 'VeraBd.ttf'), ('VeraItalic', 'VeraIt.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fontdir / filename)))
    pdfmetrics.registerFontFamily('Vera', normal='Vera', bold='VeraBold', italic='VeraItalic', boldItalic='VeraBold')
    body = ParagraphStyle('Body', fontName='Vera', fontSize=9.1, leading=12.4, spaceAfter=7)
    title = ParagraphStyle('Title', parent=body, fontName='VeraBold', fontSize=16, leading=21, textColor=BLUE, spaceAfter=9)
    small = ParagraphStyle('Small', parent=body, fontSize=8, leading=10.7)
    head = ParagraphStyle('Head', parent=small, fontName='VeraBold', alignment=TA_CENTER, textColor=colors.white)
    story = []
    def p(text, style=body):
        story.append(Paragraph(text, style))
    def table(headers, rows, widths):
        tab = Table([[Paragraph(escape(x), head) for x in headers]] + rows,
                    colWidths=widths, repeatRows=1, hAlign='LEFT')
        tab.setStyle(TableStyle([
            ('FONTNAME', (0, 1), (-1, -1), 'Vera'), ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), BLUE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F5F9')]),
            ('LINEBELOW', (0, -1), (-1, -1), .6, BLUE),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5)
        ]))
        story.extend([tab, Spacer(1, 9)])
    p('S1. When does region reduction pay?', title)
    p('Zhiran Wang | Ocean University of China | 2174560006@qq.com', small)
    story.append(Image(str(ROOT / 'paper/manuscript/images/region_speed_v10.png'), width=522, height=163.125))
    p('<b>Figure S1.</b> Retained vertices versus end-to-end paired speed by graph family. All 480 inputs have equal certified optima (2,880 calls; three timings per route/input). Filled points need CP; hollow shortcuts are shown at 100%, with no region/model built. The reference line is speed 1; no points in this cohort are censored.', small)
    p('<b>Three questions.</b> 318/480 queries require CP; 314 strictly increase the objective over the unconstrained minimum. A returned cut can be over budget even when another tied optimum is feasible. Model reduction and useful speed are conditional on entering CP. All 162 shortcuts stay in the all-case ratios.', body)
    names = {'grid': 'Grid', 'modular': 'Modular', 'smallworld': 'Small-world'}
    rows = [[f"{names[g['topology']]}, {g['n']}", f"{g['cp_required']}/{g['cases']}",
             f"{100*g['median_retained_node_fraction']:.1f}",
             f"{100*g['median_retained_edge_fraction']:.1f}",
             f"{100*g['median_constructed_bool_fraction']:.1f}",
             f"{g['median_full_ms']:.1f}/{g['median_barr_ms']:.1f}",
             f"{g['median_paired_speed']:.2f}/{g['median_speed_all']:.2f}"] for g in groups]
    table(['Family, n', 'CP/all', 'Nodes %', 'Edges %', 'Bools %', 'F/R ms', 'Speed CP/all'], rows,
          [102, 44, 54, 54, 54, 110, 104])
    p('<b>Table S1.</b> CP-required medians: n+m Booleans before presolve, reduced to |K|+|E[K]|; crossing factors enter unaries. Time medians are marginal; speed is the median of within-case ratios. Per-case/all-case absolute times and edge counts are in geometry_cases.csv and geometry_groups.csv.', small)
    rows = [[f"{names[g['topology']]}, {g['n']}",
             *[f"{g['median_'+field+'_ms']:.2f}" for field in ['common', 'preprocess', 'build', 'solver']],
             '--' if g['spearman_node_speed_cp'] is None else f"{g['spearman_node_speed_cp']:.3f}",
             '--' if g['spearman_bool_speed_cp'] is None else f"{g['spearman_bool_speed_cp']:.3f}"] for g in groups]
    table(['Family, n', 'Cut ms', 'Prep ms', 'Build ms', 'Solve ms', 'Rank r: nodes', 'Rank r: Bools'], rows,
          [102, 58, 62, 62, 62, 88, 88])
    p('<b>Table S2.</b> BARR components and descriptive within-family/size rank correlations. Component medians do not add; constant fractions give undefined correlations. Seed/factor dependence and changing costs, topology, budget and search preclude causal/significance claims. Censored scale/core calls remain in separate-stage manuscript Tables IV/V; no unequal-quality speed or time-to-target is inferred.', small)
    story.append(PageBreak())
    p('S2. Old-gap certificate tightness', title)
    story.append(Image(str(ROOT / 'paper/manuscript/images/epsilon_tightness_v10.png'), width=522, height=184.875))
    p('<b>Figure S2.</b> Actual restricted-optimum loss Delta versus the old-objective gap epsilon, and the ratio distribution. Marker area represents duplicate pairs. Each full bound is closed, and each restricted lower bound (before subtracting epsilon) equals its upper bound. Thus Delta is an actual optimum difference, not a returned open bound gap. All 32 gaps are positive.', small)
    p('Of 32 inexact plans, 22 have Delta=0 (68.75%), ten have positive loss and three satisfy Delta=epsilon. Positive absolute losses are 26, 26, 29, 29, 31, 31, 31, 34, 64 and 67. The old gap includes unary and pairwise effects of the one/three non-anchor flips. It is checked against an exact old cut. No speed comparison treats different-quality full/restricted answers as equivalent.', body)
    rows = []
    for name, key in [('Old gap epsilon', 'epsilon'), ('Absolute loss Delta', 'absolute_delta'),
                      ('Delta/epsilon: all 32', 'ratio_all'), ('Delta/epsilon: positive 10', 'ratio_positive')]:
        q = eps[key];rows.append([name] + [f"{q[k]:.3f}".rstrip('0').rstrip('.') if q[k] != 0 else '0'
                                             for k in ['min', 'q1', 'median', 'q3', 'max']])
    table(['Quantity', 'Minimum', 'Q1', 'Median', 'Q3', 'Maximum'], rows, [190, 70, 65, 65, 65, 67])
    p('<b>Table S3.</b> Linear-interpolated quartiles of the 32 saved instance/budget combinations. These constructed cases are not an observed planner population. Delta/epsilon measures how tight the certificate is; an acceptable ratio can still conceal an unacceptable absolute loss. Absolute Delta must be judged in application cost units.', small)
    p('<b>Checks and files.</b> The read-only analyzer verifies saved labels, handoff feasibility, full/restricted closed bounds, old certificates and region exterior labels. The complete 32-row table is epsilon_cases.csv. Source hashes and the analyzer snapshot are in results/certificate_analysis_v10. The original epsilon_v2 records remain unchanged.', body)
    p('<b>Weighted path example used in the method.</b> For the path a[3]-b[2]-c[1], with a as the only anchor and B=5, the node-weighted distances are 3, 5 and 6. The retained set is {a,b}. Both the anchor and target consume budget. This is an explanatory path, not a modification of the Fluent UI case or an additional benchmark.', body)
    p('<b>Scope of the certificate.</b> The old gap is paid once for the union of unanchored components. At epsilon=0 an appropriate optimal value is preserved; the theorem does not fix the exterior of every tied optimum. At positive epsilon the loss is at most epsilon. Every later update requires a new old-objective certificate: the previous budgeted optimum may be suboptimal for the next old unconstrained problem.', body)
    story.append(PageBreak())
    p('S3. Protocol detail and stage history', title)
    p('<b>Main generator.</b> The 480-case grid crosses n=128/512, modular/grid/small-world structure, edge coupling 2/12, one/four anchors, B=8/16 and ten seeds. Modular graphs join 4x4 blocks by unit bridges; small-world graphs add 2n pairs to a grid and merge duplicates. Nonbridge weights are uniform [c,2c]; unary base/preference costs are uniform [1,4], with alternating preferred modules/rows. Old plans are exact cuts. Old-label anchor costs increase by [8c,10c], and the alternative decreases by at most a quarter of that increase. Handoff costs are one. No case is rejected.', body)
    p('<b>Freeze and timing.</b> After 96 calibration cases, seeds 100--102 were frozen; seeds 103--109 extended the same factors. The whole study was not prospectively registered. Three alternating timings per method/case are reduced to a case median before ratios. Bootstrap intervals resample 2,000 (n, family, seed) clusters, retaining reused factors/repeats. Single-worker FullCP/BARRCP share the formulation, hint and new-cut shortcut. Every query includes cuts, preprocessing, model/solver construction and solving. BARR pays its old cut; shared imports/warm-up and old-plan generation are outside timing. Soft targets are not process deadlines.', body)
    p('<b>Hard-core construction.</b> A q=64/128 cycle plus random matching has unit internal edges; anchor-star edges have weight 3. A dominated tail reaches n=1024/2048. Core unary pairs are (0,-1), tail (0,10); the anchor changes from (0,4q+1) to (0,-4q). Unit handoffs and B=1+q/2 give a uniquely optimal old all-zero plan; a new optimum changes the anchor and q/2 core vertices. Thus tail growth does not increase intrinsic core difficulty.', body)
    p('<b>LRRepair detail.</b> Exact rational cuts use integer scaling. Doubling brackets a feasible cut and at most 24 bisections refine it. Keep the best feasible cut and restore the closest infeasible cut by reverting the vertex of minimum energy increase per freed effort. Feasible single-flip descent starts from that restored result, the old plan and the feasible cut. At most 65% of the target goes to the dual phase, the remainder to recovery. Integer-ceiling bounds are valid, but a finite multiplier search need not reach the optimal dual, and recovery has no approximation guarantee.', body)
    p('<b>Separate stages, not pooled samples.</b> Three-route single timings reuse 120 large, 20 core and 72 public inputs (636 calls); they are not pooled with main/weighted triple timings. At n=2048, modular CP-subset speed was 7.67 (v4), then 7.30 (v5); 64-core speed was 2.86, then 3.24. At each 128-core size BARR certified 1/5, then 4/5. Separate stages identify neither cause nor stable success probability.', body)
    p('<b>Final repeated cores.</b> All 20 inputs have ten calls per CP route (400), five-second soft targets, one worker and fixed seeds, with round-wise shuffling and alternating methods. Two segments (261 + 139) follow a tool interruption; saved calls were not rerun. All pass 0.1-second continuous-clock/pause checks. No concurrent benchmark/build ran; background load/power were uncontrolled. Closure uses each call interval, not another call that proved the optimum.', body)
    p('<b>Preserved diagnostics.</b> Earlier suspend-affected attempts remain separate: 400 calls with 42 clock mismatches, an interrupted 129-call attempt, and a continuous-clock batch with 13 pause flags. They are not pooled with the final 400. The source timing correction and interruption records remain in TIMING_FIX_V6.md and the original result directories. Main-text Table V reports all final incomplete calls and censored query totals, not uncensored time-to-optimum.', body)
    p('<b>Bounds versus loss.</b> A returned U-L is a certificate gap, not loss to an unknown true optimum. Actual loss is stated only with a proved reference. Final objectives and total times alone do not reveal time to equal target quality; solver trajectories would be needed. No such target-time result is claimed here.', body)
    p('<b>Application roles.</b> Labels denote the same two teams at every vertex. Fluent UI supplies candidate-contact declarations; Bath supplies co-edits, neither measured costs, capacity or skills. Optional capacity redundancy uses operator-supplied static loads. Effective-anchor refinement and sequential experiments are deferred; repair solvers and historical inputs are unchanged.', body)
    p('<b>Reproduce the analyses.</b> Run scripts/analyze_certificates_v10.py with a new --out; build_analysis_assets_v10.py and build_analysis_supplement_v10.py render saved analyses. Sources, inputs, hashes and outcomes: <link href="https://github.com/elexlebron-spec/cscwd-11" color="#244F72">github.com/elexlebron-spec/cscwd-11</link>. Plotting uses the project matplotlib runtime; the document builder uses the optional reportlab dependency. No new timed CP query is required.', small)
    pdf = OUT / 'BARR_Analysis_Supplement.pdf'
    doc = SimpleDocTemplate(str(pdf), pagesize=letter, leftMargin=45, rightMargin=45, topMargin=56, bottomMargin=42,
                            title='BARR: Geometry, Certificate Tightness and Protocol', author='Zhiran Wang')
    def decoration(canvas, document):
        canvas.saveState();canvas.setFont('VeraBold', 8);canvas.setFillColor(BLUE)
        canvas.drawString(45, 761, 'BARR / SUPPLEMENTARY ANALYSES')
        canvas.setStrokeColor(colors.HexColor('#CAD9E4'));canvas.line(45, 751, 567, 751)
        canvas.setFont('Vera', 8);canvas.drawString(45, 25, '5 November 2026 | Frozen records; no timed CP rerun')
        canvas.drawRightString(567, 25, f'S{document.page}');canvas.restoreState()
    doc.build(story, onFirstPage=decoration, onLaterPages=decoration)
    (OUT / 'analysis_provenance_v10.json').write_text(json.dumps({
        'date': '2026-11-05', 'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'analysis_summary_sha256': hashlib.sha256((ROOT / 'results/certificate_analysis_v10/summary.json').read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
        'no_timed_cp_rerun': True}, indent=2) + '\n')
    print(pdf)


if __name__ == '__main__':
    main()
