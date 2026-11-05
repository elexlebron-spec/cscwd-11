# Authored English manuscript

The current paper lists **Zhiran Wang (王治然)**, **Ocean University of China (中国海洋大学)**, and **2174560006@qq.com**. The author supplied this information; the current author list contains one person, identified as the independent first author in the repository metadata.

`main.tex` is the manuscript source; `BARR_CSCWD2027_draft.pdf` is the compiled six-page draft including references and illustrations. A convenience copy is at `../BARR_CSCWD2027_ZhiranWang.pdf`.

Compile with an IEEEtran-capable LaTeX setup, for example `tectonic main.tex`. The 15 references are embedded; `references.bib` is an editing resource and no separate BibTeX pass is required. Figure assets and generated table rows are included.

From the repository root, `python scripts/check_paper.py` validates page count, citations, table rows, embedded fonts and saved data. `verification.json` and `visual_review.json` record the checks and the exact reviewed PDF hash. The original union-reversion/region/boundary proof is preserved. The v8 revision adds a sourced alternative-owner case and a separate static-capacity redundancy check, not an active-capacity solver. Historical source snapshots and outcomes are retained separately; the current root README and AUTHOR_INFO.json govern author information.

The paper is an unsubmitted research draft. Successful compilation and finite tests do not establish originality or venue acceptance. Model limits and reproduction details appear in the paper, THEORY.md and EXPERIMENT_PROTOCOL.md. This publicly identified repository is not an anonymous review link.

## Historical v9: both figures in the six-page body

The original v5 three-panel CAD matrix is restored at full text width as Figure 2 (page 5), alongside the ownership case as Figure 1. The PNG bytes are unchanged. Introductory and explanatory prose is shorter; all displayed equations, the central proof, capacity subsection, tables IV/V including captions and values, all references and the numeric tokens of the original source are preserved. Fonts, margins and the IEEEtran layout settings are unchanged.

An optional one-page companion is at `../supplementary/BARR_CAD_Supplement.pdf`; it includes the same figure plus structure counts for all six public graphs. It does not replace the body figure. Build it with `python -m pip install -r paper/supplementary/requirements-build.txt` and `python scripts/build_cad_supplement_v9.py` from the repository root. The builder reads frozen inputs and never runs solvers.

## Historical v10: a single certified-reduction chain

The six-page body keeps five tables, two figures and 15 references, with Algorithm 1, explicit global team labels and a weighted-path example. Table II adds constructed model fractions and absolute times; the CAD matrix retains all original pixels below a new result annotation strip. The original proof/display equations and all ablation/route/repeat numeric rows are preserved. Process history and detailed generators move to Supplement S3.

The current analysis companion is `../supplementary/BARR_Analysis_Supplement.pdf`: S1 geometry versus paired query time, S2 epsilon tightness, S3 protocols/history. These sections refer to this companion, not the older one-page CAD document. The new CSVs and source hashes are in results/certificate_analysis_v10. No timed CP query or repair solver changed. See REVISION_V10.md for prioritization and reproducibility commands.


## Current v11: termination and merged certificates

Algorithm 1 returns CAPACITY_NOT_CERTIFIED on a failed capacity guard (CapacityNotCertified exception in Python), or the reconstructed old plan if the retained solver has no incumbent. The returned objective equals the plan energy. Corollary 2 combines the new cut lower bound with the transferred restricted bound; a full retained region pays no epsilon. The original three proofs and all generated numeric table rows are preserved, with one merged-bound corollary added. The complexity sum is written inline. Fonts, margins, both figures and the six-page limit are unchanged.

The current four-page analysis companion contains S1 geometry and cumulative timing, S2 paired stage accounting, S3 epsilon strata/derived certificates and S4 protocol history. New CSVs are in results/certificate_analysis_v11. Frozen records/source snapshots remain unchanged; new certificates are derived separately. The earlier S1--S3 description above applies only to v10. See REVISION_V11.md.
