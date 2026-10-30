"""Join completed records from two execution segments; never rewrite raw files."""
import csv,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
a=ROOT/'results/core_repeats_v6_confirmed_awake';b=ROOT/'results/core_repeats_v6_resume';out=ROOT/'results/core_repeats_v6_completed'
assert (b/'completion.json').exists()
rows=[];seen=set()
for folder,expected in [(a,261),(b,139)]:
 rr=[json.loads(s) for s in (folder/'solutions.jsonl').read_text().splitlines()];assert len(rr)==expected
 for r in rr:
  key=(r['case_id'],r['repeat'],r['method']);assert key not in seen;seen.add(key)
  assert r['clock_consistent'] and r['suspend_clock_delta_seconds']<=.1
 rows.extend(rr)
assert len(rows)==400
out.mkdir(exist_ok=True);shutil.copytree(a/'inputs',out/'inputs',dirs_exist_ok=True);shutil.copytree(a/'source',out/'source',dirs_exist_ok=True);shutil.copy2(a/'config.json',out/'config.json')
meta=json.loads((a/'metadata.json').read_text());resume=json.loads((b/'completion.json').read_text())
for rel,digest in resume['source_sha256'].items():
 dest=out/'source'/rel
 if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
 else:dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(b/'source'/rel,dest)
 meta['source_sha256'][rel]=digest
meta.update(scope='fixed-input repeats on one laptop across two execution segments; completed records are not rerun; all logged queries pass clock and pause gates',segments=[{'folder':f.name,'calls':n,'raw_sha256':hashlib.sha256((f/'solutions.jsonl').read_bytes()).hexdigest()} for f,n in [(a,261),(b,139)]],merge_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),resumption_reason='first process ended with tool turn interruption; possibly one unlogged in-flight query was interrupted; only missing planned keys were rerun; pause between segments is outside query timing',completed_calls=400,completed_utc=resume['completed_utc'])
for name in ['metadata.json','completion.json']:(out/name).write_text(json.dumps(meta,indent=2)+'\n')
(out/'solutions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
with (out/'runs.csv').open('w',newline='') as cf:
 flat=[{k:v for k,v in r.items() if k!='x'} for r in rows];writer=csv.DictWriter(cf,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
print('Joined 261 + 139 = 400 logged calls; original raw segments preserved.')
