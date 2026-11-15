#!/usr/bin/env python3
"""Hide UI that has no place on 2Web (store purchases, ad buttons, sharing, store review, online
ranking) in a Unity WebGL .data file.

    python3 patch_scene.py <in.data> <out.data>

Each listed object is switched off and its RectTransform scaled to 0, so it stays invisible and
cannot be clicked even if a game script switches it back on. Needs UnityPy (pip install UnityPy).
"""
import os, struct, sys, tempfile
import UnityPy

HIDE = [
    'Canvas/Game Over Panel/Shop Content/Shop Items/Remove Ads',      # IAP: remove ads
    'Canvas/Game Over Panel/Shop Content/Shop Items/Remove Ads (3)',  # IAP: remove ads (second offer)
    'Canvas/Game Over Panel/Display Score Content/Share Button',      # opens native share / links out
    'Canvas/ReviewPopUpPanel',                                        # "rate us" -> app store link
    'Canvas/Title/Main Panel/Content/Buttons/Ranking Button',                # Firebase online ranking
    'Canvas/Title/Sub Panel/Content/Ranking',                                # Firebase online ranking panel
    'Canvas/OfflineEarningsPanel/Content/Ad Button',                   # rewarded video (mobile ads)
]


def read_webdata(buf):
    assert buf[:16] == b'UnityWebData1.0\0'
    head = struct.unpack_from('<I', buf, 16)[0]
    p, out = 20, []
    while p < head:
        off, size, n = struct.unpack_from('<III', buf, p); p += 12
        out.append((buf[p:p + n].decode(), buf[off:off + size])); p += n
    return out


def write_webdata(entries):
    head = 20 + sum(12 + len(n.encode()) for n, _ in entries)
    table, body, off = b'', b'', head
    for n, d in entries:
        nb = n.encode()
        table += struct.pack('<III', off, len(d), len(nb)) + nb
        body += d; off += len(d)
    return b'UnityWebData1.0\0' + struct.pack('<I', head) + table + body


def patch_bundle(data):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'data.unity3d')
        open(src, 'wb').write(data)
        env = UnityPy.load(src)
        tf = {}
        for o in env.objects:
            if o.type.name in ('Transform', 'RectTransform'):
                tf[o.path_id] = o

        def path(o):
            names, t = [], o.read()
            while True:
                names.append(t.m_GameObject.read().m_Name)
                if not t.m_Father or t.m_Father.path_id == 0 or t.m_Father.path_id not in tf:
                    break
                t = tf[t.m_Father.path_id].read()
            return '/'.join(reversed(names))

        found = set()
        for pid, o in tf.items():
            p = path(o)
            if p not in HIDE:
                continue
            found.add(p)
            tree = o.read_typetree()
            tree['m_LocalScale'] = {'x': 0.0, 'y': 0.0, 'z': 0.0}
            o.save_typetree(tree)
            go = tree['m_GameObject']
            gobj = o.assets_file.objects[go['m_PathID']]
            gtree = gobj.read_typetree()
            gtree['m_IsActive'] = False
            gobj.save_typetree(gtree)
            print('hidden:', p)
        missing = set(HIDE) - found
        if missing:
            sys.exit('not found in scene: ' + ', '.join(sorted(missing)))
        bundle = next(iter(env.files.values()))
        return bundle.save(packer='none')


def main(src, dst):
    entries = read_webdata(open(src, 'rb').read())
    entries = [(n, patch_bundle(d) if n == 'data.unity3d' else d) for n, d in entries]
    open(dst, 'wb').write(write_webdata(entries))


if __name__ == '__main__':
    main(*sys.argv[1:3])
