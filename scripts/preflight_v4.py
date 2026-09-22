#!/usr/bin/env python3
"""Archival static diagnostic for a materialized companion tree.  NOT a release gate.

The release gates are scripts/verify_companion.py (exact distribution
integrity) and scripts/replay_companion.py (the arithmetic replay).  This
tool was used while deriving the V4 companion to find, without SageMath or
PARI, the places where an archived script or record pins a manifest by
digest or row count.  It scans EVERY archived script and JSON record --
including runs outside the declared execution set -- so its findings are
classified rather than all counted as failures:

  failure     a pinned digest or row count that disagrees with the tree, or a
              listed file that is missing or has the wrong digest, for a
              reference this tool can resolve;
  historical  a manifest row with an absolute path outside the tree's known
              relocation root (kept from earlier workspaces; the executed
              verifiers relocate or ignore them; not checked here);
  unresolved  a manifest or listed file this tool's resolver cannot locate
              (reported, not counted as a failure: the resolver reproduces only
              the common relocation rules, not every historical one).

Comment lines (starting with '#') and blank lines in manifests are not
entries, as in the executed verifiers.  The exit status is 1 only for
failures, 2 if nothing at all was checked (an empty or wrong tree), else 0.

Usage: preflight_v4.py LOGICAL_ROOT [--declared EXEC_ANALYSIS_JSON] [--verbose]
  --declared restricts the scanned scripts to the declared execution set of
             the given analysis file (key 'executed'); by default every script
             in the tree is scanned.
"""
import ast, hashlib, json, os, re, sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = sys.argv[1:]
if not args: print(__doc__); sys.exit(2)
L = Path(args[0]).resolve()
VERBOSE = '--verbose' in opts
declared = None
if '--declared' in opts:
    declared = set(json.load(open(opts[opts.index('--declared') + 1]))['executed'])
EX = sorted(str(p.relative_to(L)) for p in L.rglob('*') if p.suffix in ('.py', '.gp', '.sage', '.sh'))
if declared is not None: EX = [s for s in EX if s in declared]
HEX = re.compile(r'[0-9a-f]{64}')

# relocation root of the sector runner, if the tree carries it
ORIGINAL_ROOT = None
pp = L / 'verification/sectors/v3/scripts/portable_python.py'
if pp.is_file():
    m = re.search(r'^ORIGINAL_ROOT\s*=\s*"([^"]+)"', pp.read_text(errors='ignore'), re.M)
    if m: ORIGINAL_ROOT = m.group(1)

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()

def rd(p, limit=3_000_000):
    try:
        if p.stat().st_size > limit: return ''
        return p.read_text(errors='ignore')
    except Exception: return ''

BASES = ('evidence/v3/repository', 'evidence/v3', 'evidence/p5/repository', 'evidence/rank/repository', '')
def relocate(v):
    """Map an absolute historical path into the tree when it lies under the known relocation root."""
    if ORIGINAL_ROOT and v.startswith(ORIGINAL_ROOT + '/'):
        return v[len(ORIGINAL_ROOT) + 1:], True
    return v, False

def resolve(v, ctx):
    v, relocated = relocate(v)
    if os.path.isabs(v): return None
    for base in BASES:
        c = L / base / v
        if c.is_file(): return c
    for up in (ctx.parent, ctx.parent.parent, ctx.parent.parent.parent):
        c = up / v
        if c.is_file(): return c
    return None

failures, historical, unresolved = [], [], []
checked = 0
def manifest_rows(mf):
    return [ln for ln in rd(mf).splitlines() if ln.strip() and not ln.lstrip().startswith('#')]

def check_manifest(ref, exp_sha, exp_rows, origin):
    global checked
    checked += 1
    mf = resolve(ref, origin_path.get(origin, L))
    if mf is None:
        if os.path.isabs(relocate(ref)[0]): historical.append((origin, f'manifest at historical absolute path: {ref}'))
        else: unresolved.append((origin, f'manifest not located by this resolver: {ref}'))
        return
    if exp_sha and sha(mf) != exp_sha: failures.append((origin, f'manifest digest mismatch {mf.name}')); return
    rows = manifest_rows(mf)
    if exp_rows is not None and len(rows) != exp_rows:
        failures.append((origin, f'row count {len(rows)} != pinned {exp_rows} in {mf.name}'))
    for ln in rows:
        parts = re.split(r'\s+\*?', ln.strip(), maxsplit=1)
        if len(parts) != 2 or not HEX.fullmatch(parts[0]):
            failures.append((origin, f'bad manifest line in {mf.name}')); continue
        digest, rel = parts
        rel, relocated = relocate(rel)
        if os.path.isabs(rel): historical.append((origin, f'row at historical absolute path: {rel} (in {mf.name})')); continue
        tgt = None
        for base in (mf.parents[1], L / 'evidence/v3/repository', L / 'evidence/v3', L / 'evidence/p5/repository', L / 'evidence/rank/repository', mf.parent):
            c = base / rel
            if c.is_file(): tgt = c; break
        if tgt is None:
            unresolved.append((origin, f'listed file not located: {rel} (in {mf.name})')); continue
        if sha(tgt) != digest: failures.append((origin, f'listed file digest mismatch: {rel} (in {mf.name})'))

