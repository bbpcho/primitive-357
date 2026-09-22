#!/usr/bin/env python3
"""Build the V3 companion from an extracted V2 companion.

The author's internal working reports (every *.pdf, *.tex and *.md under a
results/*/summaries/ directory, plus the Spark-handover progress report) stop
being public objects.  They become author-held inputs of the external-inputs
lock, exactly like the third-party papers: their exact byte counts and SHA-256
digests stay in the lock and in the logical file map, so the materialized
replay tree is byte-for-byte the same as the one the recorded replay used
(RELEASE_MANIFEST.json is unchanged), but the public distribution no longer
carries the documents themselves.

Usage: python3 build_privatised_companion.py V2_ROOT OUT_DIR
Produces OUT_DIR/<V3 name>/ and OUT_DIR/<V3 name>.zip (deterministic).
"""
import hashlib, json, os, re, shutil, stat, sys, zipfile
from pathlib import Path, PurePosixPath

V2_TAG  = 'replay-companion-2026-09-15.2'
V3_TAG  = 'replay-companion-2026-09-22.1'
V3_NAME = 'PRIMITIVE_357_REPLAY_COMPANION_2026-09-22_V3'
DATE    = '2026-09-22'
ZIP_DT  = (2026, 9, 22, 0, 0, 0)

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def load(p):
    return json.loads(Path(p).read_text())

def write(p, data):
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def is_report(path):
    ext = PurePosixPath(path).suffix
    if '/summaries/' in path and ext in ('.pdf', '.tex', '.md'):
        return True
    return path in (
        'evidence/v3/repository/beal_357_spark_handover_2026-08-20/project/beal_357_progress.pdf',
        'evidence/v3/repository/beal_357_spark_handover_2026-08-20/project/beal_357_progress.tex',
        # audit-history bundle that carries copies and variants of two of the reports above
        'audit/history/v3_review_bundle.zip',
    )

def patch_scripts(root):
    """Teach the tooling about the author_inputs collection (minimal edits)."""
    cc = root / 'scripts/companion_common.py'
    s = cc.read_text()
    old = "    rows=lock.get('inputs',[])+lock.get('derived_inputs',[])\n"
    new = "    rows=lock.get('inputs',[])+lock.get('derived_inputs',[])+lock.get('author_inputs',[])\n"
    assert s.count(old) == 1; cc.write_text(s.replace(old, new))

    aq = root / 'scripts/acquire_external_inputs.py'
    s = aq.read_text()
    edits = [
        ("    for r in records+obj.get('derived_inputs',[]):\n        name=r.get('id'); sha=r.get('sha256'); size=r.get('bytes')\n        expected_kind='download' if r in records else 'derived'\n",
         "    authors=obj.get('author_inputs',[])\n    for r in records+obj.get('derived_inputs',[])+authors:\n        name=r.get('id'); sha=r.get('sha256'); size=r.get('bytes')\n        expected_kind='download' if r in records else ('author' if r in authors else 'derived')\n"),
        ("def acquire(r,cache,offline,explicit):\n    target=cache/r['sha256'];no_symlinks(target)\n",
         "def acquire(r,cache,offline,explicit):\n    target=cache/r['sha256'];no_symlinks(target)\n    if r.get('kind')=='author' and explicit is None and not target.exists():\n        raise InputError(f'Author-held input {r[\"id\"]} ({r[\"sha256\"]}) is not downloadable; supply --file ID=PATH or --author-dir DIR')\n"),
        ("    ap.add_argument('--only',action='append',default=[],metavar='ID')\n",
         "    ap.add_argument('--only',action='append',default=[],metavar='ID')\n    ap.add_argument('--author-dir',type=Path,help='directory holding author-held inputs named by their SHA-256')\n"),
        ("        ids={r['id'] for r in lock['inputs']};explicit={}\n",
         "        authors=lock.get('author_inputs',[]);ids={r['id'] for r in lock['inputs']+authors};explicit={}\n        if args.author_dir is not None:\n            for r in authors:\n                candidate=no_symlinks(args.author_dir)/r['sha256']\n                if candidate.is_file(): explicit[r['id']]=candidate\n"),
        ("        selected=[r for r in lock['inputs'] if not args.only or r['id'] in args.only]\n",
         "        selected=[r for r in lock['inputs']+authors if not args.only or r['id'] in args.only]\n"),
        ("'complete_lock_selection':len(selected)==len(lock['inputs']),",
         "'complete_lock_selection':len(selected)==len(lock['inputs'])+len(authors),"),
    ]
    for old, new in edits:
        assert s.count(old) == 1, old[:60]
        s = s.replace(old, new)
    aq.write_text(s)

    cp = root / 'scripts/check_public_contents.py'
    s = cp.read_text()
    old = "    forbidden={r['sha256']:r['id'] for r in lock['inputs']+lock['derived_inputs']}\n"
    new = "    forbidden={r['sha256']:r['id'] for r in lock['inputs']+lock['derived_inputs']+lock.get('author_inputs',[])}\n"
    assert s.count(old) == 1; cp.write_text(s.replace(old, new))

