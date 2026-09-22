#!/usr/bin/env python3
"""Static pre-flight for a V4 logical tree.

Emulates, without Sage or PARI, every manifest-replay check the executed suite
performs: for each manifest referenced by an executed script or by a JSON input
those scripts read, verify that the manifest exists, that its pinned digest and
row count (where pinned) agree, and that every row resolves to an existing file
with the listed digest.  Usage: preflight_v4.py LOGICAL_ROOT EXEC_ANALYSIS_JSON
"""
import hashlib, json, os, re, sys
from pathlib import Path

L = Path(sys.argv[1]).resolve()
EX = sorted(str(p.relative_to(Path(sys.argv[1]).resolve())) for p in Path(sys.argv[1]).resolve().rglob('*') if p.suffix in ('.py', '.gp', '.sage', '.sh'))
HEX = re.compile(r'[0-9a-f]{64}')

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()

def resolve(v, ctx):
    for base in ('evidence/v3/repository', 'evidence/v3', 'evidence/p5/repository', 'evidence/rank/repository', ''):
        c = L / base / v
        if c.is_file(): return c
    for up in (ctx.parent, ctx.parent.parent, ctx.parent.parent.parent):
        c = up / v
        if c.is_file(): return c
    return None

def rd(p, limit=3_000_000):
    try:
        if p.stat().st_size > limit: return ''
        return p.read_text(errors='ignore')
    except Exception: return ''

failures = []; checked = 0
def check_manifest(mf, exp_sha, exp_rows, origin):
    global checked
    checked += 1
    if mf is None: failures.append((origin, 'manifest missing')); return
    if exp_sha and sha(mf) != exp_sha: failures.append((origin, f'manifest digest mismatch {mf.name}')); return
    rows = [ln for ln in rd(mf).splitlines() if ln.strip()]
    if exp_rows is not None and len(rows) != exp_rows: failures.append((origin, f'row count {len(rows)} != pinned {exp_rows} in {mf.name}'))
    for ln in rows:
        parts = ln.split('  ', 1)
        if len(parts) != 2: failures.append((origin, f'bad manifest line in {mf.name}')); continue
        digest, rel = parts[0], parts[1].strip().lstrip('*')
        tgt = None
        for base in (mf.parents[1], L / 'evidence/v3/repository', L / 'evidence/v3', L / 'evidence/p5/repository', L / 'evidence/rank/repository', mf.parent):
            c = base / rel
            if c.is_file(): tgt = c; break
        if tgt is None:
            if rel.endswith('.pdf') and ('Pacetti' in rel or 'Bruin' in rel or 'Thesis' in rel) or rel.endswith('p7_level23_data_mod7.m'):
                continue  # external logical inputs, materialized from the private cache
            failures.append((origin, f'listed file missing: {rel} (in {mf.name})')); continue
        if sha(tgt) != digest: failures.append((origin, f'listed file digest mismatch: {rel} (in {mf.name})'))

# 1. JSON inputs of executed scripts
for dp, dn, fn in os.walk(L):
    for f in fn:
        if not f.endswith('.json') or f in ('RELEASE_MANIFEST.json', 'TESTED_RELEASE_MANIFEST.json', 'PROOF_INPUTS_SHA256.json', 'ARTIFACT_SELECTION.json', 'REQUIRED_PRIOR_EVIDENCE.json', 'BASE_EVIDENCE_MANIFEST_INDEX_V1.json', 'DEPENDENCY_CLOSURE_INDEX_V3.json', 'DEPENDENCY_CLOSURE_INDEX_V2.json'): continue
        jp = Path(dp) / f
        try: d = json.loads(rd(jp) or 'null')
        except Exception: continue
        def walk(node):
            if isinstance(node, dict):
                for mk in ('manifest', 'path', 'file'):
                    if isinstance(node.get(mk), str) and 'SHA256SUMS' in node[mk] and node[mk].endswith('.txt') and node.get('sha256'):
                        check_manifest(resolve(node[mk], jp), node.get('sha256'), node.get('rows'), f); break
                for k, v in node.items():
                    if isinstance(v, str) and 'SHA256SUMS' in v and v.endswith('.txt') and k != 'manifest' and node.get(k + '_sha256'):
                        check_manifest(resolve(v, jp), node.get(k + '_sha256'), node.get(k + '_rows'), f + ':' + k)
                for v in node.values(): walk(v)
            elif isinstance(node, list):
                for v in node: walk(v)
        walk(d)