origin_path = {}
# 1. JSON records: any object that names a manifest together with a digest (and optionally a row count)
for dp, dn, fn in os.walk(L):
    for f in fn:
        if not f.endswith('.json') or f in ('RELEASE_MANIFEST.json', 'TESTED_RELEASE_MANIFEST.json', 'PROOF_INPUTS_SHA256.json',
                                             'ARTIFACT_SELECTION.json', 'REQUIRED_PRIOR_EVIDENCE.json',
                                             'BASE_EVIDENCE_MANIFEST_INDEX_V1.json', 'DEPENDENCY_CLOSURE_INDEX_V3.json',
                                             'DEPENDENCY_CLOSURE_INDEX_V2.json'): continue
        jp = Path(dp) / f
        try: d = json.loads(rd(jp) or 'null')
        except Exception: continue
        origin_path[f] = jp
        def walk(node):
            if isinstance(node, dict):
                for mk in ('manifest', 'path', 'file'):
                    if isinstance(node.get(mk), str) and 'SHA256SUMS' in node[mk] and node[mk].endswith('.txt') and node.get('sha256'):
                        check_manifest(node[mk], node.get('sha256'), node.get('rows'), f); break
                for k, v in node.items():
                    if isinstance(v, str) and 'SHA256SUMS' in v and v.endswith('.txt') and k != 'manifest' and node.get(k + '_sha256'):
                        origin_path[f + ':' + k] = jp
                        check_manifest(v, node.get(k + '_sha256'), node.get(k + '_rows'), f + ':' + k)
                for v in node.values(): walk(v)
            elif isinstance(node, list):
                for v in node: walk(v)
        walk(d)

# 2. scripts: pinned digests and row counts in every form found in the archive
for s in EX:
    p = L / s
    if not p.exists(): continue
    origin_path[s] = p; origin_path[p.name] = p
    t = rd(p)
    for m in re.finditer(r'"([^"]*SHA256SUMS[^"]*\.txt)"\s*:\s*"([0-9a-f]{64})"', t):
        check_manifest(m.group(1), m.group(2), None, s)
    if not s.endswith('.py'): continue
    try: tree = ast.parse(t)
    except SyntaxError: continue
    keymap = {}; digmap = {}
    for d in ast.walk(tree):
        if isinstance(d, ast.Dict):
            for k, v in zip(d.keys, d.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    parts = [c.value for c in ast.walk(v) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
                    if any('SHA256SUMS' in x for x in parts):
                        joined = ''.join(parts); keymap[k.value] = joined if 'SHA256SUMS' in joined else next(x for x in parts if 'SHA256SUMS' in x)
                    elif len(parts) == 1 and HEX.fullmatch(parts[0]): digmap[k.value] = parts[0]
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
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Call) and len(node.comparators) == 1 \
                and isinstance(node.comparators[0], ast.Constant) and isinstance(node.comparators[0].value, int):
            cand = [c for c in (manifest_of(x) for x in node.left.args) if c]
            if len(cand) == 1 and (cand[0], node.lineno) not in seen:
                seen.add((cand[0], node.lineno)); check_manifest(cand[0], None, node.comparators[0].value, s)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List, ast.Call)):
            elts = list(node.elts) if not isinstance(node, ast.Call) else list(node.args)
            cand = [c for c in (manifest_of(e) for e in elts) if c]
            strs = [e.value for e in elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            ints = [e.value for e in elts if isinstance(e, ast.Constant) and isinstance(e.value, int) and not isinstance(e.value, bool)]
            digs = [x for x in strs if HEX.fullmatch(x)]
            key_digs = [digmap[x] for x in strs if x in digmap]
            if len(cand) == 1 and (len(ints) == 1 or len(digs) == 1) and (cand[0], node.lineno) not in seen:
                seen.add((cand[0], node.lineno))
                check_manifest(cand[0], (digs or key_digs or [None])[0], ints[0] if len(ints) == 1 else None, s)
    # accumulated form: var += replay_manifest(dep["manifest"], ...) over a ledger, then assert var == N
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
                else: total += len(manifest_rows(mf))
            checked += 1
            if missing: unresolved.append((s, 'accumulated form: a dependency manifest was not located'))
            elif total != int(m.group(1)): failures.append((s, f'accumulated rows {total} != pinned {m.group(1)}'))

print(f'pinned manifest references checked: {checked}; failures: {len(failures)}; '
      f'historical absolute paths: {len(historical)}; unresolved by this resolver: {len(unresolved)}')
for f in failures: print('  FAIL', f)
if VERBOSE:
    for h in historical: print('  HIST', h)
    for u in unresolved: print('  UNRES', u)
print('This is an archival diagnostic, not a release gate; see the module docstring.')
sys.exit(2 if checked == 0 else (1 if failures else 0))
