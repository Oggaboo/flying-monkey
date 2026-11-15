#!/usr/bin/env python3
"""Build the 2Web zip for Flying Gorilla from the Unity WebGL export in ../Build.

    python3 2web/build.py            ->  dist/flying-gorilla/  and  dist/flying-gorilla-<version>.zip

Steps: join the split .data/.wasm, hide store/ad/share/review UI in the scene data
(patch_scene.py, needs UnityPy), gzip -9 both, split into parts under 20 MB, copy the
listing, pictures and index.html, then zip.
"""
import gzip, json, os, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SLUG = 'flying-gorilla'
PART = 20 * 1024 * 1024
DIST = os.path.join(ROOT, 'dist')
OUT = os.path.join(DIST, SLUG)
WORK = os.path.join(DIST, '.work')


def join(name):
    parts = sorted(p for p in os.listdir(os.path.join(ROOT, 'Build')) if p.startswith(name + '.part'))
    data = b''.join(open(os.path.join(ROOT, 'Build', p), 'rb').read() for p in parts)
    if not data:
        data = open(os.path.join(ROOT, 'Build', name), 'rb').read()
    return data


def write_gz(data, base):
    """gzip -9 `data`, split into PART-sized files Build/<base>.gz[.N].bin; return names."""
    gz = gzip.compress(data, 9, mtime=0)
    chunks = [gz[i:i + PART] for i in range(0, len(gz), PART)]
    names = [f'Build/{base}.gz.bin'] if len(chunks) == 1 else \
            [f'Build/{base}.gz.{i + 1}.bin' for i in range(len(chunks))]
    for n, c in zip(names, chunks):
        open(os.path.join(OUT, n), 'wb').write(c)
    return names, len(gz)


def main():
    meta = json.load(open(os.path.join(HERE, '2web.json')))
    assert meta['slug'] == SLUG
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(os.path.join(OUT, 'Build'))
    os.makedirs(WORK)

    raw = os.path.join(WORK, 'vb.data')
    open(raw, 'wb').write(join('vb.data'))
    patched = os.path.join(WORK, 'vb.patched.data')
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'patch_scene.py'), raw, patched], check=True)

    data_files, data_gz = write_gz(open(patched, 'rb').read(), 'vb.data')
    wasm_files, wasm_gz = write_gz(join('vb.wasm'), 'vb.wasm')
    for f in ('vb.loader.js', 'vb.framework.js'):
        shutil.copy(os.path.join(ROOT, 'Build', f), os.path.join(OUT, 'Build', f))

    html = open(os.path.join(HERE, 'index.html')).read()
    html = html.replace("data: ['Build/vb.data.gz.1.bin', 'Build/vb.data.gz.2.bin']", 'data: ' + json.dumps(data_files).replace('"', "'"))
    html = html.replace("wasm: ['Build/vb.wasm.gz.bin']", 'wasm: ' + json.dumps(wasm_files).replace('"', "'"))
    html = html.replace('var TOTAL = 43420000;', f'var TOTAL = {data_gz + wasm_gz};')
    html = html.replace("var VERSION = '1.0.0';", f"var VERSION = '{meta['version']}';")
    open(os.path.join(OUT, 'index.html'), 'w').write(html)
    for f in ('2web.json', 'thumb.webp', 'cover.jpg'):
        shutil.copy(os.path.join(HERE, f), os.path.join(OUT, f))
    shutil.rmtree(WORK)

    files = []
    for d, _, fs in os.walk(OUT):
        files += [os.path.join(d, f) for f in fs]
    total = sum(os.path.getsize(f) for f in files)
    biggest = max(os.path.getsize(f) for f in files)
    zpath = os.path.join(DIST, f"{SLUG}-{meta['version']}.zip")
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files):
            z.write(f, os.path.relpath(f, DIST))
    print(f'{len(files)} files, {total / 1e6:.1f} MB total, largest {biggest / 1e6:.1f} MB')
    print(zpath)
    assert total <= 50 * 1024 * 1024 and biggest <= 25 * 1024 * 1024 and len(files) <= 500


if __name__ == '__main__':
    main()
