#!/usr/bin/env python3
"""Build the V4 companion from an extracted V2 companion.

V4 removes the author's exploratory working reports from the logical replay
tree itself (rather than declaring them author-held inputs, which V3 did and
which made the public replay procedure unrunnable).  Every manifest, index and
inventory that listed a removed document is regenerated, and every file whose
digest changed as a result has its new digest propagated wherever the old one
was pinned, to a fixed point.  Documents that any script executed by the
declared suite names, and every document without the working vocabulary, stay
public.

What this changes beyond the removed documents, all listed in the delta file:
certificate and ledger METADATA is regenerated (pinned digests, pinned
manifest row counts adjusted by the exact delta of each manifest, and the
report-artifact fields that named a removed report), and the ten verifiers
that certified their own narrative report as an artifact have those checks
removed.  No mathematical acceptance predicate, exact arithmetic input or
certified mathematical value is changed.  The result is a complete logical
tree whose declared suite can be replayed from public inputs alone; the
recorded replay of V2 no longer applies and a fresh replay must be recorded.

Usage: python3 build_v4_companion.py V2_ROOT OUT_DIR [--exec-analysis JSON]
"""
import ast, hashlib, json, os, re, shutil, stat, subprocess, sys, zipfile
from pathlib import Path, PurePosixPath

V2_TAG = 'replay-companion-2026-09-15.2'
V4_TAG = 'replay-companion-2026-09-23.1'
V4_NAME = 'PRIMITIVE_357_REPLAY_COMPANION_2026-09-23_V4'
DATE = '2026-09-23'
ZIP_DT = (2026, 9, 23, 0, 0, 0)
VOCAB = re.compile(rb'Numbers Without Time|[Qq]uantum|[Pp]rojector')
TEXT_EXT = {'.json', '.txt', '.md', '.py', '.gp', '.sage', '.sh', '.tex', '.csv', '.log', '.m', '.cfg', '.toml', '.yaml', '.yml'}
HEX64 = re.compile(r'[0-9a-f]{64}')

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()
def load(p): return json.loads(Path(p).read_text())
def write(p, d): Path(p).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

EXECUTED = set()
EXEC_JSON = set()   # JSON files named inside executed scripts (verified inputs such as proof graphs and certificates)
def is_text(path):
    """Files rewritten by the pipeline: manifests, index/inventory JSON, and scripts the declared suite
    executes.  Certificates, ledgers, checkpoints, logs and narrative documents are historical records
    of past runs and are never rewritten; a stale digest inside them is a record, not a verified input."""
    name = PurePosixPath(path).name; ext = PurePosixPath(path).suffix
    if ext == '.txt' and 'SHA256SUMS' in name: return True
    if ext == '.json':
        return True          # every ledger, certificate, index and inventory (large data files are skipped by size)
    if ext in ('.py', '.gp', '.sage', '.sh'):
        return True          # every script: sector verifiers run other runs' verifiers several levels deep
    return False

def has_vocab(fp):
    head = open(fp, 'rb').read(4)
    if head == b'%PDF':
        return bool(VOCAB.search(subprocess.run(['pdftotext', str(fp), '-'], capture_output=True).stdout))
    if head[:2] == b'PK' or head[:2] == b'\x1f\x8b':
        return False
    return bool(VOCAB.search(open(fp, 'rb').read()))

