"""Build S1--S4 from frozen/derived records; no benchmark is rerun."""
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
    data = json.loads((ROOT / 'results/certificate_analysis_v11/summary.json').read_text())
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
    story.append(Image(str(ROOT / 'paper/manuscript/images/region_speed_v11.png'), width=522, height=163.125))
    p('<b>Figure S1.</b> All 480 inputs have equal certified optima (2,880 calls). Filled points use a retained model. Hollow shortcuts occupy a separate shaded band, outside the 0-100% region axis: no region/model was built. The line is speed 1. This cohort has no censored points; larger/core incomplete calls stay in separate main-text tables.', small)
    p('N denotes queries not resolved by the shared cut shortcut: 318/480, versus 314 with a strictly larger budgeted optimum. A rejected cut can have a feasible tie. All 162 shortcut cases remain in all-case summaries. Size, topology, costs and budget co-vary, so geometry-speed associations are descriptive.', body)
    names = {'grid': 'Grid', 'modular': 'Modular', 'smallworld': 'Small-world'}
    rows = [[f"{names[g['topology']]}, {g['n']}", f"{g['cp_required']}/{g['cases']}",
             f"{100*g['median_retained_node_fraction']:.1f}",
             f"{100*g['median_retained_edge_fraction']:.1f}",
             f"{100*g['median_constructed_bool_fraction']:.1f}",
             f"{g['median_full_ms']:.1f}/{g['median_barr_ms']:.1f}",
             f"{g['median_paired_speed']:.2f}/{g['median_speed_all']:.2f}"] for g in groups]
    table(['Family, n', 'N/all', 'Nodes %', 'Edges %', 'Bools %', 'F/R ms', 'Speed N/all'], rows,
          [102, 44, 54, 54, 54, 110, 104])
    p('<b>Table S1(a).</b> N-query median model fractions before presolve: n+m Booleans become |K|+|E[K]|, with crossing factors absorbed into unaries. Time medians are marginal; speed is the median of paired per-case ratios, after three timings per route/case.', small)
    rows = [[f"{names[g['topology']]}, {g['n']}", str(g['cases']),
             f"{g['sum_case_median_full_seconds']:.3f}", f"{g['sum_case_median_barr_seconds']:.3f}",
             f"{g['ratio_sums_case_medians']:.3f}", f"{g['median_speed_all']:.3f}"] for g in groups]
    table(['Family, n', 'All cases', 'Sum F (s)', 'Sum R (s)', 'Ratio of sums', 'Median ratio'], rows,
          [116, 55, 88, 88, 90, 85])
    p('<b>Table S1(b).</b> Ratio of sums of per-case median times: sum_i median(T_F,i) / sum_i median(T_R,i). Every family/size uses all 80 fixed cases. This aggregates saved timings; it is neither a new sequential workload run nor a speed generalization to a deployment mix. The statistic weights costly cases more than the median paired ratio. These two summaries answer different questions.', small)
    story.append(PageBreak())
    p('S2. Paired end-to-end time accounting', title)
    p('Calls are paired by input and repeat, averaged within input, then across the stratum. Equal repeat counts give the same mean over calls. All-case versions and paired components are in timing_components_calls.csv, timing_components_cases.csv and timing_components_groups.csv.', body)
    timing = [g for g in data['timing_groups'] if g['scope'] == 'not_shortcut']
    rows = []
    for g in timing:
        for method, prefix in [('F', 'full'), ('R', 'barr')]:
            rows.append([f"{names[g['topology']]}, {g['n']}", method] +
                        [f"{g['mean_' + prefix + '_' + k + '_ms']:.3f}" for k in
                         ['common','preprocess','build','solver','other','total']])
    table(['Family, n', 'F/R', 'Cut ms', 'Prep ms', 'Build ms', 'Solve ms', 'Other ms', 'Total ms'], rows,
          [108, 32, 56, 56, 65, 65, 66, 74])
    p('<b>Table S2(a).</b> F/R = FullCP/BARRCP. Arithmetic mean milliseconds on all N queries, including both routes. Shared cut, preprocessing, build and solver fields come from the same call. Other = total minus these four fields: solver setup, reconstruction, bookkeeping and clock residuals. These means add to the mean total (rounding aside). No component median is summed.', small)
    rows = []
    for g in timing:
        rows.append([f"{names[g['topology']]}, {g['n']}", str(g['cases']),
                     f"{g['mean_saving_build_ms']:.3f}", f"{g['mean_saving_solver_ms']:.3f}",
                     f"{-g['mean_saving_preprocess_ms']:.3f}",
                     f"{g['mean_saving_common_ms']+g['mean_saving_other_ms']:.3f}",
                     f"{g['mean_saving_total_ms']:.3f}"])
    table(['Family, n', 'N cases', 'Build saved', 'Solve saved', 'Extra prep', 'Cut+other saved', 'Total saved'], rows,
          [108, 44, 72, 72, 72, 82, 72])
    p('<b>Table S2(b).</b> Mean paired differences (ms), formed within each input/repeat before aggregation. Saved = F-R; extra prep = R-F. Build saved + solve saved - extra prep + cut/other saved = total saved. Negative savings remain visible. The prep field combines old certification, support extraction, region construction and boundary absorption; the saved logs do not identify their separate costs. Extra prep is relative to FullCP prep.', small)
    p('For modular n=512, the non-shortcut mean build/solve savings are 14.575/55.404 ms, against 1.744 ms extra preprocessing. Small-world n=512 saves 0.434/2.465 ms in build/solve but adds 5.463 ms prep, leaving a mean total penalty of 1.563 ms. Such stage-level means do not replace paired median speeds or imply a single cause for search variation.', body)
    story.append(PageBreak())
    p('S3. Old-gap loss and certificate interpretation', title)
    story.append(Image(str(ROOT / 'paper/manuscript/images/epsilon_tightness_v11.png'), width=522, height=184.875))
    p('<b>Figure S2.</b> Actual optimum loss Delta = OPT_K - OPT_B versus positive old gap epsilon. Full and restricted reference optima are proved; marker area counts duplicate pairs. Actual loss is distinct from the returned interval gap U-L and the solver\'s own global-optimality status.', small)
    rows = []
    for name, key in [('Old gap epsilon', 'epsilon'), ('Absolute loss Delta', 'absolute_delta'),
                      ('Delta/epsilon: all 32', 'ratio_all'), ('Delta/epsilon: positive 10', 'ratio_positive')]:
        q = eps[key]; rows.append([name] + [f"{q[k]:.3f}".rstrip('0').rstrip('.') if q[k] else '0'
                                             for k in ['min', 'q1', 'median', 'q3', 'max']])
    table(['Quantity', 'Minimum', 'Q1', 'Median', 'Q3', 'Maximum'], rows, [190, 70, 65, 65, 65, 67])
    p('<b>Table S3.</b> Linear-interpolated quartiles. Ten losses are positive (26,26,29,29,31,31,31,34,64,67); three attain epsilon. Tightness ratios do not establish acceptable absolute cost.', small)
    rows = [[g['stratum'], str(g['cases']), str(g['zero_loss']), f"{g['zero_loss_percent']:.2f}%", str(g['proper_regions'])]
            for g in data['epsilon_strata']]
    table(['Stratum', 'Cases', 'Zero loss', 'Zero loss %', 'Proper regions'], rows, [162, 75, 90, 100, 95])
    p('<b>Table S4.</b> Constructed-case descriptions, not an operational population estimate. Of 26 genuinely reduced regions, 16 preserve the global value (61.54%). Six full regions cannot lose value through restriction. At B=8, 6/16 have zero loss; at B=16, 16/16 do, including ten proper regions. Actual zero loss uses the full reference; it is not BARR self-certification.', small)
    p('<b>Derived certificate audit.</b> Recomputing new unconstrained minima and merging saved bounds strengthens 18/32 epsilon-case lower bounds; six full-region intervals newly close. The remaining 26 do not close, including 16 with verified zero actual loss. Across 6,208 saved CP calls in nine final stages, no other lower bound changes. Original outcomes, statuses and timings are untouched; derived_certificates.csv records both old and strengthened intervals. No CP timing is rerun.', body)
    p('At epsilon=0, at least one suitable optimum is retained, not every tied optimum. At epsilon>0 the union pays epsilon once. Each later update needs a new old-objective certificate: a previous budgeted optimum may fail old unconstrained optimality. Source hashes, 32-row losses and region sizes are in results/certificate_analysis_v11.', small)
    story.append(PageBreak())
    p('S4. Protocol detail and stage history', title)
    p('<b>Main generator.</b> The 480-case grid crosses n=128/512, modular/grid/small-world structure, edge coupling 2/12, one/four anchors, B=8/16 and ten seeds. Modular graphs join 4x4 blocks by unit bridges; small-world graphs add 2n pairs to a grid and merge duplicates. Nonbridge weights are uniform [c,2c]; unary base/preference costs are uniform [1,4], with alternating preferred modules/rows. Old plans are exact cuts. Old-label anchor costs increase by [8c,10c], and the alternative decreases by at most a quarter of that increase. Handoff costs are one. No case is rejected.', body)
    p('<b>Freeze and timing.</b> After 96 calibration cases, seeds 100--102 were frozen; seeds 103--109 extended the same factors. The whole study was not prospectively registered. Three alternating timings per method/case are reduced to a case median before ratios. Bootstrap intervals resample 2,000 (n, family, seed) clusters, retaining reused factors/repeats. Single-worker FullCP/BARRCP share the formulation, hint and new-cut shortcut. Every query includes cuts, preprocessing, model/solver construction and solving. BARR pays its old cut; shared imports/warm-up and old-plan generation are outside timing. Soft targets are not process deadlines.', body)
    p('<b>Large-scale factors.</b> n=1024/2048, three families, one/four anchors, B=16/64, coupling 12, perturbation scale 64, heterogeneous handoffs and five seeds were frozen after 24 scale and eight cost-ratio exploratory cases. Targets are three seconds (scale/public), five (cores); method order rotates.', body)
    p('<b>Hard-core construction.</b> A q=64/128 cycle plus random matching has unit internal edges; anchor-star edges have weight 3. A dominated tail reaches n=1024/2048. Core unary pairs are (0,-1), tail (0,10); the anchor changes from (0,4q+1) to (0,-4q). Unit handoffs and B=1+q/2 give a uniquely optimal old all-zero plan; a new optimum changes the anchor and q/2 core vertices. Thus tail growth does not increase intrinsic core difficulty.', body)
    p('<b>LRRepair detail.</b> Exact rational cuts use integer scaling. Doubling brackets a feasible cut and at most 24 bisections refine it. Keep the best feasible cut and restore the closest infeasible cut by reverting the vertex of minimum energy increase per freed effort. Feasible single-flip descent starts from that restored result, the old plan and the feasible cut. At most 65% of the target goes to the dual phase, the remainder to recovery. Integer-ceiling bounds are valid, but a finite multiplier search need not reach the optimal dual; recovery has no approximation guarantee.', body)
    p('<b>Separate stages, not pooled samples.</b> Three-route single timings reuse 120 large, 20 core and 72 public inputs (636 calls); they are not pooled with main/weighted triple timings. At n=2048, modular non-shortcut speed was 7.67 (v4), then 7.30 (v5); 64-core speed was 2.86, then 3.24. At each 128-core size BARR certified 1/5, then 4/5. Separate stages identify neither cause nor stable success probability.', body)
    p('<b>Final repeated cores.</b> All 20 inputs have ten calls per CP route (400), five-second soft targets, one worker and fixed seeds, with round-wise shuffling and alternating methods. Two segments (261 + 139) follow a tool interruption; saved calls were not rerun. All pass 0.1-second continuous-clock/pause checks. No concurrent benchmark/build ran; background load/power were uncontrolled. Closure uses each call interval, not another call that proved the optimum.', body)
    p('<b>Preserved diagnostics.</b> Earlier suspend-affected attempts remain separate: 400 calls with 42 clock mismatches, an interrupted 129-call attempt, and a continuous-clock batch with 13 pause flags. They are not pooled with the final 400. The source timing correction and interruption records remain in TIMING_FIX_V6.md and the original result directories. Main-text Table V reports all final incomplete calls and censored query totals, not uncensored time-to-optimum.', body)
    p('<b>Reproduce.</b> Run scripts/analyze_certificates_v11.py with a new --out; build_analysis_assets_v11.py and build_analysis_supplement_v11.py render the analyses. Sources/hashes: <link href="https://github.com/elexlebron-spec/cscwd-11" color="#244F72">github.com/elexlebron-spec/cscwd-11</link>. Use project matplotlib and optional reportlab. No timed CP rerun is required.', small)
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
    (OUT / 'analysis_provenance_v11.json').write_text(json.dumps({
        'date': '2026-11-05', 'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'analysis_summary_sha256': hashlib.sha256((ROOT / 'results/certificate_analysis_v11/summary.json').read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
        'no_timed_cp_rerun': True}, indent=2) + '\n')
    print(pdf)


if __name__ == '__main__':
    main()