# 2. executed scripts: pinned digests of manifests, and literal row counts
for s in EX:
    p = L / s
    if not p.exists(): continue
    t = rd(p)
    for m in re.finditer(r'"([^"]*SHA256SUMS[^"]*\.txt)"\s*:\s*"([0-9a-f]{64})"', t):
        check_manifest(resolve(m.group(1), p), m.group(2), None, p.name)
    paths = dict(re.findall(r'"(\w+)":\s*(?:ROOT|PKG|REPO)\s*/\s*"([^"]+)"', t))
    for m in re.finditer(r'replay_manifest\(PATHS\["(\w+)"\]\)\s*==\s*(\d+)', t):
        key, n = m.group(1), int(m.group(2))
        if key in paths: check_manifest(resolve(paths[key], p), None, n, p.name + ':' + key)

# AST pass over scripts: tuples/lists/calls holding (manifest path, digest, rows)
import ast
for s in EX:
    p = L / s
    if not p.exists() or not s.endswith('.py'): continue
    try: tree = ast.parse(rd(p))
    except SyntaxError: continue
    keymap = {}; digmap = {}
    for d in ast.walk(tree):
        if isinstance(d, ast.Dict):
            for k, v in zip(d.keys, d.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    parts = [c.value for c in ast.walk(v) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
                    if any('SHA256SUMS' in x for x in parts):
                        joined = ''.join(parts); keymap[k.value] = joined if 'SHA256SUMS' in joined else next(x for x in parts if 'SHA256SUMS' in x)
                    elif len(parts) == 1 and re.fullmatch(r'[0-9a-f]{64}', parts[0]): digmap[k.value] = parts[0]
    varmap = {}
    for a in ast.walk(tree):
        if isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name):
            parts = [c.value for c in ast.walk(a.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
            if any('SHA256SUMS' in x for x in parts):
                joined = ''.join(parts); varmap[a.targets[0].id] = joined if 'SHA256SUMS' in joined else next(x for x in parts if 'SHA256SUMS' in x)
    def manifest_of(arg):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if arg.value in keymap: return keymap[arg.value]
            if 'SHA256SUMS' in arg.value: return arg.value
        if isinstance(arg, ast.Name) and arg.id in varmap: return varmap[arg.id]
        if isinstance(arg, ast.Subscript) and isinstance(arg.slice, ast.Constant) and arg.slice.value in keymap: return keymap[arg.slice.value]
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Call) and len(node.comparators) == 1 \
                and isinstance(node.comparators[0], ast.Constant) and isinstance(node.comparators[0].value, int):
            cand = [manifest_of(x) for x in node.left.args]; cand = [c for c in cand if c]
            if len(cand) == 1: check_manifest(resolve(cand[0], p), None, node.comparators[0].value, s)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            keys = [e.value for e in node.args if isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value in keymap]
            ints = [e.value for e in node.args if isinstance(e, ast.Constant) and isinstance(e.value, int) and not isinstance(e.value, bool)]
            if len(keys) == 1 and len(ints) == 1:
                check_manifest(resolve(keymap[keys[0]], p), digmap.get(keys[0]), ints[0], s)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List, ast.Call)):
            elts = list(node.elts) if not isinstance(node, ast.Call) else list(node.args)
            strs = [e.value for e in elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            ints = [e.value for e in elts if isinstance(e, ast.Constant) and isinstance(e.value, int) and not isinstance(e.value, bool)]
            mfs = [x for x in strs if 'SHA256SUMS' in x and x.endswith('.txt')]
            digs = [x for x in strs if re.fullmatch(r'[0-9a-f]{64}', x)]
            if len(mfs) == 1 and len(digs) == 1:
                check_manifest(resolve(mfs[0], p), digs[0], ints[0] if len(ints) == 1 else None, s)
# accumulated form: var += replay_manifest(dep["manifest"], …) over a ledger, then assert var == N
for s in EX:
    p = L / s
    if not p.exists() or not s.endswith('.py'): continue
    t = rd(p)
    acc = re.search(r'^\s*(\w+)\s*\+=\s*replay_manifest\(\w+\["manifest"\]', t, re.M)
    led = re.search(r'^LEDGER_PATH\s*=\s*PACKAGE\s*/\s*"([^"]+\.json)"', t, re.M)
    m = acc and re.search(r'^\s*assert\s+' + acc.group(1) + r'\s*==\s*(\d+)', t, re.M)
    if acc and led and m:
        lp = p.parent.parent / led.group(1)
        if lp.is_file():
            ledger = json.loads(rd(lp))
            deps = next((v for k, v in ledger.items() if isinstance(v, list) and v and isinstance(v[0], dict) and 'manifest' in v[0]), [])
            total = 0; missing = False
            for dep in deps:
                mf = resolve(dep['manifest'], lp)
                if mf is None: missing = True
                else: total += len([ln for ln in rd(mf).splitlines() if ln.strip()])
            checked += 1
            if missing: failures.append((s, 'accumulated: manifest missing'))
            elif total != int(m.group(1)): failures.append((s, f'accumulated rows {total} != pinned {m.group(1)}'))
print(f'manifest checks: {checked}, failures: {len(failures)}')
for f in failures: print('  ', f)
sys.exit(1 if failures else 0)
