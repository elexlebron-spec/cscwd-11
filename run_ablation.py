"""Prospective three-way safe-region ablation. No sample filtering."""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import shutil
import sys
import ortools
from barr.core import Problem, anchored_region, hop_region
from barr.cpsat import solve_cpsat, solve_repair_cpsat
from barr.generate_v2 import Setting, generate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    raw = Path(args.config).read_bytes()
    cfg = json.loads(raw)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'inputs').mkdir()
    (out / 'config.json').write_bytes(raw)
    sources = [Path(__file__).resolve(), *sorted(Path('barr').glob('*.py'))]
    manifest = {}
    for path in sources:
        rel = Path(path.name) if path.name == 'run_ablation.py' else Path('barr') / path.name
        dest = out / 'source' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        manifest[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = {'utc_started': datetime.now(timezone.utc).isoformat(), 'config': cfg,
            'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
            'ortools': ortools.__version__, 'config_sha256': hashlib.sha256(raw).hexdigest(),
            'source_sha256': manifest,
            'timing': 'single-thread; common fastpath; old certificate charged to both regional methods; all query preprocessing and modeling included',
            'selection': 'full Cartesian grid, no filtering, new seeds 200-209; frozen before any ablation outcomes'}
    (out / 'metadata.json').write_text(json.dumps(meta, indent=2))
    solve_cpsat(Problem(((0, 1),), (), (0,), (1,)), 0, 1)
    names = list(cfg['grid'])
    methods = ['FullCP', 'HopCP', 'BARRCP']
    writer = None
    count = 0
    with (out / 'solutions.jsonl').open('w') as jf, (out / 'runs.csv').open('w', newline='') as cf:
        for index, vals in enumerate(product(*(cfg['grid'][key] for key in names))):
            setting = Setting(**dict(zip(names, vals)))
            old, new, details = generate(setting)
            payload = {'old': asdict(old), 'new': asdict(new)}
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            case_id = f'case_{index:04d}'
            (out / 'inputs' / f'{case_id}.json').write_text(json.dumps(payload))
            weighted_n = len(anchored_region(new, details['anchors'], setting.budget))
            hop_n = len(hop_region(new, details['anchors'], setting.budget))
            assert weighted_n <= hop_n
            for repeat in range(cfg['repeats']):
                shift = (index + repeat) % 3
                order = methods[shift:] + methods[:shift]
                # Each method occupies each timing position exactly once per case.
                for method in order:
                    result = solve_repair_cpsat(old, new, setting.budget, cfg['seconds_per_query'],
                                               regional=method != 'FullCP',
                                               common_fastpath=cfg['common_fastpath'], seed=setting.seed,
                                               region_mode='hop' if method == 'HopCP' else 'weighted')
                    record = {'case_id': case_id, **asdict(setting), 'repeat': repeat,
                              'method': method, 'input_sha256': digest,
                              'weighted_region_n': weighted_n, 'hop_region_n': hop_n,
                              **result, 'old_epsilon': details['old_epsilon']}
                    assert new.energy(record['x']) == record['upper']
                    assert new.resource(record['x']) <= setting.budget
                    jf.write(json.dumps(record) + '\n')
                    if writer is None:
                        writer = csv.DictWriter(cf, fieldnames=[k for k in record if k != 'x'], extrasaction='ignore')
                        writer.writeheader()
                    writer.writerow(record)
                    jf.flush()
                    cf.flush()
            count += 1
            if count % 10 == 0:
                print(f'Completed {count} cases; last {setting.topology}', flush=True)
    meta.update(completed_cases=count, utc_completed=datetime.now(timezone.utc).isoformat())
    (out / 'completion.json').write_text(json.dumps(meta, indent=2))
    print(f'Completed {count} cases at {out}', flush=True)


if __name__ == '__main__':
    main()
