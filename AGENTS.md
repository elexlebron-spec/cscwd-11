# Repository instructions

Preserve frozen experimental inputs, source snapshots, labels and bounds. Do not overwrite raw outcomes or select favorable seeds. Keep the theorem assumptions and additive certificate intact. User-provided author metadata is in AUTHOR_INFO.json. Test with `python -m unittest discover -s tests -v`. The paper is an unsubmitted draft; do not claim novelty or acceptance has been established.

Current certificate: max(new unconstrained value, restricted lower bound minus epsilon), with no epsilon deduction when the retained region is the whole graph. Global optimality requires closed valid final bounds. Capacity guard failure terminates; an unknown solve with no incumbent returns the old feasible plan. Preserve original records and put re-certification in derived files.