def main(v2_root, out_dir):
    v2_root = Path(v2_root).resolve(); out_dir = Path(out_dir).resolve()
    root = out_dir / V3_NAME
    if root.exists(): shutil.rmtree(root)
    shutil.copytree(v2_root, root, symlinks=False)

    fmap = load(root / 'inputs/REPLAY_FILE_MAP.json')
    lock = load(root / 'inputs/EXTERNAL_INPUTS_LOCK.json')
    assert lock.get('author_inputs') is None and fmap['public_release_tag'] == V2_TAG

    # 1. select the reports and group them by content digest
    rows = fmap['files']
    reports = [r for r in rows if r['source']['kind'] == 'object' and is_report(r['path'])]
    by_sha = {}
    for r in reports:
        by_sha.setdefault(r['sha256'], []).append(r)
    # an object may only leave the public store if every logical path using it is a report
    keep_public = set()
    for r in rows:
        if r['source']['kind'] == 'object' and r['sha256'] in by_sha and not is_report(r['path']):
            keep_public.add(r['sha256'])
    assert not keep_public, f'objects shared with non-report paths: {sorted(keep_public)}'

    # 2. author-held lock entries, in deterministic order
    author_inputs = []
    used_ids = {e['id'] for e in lock['inputs'] + lock['derived_inputs']}
    for digest in sorted(by_sha):
        group = by_sha[digest]
        base = PurePosixPath(group[0]['path']).stem.lower()
        ident = 'author-' + re.sub(r'[^a-z0-9]+', '-', base).strip('-')[:48] + '-' + digest[:8]
        assert ident not in used_ids; used_ids.add(ident)
        author_inputs.append({
            'id': ident, 'kind': 'author', 'sha256': digest, 'bytes': group[0]['bytes'],
            'logical_destinations': sorted(r['path'] for r in group), 'private_destinations': [],
            'material_type': 'author_working_document',
            'rights_status': "Author's internal working report. Not part of the public distribution; supplied by the author on request for a full replay, and authenticated by the digest above.",
        })
        for r in group:
            r['source'] = {'kind': 'external', 'id': ident}
    lock['author_inputs'] = author_inputs
    lock['policy']['author_working_documents'] = (
        f'{len(reports)} internal working reports ({len(author_inputs)} distinct documents) are author-held inputs since {DATE}: '
        'their exact identities remain in this lock and in the logical file map, so the materialized replay tree is unchanged, '
        'but the documents are not redistributed.')
    fmap['public_release_tag'] = V3_TAG
    fmap['previous_public_release_tag'] = V2_TAG
    write(root / 'inputs/REPLAY_FILE_MAP.json', fmap)
    write(root / 'inputs/EXTERNAL_INPUTS_LOCK.json', lock)

    # 3. drop the objects no logical path references any more
    referenced = {r['sha256'] for r in rows if r['source']['kind'] == 'object'}
    removed_objects = []
    for obj in sorted(os.listdir(root / 'objects')):
        if obj not in referenced:
            (root / 'objects' / obj).unlink(); removed_objects.append(obj)
    assert set(removed_objects) == set(by_sha)

    # 4. tooling and documentation
    patch_scripts(root)
    delta = {
        'schema': 'primitive357_release_delta_v1', 'date': DATE,
        'from_release_tag': V2_TAG, 'to_release_tag': V3_TAG,
        'statement': ('The only change from the previous distribution is that the listed author working '
                      'reports are no longer public objects; they are author-held inputs in inputs/EXTERNAL_INPUTS_LOCK.json '
                      'with unchanged logical paths, byte counts and SHA-256 digests. RELEASE_MANIFEST.json, and therefore the '
                      'materialized replay tree and the recorded replay, are unchanged.'),
        'author_held_documents': author_inputs,
        'removed_public_objects': removed_objects,
    }
    write(root / f'RELEASE_DELTA_{DATE}.json', delta)
    readme = root / 'README.md'
    s = readme.read_text()
    s = s.replace(f'`{V2_TAG}`', f'`{V3_TAG}`', 1)
    s += (f'\n## Author-held working documents ({DATE})\n\n'
          f'This distribution replaces `{V2_TAG}`. The only difference is that {len(reports)} internal working '
          f'reports ({len(author_inputs)} distinct documents, listed in `RELEASE_DELTA_{DATE}.json` and in the `author_inputs` '
          'collection of `inputs/EXTERNAL_INPUTS_LOCK.json`) are no longer public objects. Their logical paths, byte counts '
          'and SHA-256 digests are unchanged, so `RELEASE_MANIFEST.json` and the materialized replay tree are identical to '
          'the replayed distribution. For a full replay the author supplies these documents on request; '
          '`scripts/acquire_external_inputs.py --author-dir DIR` authenticates them into the private cache. The public '
          'integrity check and the public-contents scan treat them exactly like the third-party inputs.\n')
    readme.write_text(s)
    guide = root / 'EXTERNAL_INPUTS_GUIDE.md'
    s = guide.read_text()
    s += (f'\n## Author-held inputs\n\nThe `author_inputs` collection (kind `author`) lists the author\'s internal working reports. '
          'They are never downloaded: place each file in a directory under its SHA-256 name and pass `--author-dir DIR` to '
          '`scripts/acquire_external_inputs.py`, or supply `--file ID=PATH`. Materialization then authenticates them like every other input.\n')
    guide.write_text(s)

    # 5. distribution manifest
    man = load(root / 'COMPANION_MANIFEST.json')
    man['release_tag'] = V3_TAG
    man['derived_from_release_tag'] = V2_TAG
    man['derived_from_tested_distribution_manifest_sha256'] = man['tested_distribution_manifest_sha256']
    man['distribution_note'] = (f'Differs from the tested distribution only by the author-held inputs recorded in RELEASE_DELTA_{DATE}.json; '
                                'the logical manifest RELEASE_MANIFEST.json is unchanged.')
    files = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = Path(dp) / f; rel = p.relative_to(root).as_posix()
            if rel == 'COMPANION_MANIFEST.json': continue
            files.append({'path': rel, 'sha256': sha(p), 'bytes': p.stat().st_size})
    files.sort(key=lambda r: r['path'])
    man['files'] = files
    write(root / 'COMPANION_MANIFEST.json', man)

    # 6. deterministic zip: sorted entries, fixed timestamp, deflate level 9, mode 0644
    zpath = out_dir / (V3_NAME + '.zip')
    if zpath.exists(): zpath.unlink()
    entries = sorted(p for p in root.rglob('*') if p.is_file())
    with zipfile.ZipFile(zpath, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in entries:
            arc = V3_NAME + '/' + p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(arc, date_time=ZIP_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.create_system = 3
            z.writestr(info, p.read_bytes())
    print(json.dumps({'v3_root': str(root), 'zip': str(zpath), 'zip_bytes': zpath.stat().st_size, 'zip_sha256': sha(zpath),
                      'reports_privatised': len(reports), 'distinct_documents': len(author_inputs),
                      'public_files': len(files) + 1, 'objects': len(referenced),
                      'release_manifest_sha256': next(r['sha256'] for r in rows if r['path'] == 'RELEASE_MANIFEST.json')}, indent=2))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
