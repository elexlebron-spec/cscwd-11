"""Artifact/data checks, not a substitute for mathematical review."""
from pathlib import Path
import hashlib
import json
import re
from pypdf import PdfReader

root=Path(__file__).resolve().parents[1]
paper=root/'paper/manuscript'
source=(paper/'main.tex').read_text()
pdf=paper/'BARR_CSCWD2027_draft.pdf'
reader=PdfReader(pdf)
assert 1<=len(reader.pages)<=6
assert all(float(p.mediabox.width)==612 and float(p.mediabox.height)==792 for p in reader.pages)
keys=set(re.findall(r'\\bibitem\{([^}]+)\}',source))
cited={k for group in re.findall(r'\\cite\{([^}]+)\}',source) for k in group.split(',')}
assert cited==keys and len(keys)==15
assert len(re.findall(r'\\begin\{figure\*?\}',source))==2
assert r'\label{fig:ownership}' in source and r'\label{fig:public}' in source
assert r'\includegraphics[width=\textwidth]{images/public_graphs_v5.png}' in source
assert hashlib.sha256((paper/'images/public_graphs_v5.png').read_bytes()).hexdigest()=='afbf685f66ee8e98b3df738c2b3bfed5830b61dd3a9dfadbbfc637e9198e7cd5'
labels=re.findall(r'\\label\{([^}]+)\}',source)
assert len(labels)==len(set(labels))
assert set(re.findall(r'\\ref\{([^}]+)\}',source))<=set(labels)
for name, token in [('main_rows','MAIN'),('ablation_rows','ABLATION'),('route_rows','ROUTE'),('repeat_rows','REPEAT')]:
    rows=(paper/(name+'.tex')).read_text().strip()
    expected='% BEGIN GENERATED '+token+' ROWS\n'+rows+'\n% END GENERATED '+token+' ROWS'
    assert expected in source
logpath=paper/'build/main.log'
if logpath.exists():
    log=logpath.read_text()
    assert not re.search(r'Overfull|Citation .*undefined|Reference .*undefined|! LaTeX Error',log)
font_names=set()
for page in reader.pages:
    for ref in page['/Resources']['/Font'].values():
        font=ref.get_object();font_names.add(str(font.get('/BaseFont')))
        if '/DescendantFonts' in font:font=font['/DescendantFonts'][0].get_object()
        desc=font.get('/FontDescriptor')
        assert desc is not None
        desc=desc.get_object()
        assert any(k in desc for k in ['/FontFile','/FontFile2','/FontFile3'])
main=json.loads((root/'results/gate_combined_v2/summary.json').read_text())
abl=json.loads((root/'results/ablation_weighted_v3/summary.json').read_text())
assert main['all_exact_pairs'] and abl['all_three_way_exact']
scale=json.loads((root/'results/scale_holdout_v4/summary.json').read_text())
stress=json.loads((root/'results/core_holdout_v4/summary.json').read_text())
assert scale['solutions_validated'] and stress['solutions_validated']
public=json.loads((root/'results/public_comparison_v5/summary.json').read_text())
routes=json.loads((root/'results/route_comparison_v5/summary.json').read_text())
assert public['solutions_validated'] and routes['solutions_validated']
repeats=json.loads((root/'results/core_repeats_v6_completed/summary.json').read_text())
assert repeats['no_pause_during_logged_queries'] and repeats['clock_audit_passed'] and repeats['solutions_validated'] and repeats['calls']==400 and repeats['cases']==20
ownership=json.loads((root/'results/ownership_case_v8_completed/summary.json').read_text())
diagnostic=json.loads((root/'results/ownership_case_v8_diagnostic/summary.json').read_text())
assert ownership['all_enumerated_values_match'] and ownership['cases']==64 and ownership['strict_budget_binding']==40
assert ownership['shared_shortcuts']==8 and diagnostic['shared_shortcuts']==64
assert ownership['capacity_guard_passes']==ownership['capacity_guard_rejections']==64
worked=json.loads((root/'results/ownership_case_v8_completed/worked_case.json').read_text())
assert worked['optimum']==7 and worked['new_energy_x0']==15 and worked['region']==[0]
review=json.loads((paper/'visual_review.json').read_text())
pdf_hash=hashlib.sha256(pdf.read_bytes()).hexdigest()
assert review['pdf_sha256']==pdf_hash
assert review['reviewed_pages']==list(range(1,len(reader.pages)+1))
report={'pages':len(reader.pages),'page_size':'US Letter','bibliography_items':len(keys),
        'body_figures':2,'original_cad_matrix_in_body':True,'original_cad_matrix_bytes_preserved':True,
        'citations_and_references_resolve':True,'generated_table_rows_match':True,
        'no_overfull_or_undefined_reference_warnings':True if logpath.exists() else None,
        'compile_log_available':logpath.exists(),'all_pdf_fonts_embedded':True,
        'font_names':sorted(font_names),'main_cases':main['cases'],'main_calls':main['solver_runs'],
        'ablation_cases':abl['cases'],'ablation_calls':abl['solver_runs'],
        'scale_cases':scale['cases'],'scale_calls':scale['calls'],
        'hard_core_cases':stress['cases'],'hard_core_calls':stress['calls'],
        'public_new_cases':public['cases'],'public_calls':public['calls'],
        'route_reused_cases':routes['cases'],'route_calls':routes['calls'],
        'repeat_fixed_cases':repeats['cases'],'repeat_calls':repeats['calls'],
        'ownership_illustration_cases':ownership['cases'],'ownership_diagnostic_cases':diagnostic['cases'],
        'ownership_case_is_runtime_benchmark':False,'capacity_guard_example_verified':True,
        'artifact_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [paper/'main.tex',pdf]},
        'visual_review_matches_pdf':review['pdf_sha256']==pdf_hash,
        'limits':'Does not establish originality, model realism or acceptance.'}
(paper/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