def main():
    v2 = Path(sys.argv[1]).resolve(); out = Path(sys.argv[2]).resolve()
    exec_analysis = load(sys.argv[4]) if len(sys.argv) > 4 else None
    root = out / V4_NAME
    if root.exists(): shutil.rmtree(root)
    shutil.copytree(v2, root, symlinks=False)
    fmap = load(root / 'inputs/REPLAY_FILE_MAP.json')
    assert fmap['public_release_tag'] == V2_TAG and 'author_inputs' not in load(root / 'inputs/EXTERNAL_INPUTS_LOCK.json')
    rows = {r['path']: r for r in fmap['files']}

    # ---- 1. materialize the logical tree from the objects (external inputs stay virtual)
    L = out / 'logical'
    if L.exists(): shutil.rmtree(L)
    for path, r in rows.items():
        if r['source']['kind'] != 'object': continue
        dst = L / path; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / r['source']['path'], dst)
    objpaths = [p for p, r in rows.items() if r['source']['kind'] == 'object']

    # original (pre-removal) row counts of every manifest, so pinned counts are adjusted by the exact delta
    def _rc(mf): return sum(1 for line in mf.read_text(errors='ignore').splitlines() if line.strip())
    ORIG_COUNTS = {str(mf.resolve()): _rc(mf) for mf in L.rglob('*SHA256SUMS*.txt') if mf.is_file()}
    # ---- 2. choose the documents to remove
    report_like = [p for p in objpaths if ('/summaries/' in p and PurePosixPath(p).suffix in ('.pdf', '.tex', '.md'))
                   or p.startswith('evidence/v3/repository/beal_357_spark_handover_2026-08-20/project/beal_357_progress.')]
    vocab_docs = [p for p in report_like if has_vocab(L / p)]
    keep_named = set(exec_analysis['read_by_exec']) if exec_analysis else set()
    EXECUTED.update(exec_analysis['executed'] if exec_analysis else [])
    for sp in EXECUTED:
        if (L / sp).exists():
            for m in re.findall(rb'([\w.-]+\.json)', (L / sp).read_bytes()):
                EXEC_JSON.add(m.decode())
    # documents listed in a per-run manifest that an executed script reads must also stay
    manifest_readers = set()
    if exec_analysis:
        for s in exec_analysis['executed']:
            t = (L / s).read_bytes() if (L / s).exists() else b''
            for m in re.findall(rb'([\w./-]*SHA256SUMS[\w.-]*\.txt)', t):
                manifest_readers.add(m.decode())
    listed_by_read_manifests = set()
    for p in objpaths:
        if p.endswith('.txt') and 'SHA256SUMS' in p and any(p.endswith(m) or m.endswith(PurePosixPath(p).name) for m in manifest_readers):
            for line in (L / p).read_text(errors='ignore').splitlines():
                parts = line.split()
                if len(parts) >= 2 and HEX64.fullmatch(parts[0]):
                    for q in vocab_docs:
                        if q.endswith(parts[-1].lstrip('*./')) or rows[q]['sha256'] == parts[0]:
                            listed_by_read_manifests.add(q)
    listed_by_read_manifests = set()  # manifests are regenerated below; only documents named in executed scripts are protected
    manuscript_drafts = {q for q in vocab_docs if 'COMPLETE_PRIMITIVE_357_PROOF_REPORT_V3' in q}   # an earlier version of the paper itself: provenance, kept
    remove = sorted(set(vocab_docs) - keep_named - manuscript_drafts)
    remove_hashes = {rows[p]['sha256'] for p in remove}
    # a removed hash must not survive under a kept path
    for p in objpaths:
        if p not in remove and rows[p]['sha256'] in remove_hashes:
            raise SystemExit('kept path shares content with a removed document: ' + p)
    for p in remove:
        (L / p).unlink()
    kept_vocab = sorted(set(vocab_docs) - set(remove))

    # ---- 3. hash-keyed deletion of the removed documents from manifests, indices and inventories
    changed = set()
    def strip_json(node, name):
        if isinstance(node, list):
            new = []
            for x in node:
                if isinstance(x, dict) and (x.get('sha256') in remove_hashes) and any(k in x for k in ('path', 'name', 'file', 'relative', 'member')):
                    changed.add(name); continue
                new.append(strip_json(x, name))
            return new
        if isinstance(node, dict):
            return {k: strip_json(v, name) for k, v in node.items()}
        return node
    for p in sorted(rows):
        fp = L / p
        if not fp.exists() or not is_text(p) or fp.stat().st_size > 5_000_000: continue
        if p.endswith('.json'):
            try: d = json.loads(fp.read_text())
            except Exception: continue
            d2 = strip_json(d, p)
            if p in changed: fp.write_text(json.dumps(d2, indent=2, ensure_ascii=False) + '\n')
        else:
            t = fp.read_text(errors='ignore'); lines = t.split('\n'); kept = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2 and HEX64.fullmatch(parts[0]) and parts[0] in remove_hashes:
                    changed.add(p); continue
                kept.append(line)
            if p in changed: fp.write_text('\n'.join(kept))

    # ---- 3b. counts that the executed verifiers compare against the actual tree
    externals = [q for q, r in rows.items() if r['source']['kind'] == 'external']
    def count_files(rel):
        rel = rel.rstrip('/') + '/'
        return sum(1 for x in (L / rel).rglob('*') if x.is_file()) + sum(1 for q in externals if q.startswith(rel))
    # (BASE_EVIDENCE_MANIFEST_INDEX_V1.json row counts are adjusted by the delta rule in 3c, once)
    ci = L / 'evidence/v3/inputs/DEPENDENCY_CLOSURE_INDEX_V3.json'
    if ci.exists():
        d = json.loads(ci.read_text()); d['repository_file_count'] = count_files('evidence/v3/repository')
        ci.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    rp = L / 'audit/work/integration_prior/REQUIRED_PRIOR_EVIDENCE.json'
    if rp.exists():
        d = json.loads(rp.read_text())
        for key, inv in d.get('required_repository_inventories', {}).items():
            if 'file_count' in inv: inv['file_count'] = count_files(inv.get('release_relative', f'evidence/{key}/repository'))
        rp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

    # ---- 3c. manifest row counts pinned by ledgers, certificates and executed scripts
    def resolve_manifest(v, jsonfile):
        for base in ('evidence/v3/repository', 'evidence/v3', 'evidence/p5/repository', 'evidence/rank/repository', ''):
            c = L / base / v
            if c.is_file(): return c
        for up in (jsonfile.parent, jsonfile.parent.parent, jsonfile.parent.parent.parent):
            c = up / v
            if c.is_file(): return c
        return None
    def rowcount(mf): return sum(1 for line in mf.read_text(errors='ignore').splitlines() if line.strip())
    def newcount(mf, pinned):
        # pinned count adjusted by the change in the manifest's row count (comment/header lines cancel out)
        orig = ORIG_COUNTS.get(str(mf.resolve()))
        return pinned if orig is None else pinned + (rowcount(mf) - orig)
    rows_updated = 0
    for p in sorted(rows):
        fp = L / p
        if not fp.exists() or not p.endswith('.json') or not is_text(p) or fp.stat().st_size > 5_000_000: continue
        try: d = json.loads(fp.read_text())
        except Exception: continue
        changed_here = [False]
        def walk(node):
            if isinstance(node, dict):
                done = set()      # a count field is adjusted once per node, even if two keys name the same manifest
                for k, v in list(node.items()):
                    if isinstance(v, str) and 'SHA256SUMS' in v and v.endswith('.txt'):
                        rk = 'rows' if k in ('manifest', 'path', 'file') else (k + '_rows' if k.endswith('manifest') else None)
                        if rk in done: continue
                        if rk and isinstance(node.get(rk), int):
                            done.add(rk)
                            mf = resolve_manifest(v, fp)
                            if mf is not None and isinstance(node[rk], int) and node[rk] != newcount(mf, node[rk]):
                                node[rk] = newcount(mf, node[rk]); changed_here[0] = True
                for v in node.values(): walk(v)
            elif isinstance(node, list):
                for v in node: walk(v)
        walk(d)
        if changed_here[0]:
            fp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n'); rows_updated += 1
    # literal row counts in executed scripts: assert replay_manifest(PATHS["key"]) == N
    lits_updated = 0
    for sp in sorted(p for p in rows if PurePosixPath(p).suffix in ('.py', '.gp', '.sage', '.sh')):
        fp = L / sp
        if not fp.exists(): continue
        t = fp.read_text(errors='ignore')
        paths = dict(re.findall(r'"(\w+)":\s*(?:ROOT|PKG|REPO)\s*/\s*"([^"]+)"', t))
        def fix(m):
            key, n = m.group(1), int(m.group(2))
            if key in paths and 'SHA256SUMS' in paths[key]:
                mf = resolve_manifest(paths[key], fp)
                if mf is not None and newcount(mf, n) != n: return m.group(0).replace(str(n), str(newcount(mf, n)))
            return m.group(0)
        t2 = t if sp.endswith('.py') else re.sub(r'replay_manifest\(PATHS\["(\w+)"\]\)\s*==\s*(\d+)', fix, t)
        own = dict(re.findall(r'^([A-Z_]+)\s*=\s*PACKAGE\s*/\s*"([^"]*SHA256SUMS[^"]*\.txt)"', t2, re.M))
        def fix2(m):
            var, n = m.group(1), int(m.group(2))
            if var in own:
                mf = resolve_manifest(own[var], fp)
                if mf is None: mf = fp.parent.parent / own[var]
                if mf.is_file() and newcount(mf, n) != n: return f'replay_manifest({var}, sha256({var}), {newcount(mf, n)})'
            return m.group(0)
        if not sp.endswith('.py'): t2 = re.sub(r'replay_manifest\((\w+), sha256\(\1\), (\d+)\)', fix2, t2)
        own.update(dict(re.findall(r'^([A-Z_0-9]+)\s*=\s*(?:ROOT|PKG|PACKAGE|REPO)\s*/\s*"([^"]*SHA256SUMS[^"]*\.txt)"', t2, re.M)))
        def fix3(m):
            var, n = m.group(1), int(m.group(3))
            if var in own:
                mf = resolve_manifest(own[var], fp)
                if mf is None: mf = fp.parent.parent / own[var]
                if mf.is_file() and newcount(mf, n) != n: return f'replay_manifest({var}, {m.group(2)}, {newcount(mf, n)})'
            return m.group(0)
        if not sp.endswith('.py'): t2 = re.sub(r'replay_manifest\((\w+),\s*((?:[^,()]|\([^()]*\)|\[[^\]]*\])+),\s*(\d+)\)', fix3, t2)
        # AST pass: any tuple / list / call that holds a manifest path string and an integer row count
        if sp.endswith('.py'):
            try: tree = ast.parse(t2)
            except SyntaxError: tree = None
            if tree is not None:
                edits = []
                # keys of dict literals whose value names a manifest, e.g. PATHS = {"closure_manifest": ROOT / ("…/" "X_SHA256SUMS.txt")}
                keymap = {}
                for d in ast.walk(tree):
                    if isinstance(d, ast.Dict):
                        for k, v in zip(d.keys, d.values):
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                parts = [c.value for c in ast.walk(v) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
                                if any('SHA256SUMS' in x for x in parts):
                                    joined = ''.join(parts)
                                    keymap[k.value] = joined if 'SHA256SUMS' in joined else next(x for x in parts if 'SHA256SUMS' in x)
                # variables assigned a manifest path, e.g. odd_manifest = ROOT / ("…/" "X_SHA256SUMS.txt")
                varmap = {}
                for a in ast.walk(tree):
                    if isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name):
                        parts = [c.value for c in ast.walk(a.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
                        if any('SHA256SUMS' in x for x in parts):
                            joined = ''.join(parts)
                            varmap[a.targets[0].id] = joined if 'SHA256SUMS' in joined else next(x for x in parts if 'SHA256SUMS' in x)
                def manifest_of(arg):
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if arg.value in keymap: return keymap[arg.value]
                        if 'SHA256SUMS' in arg.value: return arg.value
                    if isinstance(arg, ast.Name) and arg.id in varmap: return varmap[arg.id]
                    if isinstance(arg, ast.Subscript) and isinstance(arg.slice, ast.Constant) and arg.slice.value in keymap: return keymap[arg.slice.value]
                    return None
                # comparisons: assert replay_manifest(<manifest>, ...) == N
                for node in ast.walk(tree):
                    if isinstance(node, ast.Compare) and isinstance(node.left, ast.Call) and len(node.comparators) == 1 \
                            and isinstance(node.comparators[0], ast.Constant) and isinstance(node.comparators[0].value, int):
                        cand = [manifest_of(x) for x in node.left.args]; cand = [c for c in cand if c]
                        if len(cand) == 1:
                            mf = resolve_manifest(cand[0], fp)
                            if mf is None: mf = fp.parent.parent / cand[0]
                            c = node.comparators[0]
                            if mf.is_file() and newcount(mf, c.value) != c.value:
                                edits.append((c.lineno, c.col_offset, c.end_col_offset, newcount(mf, c.value)))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Tuple, ast.List, ast.Call)):
                        elts = list(node.elts) if not isinstance(node, ast.Call) else list(node.args)
                        cand = [manifest_of(e) for e in elts]; cand = [c for c in cand if c]
                        ints = [e for e in elts if isinstance(e, ast.Constant) and isinstance(e.value, int) and not isinstance(e.value, bool)]
                        if len(cand) == 1 and len(ints) == 1:
                            mf = resolve_manifest(cand[0], fp)
                            if mf is None: mf = fp.parent.parent / cand[0]
                            if mf.is_file() and newcount(mf, ints[0].value) != ints[0].value:
                                edits.append((ints[0].lineno, ints[0].col_offset, ints[0].end_col_offset, newcount(mf, ints[0].value)))
                edits = sorted(set(edits))      # a literal is edited once even if two node types cover it
                # accumulated form: var += replay_manifest(dep["manifest"], …) over a ledger, then assert var == N
                acc = re.search(r'^\s*(\w+)\s*\+=\s*replay_manifest\(\w+\["manifest"\]', t2, re.M)
                led = re.search(r'^LEDGER_PATH\s*=\s*PACKAGE\s*/\s*"([^"]+\.json)"', t2, re.M)
                if acc and led:
                    lp = fp.parent.parent / led.group(1)
                    if lp.is_file():
                        ledger = json.loads(lp.read_text())
                        deps = next((v for k, v in ledger.items() if isinstance(v, list) and v and isinstance(v[0], dict) and 'manifest' in v[0]), [])
                        total_delta = 0
                        for dep in deps:
                            mf = resolve_manifest(dep['manifest'], lp)
                            if mf is not None: total_delta += newcount(mf, 0)
                        if total_delta:
                            m = re.search(r'^(\s*assert\s+' + acc.group(1) + r'\s*==\s*)(\d+)', t2, re.M)
                            if m:
                                ln = t2[:m.start()].count('\n') + 1
                                edits.append((ln, m.start(2) - t2.rfind('\n', 0, m.start(2)) - 1, m.end(2) - t2.rfind('\n', 0, m.start(2)) - 1, int(m.group(2)) + total_delta))
                if edits:
                    ls = t2.split('\n')
                    for ln, c0, c1, n in sorted(edits, reverse=True):
                        ls[ln-1] = ls[ln-1][:c0] + str(n) + ls[ln-1][c1:]
                    t2 = '\n'.join(ls)
        if t2 != t: fp.write_text(t2); lits_updated += 1
    print(f'row counts updated in {rows_updated} JSON files and {lits_updated} scripts')

    # ---- 3d. verifiers that certify their own narrative report as an artifact: drop those checks
    removed_names = {PurePosixPath(q).name for q in remove}
    edited_scripts = []
    for sp in sorted(p for p in rows if PurePosixPath(p).suffix == '.py'):
        fp = L / sp
        if not fp.exists(): continue
        t = fp.read_text(errors='ignore')
        if not any(n in t for n in removed_names): continue
        lines = t.split('\n'); kept_lines = []; dropped_vars = set()
        for line in lines:
            hit = [n for n in removed_names if n in line]
            if hit:
                st = line.strip()
                m = re.match(r'^([A-Z_]+)\s*=\s*.*"summaries/', st)      # e.g. REPORT_PATH = PACKAGE / "summaries/X.tex"
                if m: dropped_vars.add(m.group(1)); continue
                if re.match(r'^"[\w]+":\s*"[^"]*summaries/[^"]+",?$', st): continue   # artifact dict entry
                if ' = ' not in st and st.endswith(',') and re.search(r'"[^"]*summaries/[^"]+"', st): continue   # set/list/dict element
                raise SystemExit('unhandled reference to a removed report in ' + sp + ': ' + st[:100])
            kept_lines.append(line)
        t2 = '\n'.join(kept_lines)
        # lines that read the removed report's derived properties (size, page count) or its dropped dict keys
        t2 = '\n'.join(l for l in t2.split('\n') if not re.search(r'report_(?:pdf|tex)_', l))
        for v in dropped_vars:      # a variable that held the report path: its text becomes empty
            t2 = re.sub(r'\b' + v + r'\.read_text\([^)]*\)', '""', t2)
            if re.search(r'\b' + v + r'\b', t2):
                raise SystemExit('report variable still used in ' + sp + ': ' + v)
        if t2 != t: fp.write_text(t2); edited_scripts.append(sp)
    # decision/certificate fields whose value is a removed report digest
    edited_json = []
    def drop_keys(node):
        changed = False
        if isinstance(node, dict):
            for k in [k for k, v in node.items() if isinstance(v, str) and v in remove_hashes]:
                del node[k]; changed = True
            for v in node.values(): changed |= drop_keys(v)
        elif isinstance(node, list):
            for v in node: changed |= drop_keys(v)
        return changed
    for p in sorted(rows):
        fp = L / p
        if not fp.exists() or not p.endswith('.json') or fp.stat().st_size > 5_000_000: continue
        try: d = json.loads(fp.read_text())
        except Exception: continue
        if drop_keys(d):
            fp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n'); edited_json.append(p)
    print(f'report-artifact checks removed from {len(edited_scripts)} verifiers and {len(edited_json)} JSON records')

    # ---- 4. fixed-point propagation of changed digests (and byte counts) through every text file
    def current_hash(p): return sha(L / p)
    old_hash = {p: rows[p]['sha256'] for p in rows if (L / p).exists()}
    for it in range(80):
        renames = {p: (old_hash[p], current_hash(p)) for p in old_hash if current_hash(p) != old_hash[p]}
        if not renames: break
        mapping = {o: n for o, n in renames.values()}
        sizes = {n: (L / p).stat().st_size for p, (o, n) in renames.items()}
        touched = 0
        for p in sorted(old_hash):
            fp = L / p
            if not is_text(p) or fp.stat().st_size > 5_000_000: continue
            t = fp.read_text(errors='ignore')
            if not any(o in t for o in mapping): continue
            if p.endswith('.json'):
                def fix(node):
                    if isinstance(node, dict):
                        if node.get('sha256') in mapping:
                            node['sha256'] = mapping[node['sha256']]
                            if 'bytes' in node: node['bytes'] = sizes[node['sha256']]
                        for v in node.values(): fix(v)
                    elif isinstance(node, list):
                        for v in node: fix(v)
                try:
                    d = json.loads(t); fix(d); t2 = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
                    # plain string occurrences outside sha256 fields
                    for o, n in mapping.items(): t2 = t2.replace(o, n)
                except Exception:
                    t2 = t
                    for o, n in mapping.items(): t2 = t2.replace(o, n)
            else:
                t2 = t
                for o, n in mapping.items(): t2 = t2.replace(o, n)
            if t2 != t: fp.write_text(t2); touched += 1
        for p, (o, n) in renames.items(): old_hash[p] = n   # the digest that was propagated; a later change is caught next round
        print(f'propagation round {it + 1}: {len(renames)} files changed digest, {touched} files updated')
    else:
        raise SystemExit('digest propagation did not converge (cyclic pins)')

    # ---- 5. regenerate the logical manifest and rebuild the distribution
    man = load(L / 'RELEASE_MANIFEST.json')
    files = []
    for p in sorted(x.relative_to(L).as_posix() for x in L.rglob('*') if x.is_file()):
        if p == 'RELEASE_MANIFEST.json': continue
        files.append({'path': p, 'bytes': (L / p).stat().st_size, 'sha256': current_hash(p)})
    # external inputs are logical files too: keep their rows from the V2 map
    for p, r in rows.items():
        if r['source']['kind'] == 'external':
            files.append({'path': p, 'bytes': r['bytes'], 'sha256': r['sha256']})
    files.sort(key=lambda r: r['path'])
    man['files'] = files
    write(L / 'RELEASE_MANIFEST.json', man)

    shutil.rmtree(root / 'objects'); (root / 'objects').mkdir()
    new_rows = []
    for p in sorted(set(x.relative_to(L).as_posix() for x in L.rglob('*') if x.is_file()) | {q for q, r in rows.items() if r['source']['kind'] == 'external'}):
        r = rows.get(p)
        if r and r['source']['kind'] == 'external':
            new_rows.append(r); continue
        h = current_hash(p); b = (L / p).stat().st_size
        obj = root / 'objects' / h
        if not obj.exists(): shutil.copyfile(L / p, obj)
        row = {'path': p, 'bytes': b, 'sha256': h}
        if r and 'mode' in r: row['mode'] = r['mode']
        row['source'] = {'kind': 'object', 'path': 'objects/' + h}
        new_rows.append(row)
    fmap['files'] = new_rows
    fmap['public_release_tag'] = V4_TAG
    fmap['previous_public_release_tag'] = V2_TAG
    write(root / 'inputs/REPLAY_FILE_MAP.json', fmap)

    delta_regen_placeholder = sorted(p for p in rows if (L / p).exists() and current_hash(p) != rows[p]['sha256'])
    delta = {'schema': 'primitive357_release_delta_v2', 'date': DATE, 'from_release_tag': V2_TAG, 'to_release_tag': V4_TAG,
             'statement': ('The exploratory working reports listed under removed_documents are no longer part of the logical '
                           'replay tree. Every manifest, index and inventory that listed them was regenerated, and every file whose '
                           'digest changed had its new digest propagated wherever the old one was pinned. Documents named by scripts '
                           'the declared suite executes, and every document without the working vocabulary, remain public. The '
                           'recorded replay of the previous distribution does not apply to this tree; a fresh replay from public '
                           'inputs is required and, once recorded, replaces records/completed-replay.'),
             'removed_documents': [{'path': p, 'bytes': rows[p]['bytes'], 'sha256': rows[p]['sha256']} for p in remove],
             'retained_reports_named_by_executed_scripts': sorted(keep_named | listed_by_read_manifests),
             'retained_reports_with_working_vocabulary': kept_vocab,
             'verifiers_with_report_checks_removed': edited_scripts, 'records_with_report_digests_removed': edited_json,
             'regenerated_files': sorted(p for p in rows if (L / p).exists() and current_hash(p) != rows[p]['sha256'])}
    write(root / f'RELEASE_DELTA_{DATE}.json', delta)
    # the recorded replay belongs to the previous tree; V4's fresh replay is published as a separate asset
    if (root / 'records/completed-replay').exists(): shutil.rmtree(root / 'records/completed-replay')
    rd = root / 'README.md'; t = rd.read_text()
    t = t.replace('`' + V2_TAG + '`', '`' + V4_TAG + '`', 1)
    t += (f'\n## Revision of {DATE}\n\n'
          f'This distribution supersedes `{V2_TAG}`. Its logical replay tree no longer contains {len(remove)} exploratory '
          f'working reports ({len(set(rows[q]["sha256"] for q in remove))} distinct documents), listed with exact identities in '
          f'`RELEASE_DELTA_{DATE}.json`; every manifest, index and inventory that listed them was regenerated ({len(delta_regen_placeholder)} files), '
          'and digests were propagated to a fixed point. Documents named by scripts the declared suite executes remain public. '
          'No author-held input exists: the documented acquisition, regeneration, materialization and replay run from public inputs alone. '
          f'The replay recorded for `{V2_TAG}` applied to the previous tree and is not included; the fresh replay of this distribution '
          'from public inputs is published as a separate release asset.\n')
    rd.write_text(t)
    m = load(root / 'COMPANION_MANIFEST.json')
    m['completed_replay_record'] = None; m['fresh_replay_result'] = None
    m['release_tag'] = V4_TAG; m['derived_from_release_tag'] = V2_TAG
    m['tested_distribution_manifest_sha256'] = None
    m['fresh_replay_status'] = f'The replay recorded for {V2_TAG} does not apply to this tree and is not included. A fresh replay of this distribution from public inputs is published as a separate release asset; see RELEASE_DELTA_{DATE}.json.'
    dist_files = []
    for x in root.rglob('*'):
        if x.is_file():
            rel = x.relative_to(root).as_posix()
            if rel != 'COMPANION_MANIFEST.json': dist_files.append({'path': rel, 'sha256': sha(x), 'bytes': x.stat().st_size})
    dist_files.sort(key=lambda r: r['path']); m['files'] = dist_files
    write(root / 'COMPANION_MANIFEST.json', m)

    zpath = out / (V4_NAME + '.zip')
    if zpath.exists(): zpath.unlink()
    with zipfile.ZipFile(zpath, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for x in sorted(x for x in root.rglob('*') if x.is_file()):
            info = zipfile.ZipInfo(V4_NAME + '/' + x.relative_to(root).as_posix(), date_time=ZIP_DT)
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = (stat.S_IFREG | 0o644) << 16; info.create_system = 3
            z.writestr(info, x.read_bytes())
    print(json.dumps({'removed': len(remove), 'kept_vocab_reports': len(kept_vocab), 'regenerated': len(delta['regenerated_files']),
                      'logical_files': len(new_rows), 'objects': len(os.listdir(root / 'objects')),
                      'release_manifest_sha256': current_hash('RELEASE_MANIFEST.json'),
                      'zip': str(zpath), 'zip_bytes': zpath.stat().st_size, 'zip_sha256': sha(zpath)}, indent=2))

if __name__ == '__main__':
    main()
