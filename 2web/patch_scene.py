#!/usr/bin/env python3
"""Hide UI that has no place on 2Web (store purchases, ad buttons, sharing, store review, online
ranking) in a Unity WebGL .data file.

    python3 patch_scene.py <in.data> <out.data>

Each listed object is switched off and its RectTransform scaled to 0, so it stays invisible and
cannot be clicked even if a game script switches it back on. Needs UnityPy (pip install UnityPy).
"""
import json, os, struct, sys, tempfile
import UnityPy

HIDE = [
    'Canvas/Game Over Panel/Shop Content/Shop Items/Remove Ads',      # IAP: remove ads
    'Canvas/Game Over Panel/Shop Content/Shop Items/Remove Ads (3)',  # IAP: remove ads (second offer)
    'Canvas/Game Over Panel/Display Score Content/Share Button',      # opens native share / links out
    'Canvas/ReviewPopUpPanel',                                        # "rate us" -> app store link
    'Canvas/Title/Main Panel/Content/Buttons/Ranking Button',                # Firebase online ranking
    'Canvas/Title/Sub Panel/Content/Ranking',                                # Firebase online ranking panel
    'Canvas/Title/Main Panel/Content/Title Text/Title Text (1)',  # "Port by ..." credit line
    'Canvas/OfflineEarningsPanel/Content/Ad Button',                   # rewarded video (mobile ads)
]

# Switched off only (not scaled): game objects whose scripts talk to online services.
DISABLE = [
    'FirebaseController',   # Firebase auth/database for the online ranking; Android-only on Unity
]


# Layout for tall phone screens and the 2Web edge rule (nothing important in the outer 40 px).
MOVE = {  # anchoredPosition
    'Canvas/GP': (20.0, -40.0),                              # coin counter, top-left
    'Canvas/Game Play Panel/Content/Score': (-20.0, -40.0),  # score, top-right
    'Canvas/Title/Main Panel/Content/Title Text': (0.0, -27.0),  # title: clear of the coin counter
}
SCALE = {  # localScale (x = y = z)
    'Canvas/Title/Main Panel/Content/Title Text': 1.7,       # was 2.64: cut off on upright phones
}


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
            if p in MOVE or p in SCALE:
                tree = o.read_typetree()
                if p in MOVE:
                    tree['m_AnchoredPosition'] = {'x': MOVE[p][0], 'y': MOVE[p][1]}
                if p in SCALE:
                    tree['m_LocalScale'] = {'x': SCALE[p], 'y': SCALE[p], 'z': SCALE[p]}
                o.save_typetree(tree)
                found.add(p); print('layout:', p)
                continue
            if p in DISABLE:
                gobj = o.assets_file.objects[o.read_typetree()['m_GameObject']['m_PathID']]
                gtree = gobj.read_typetree(); gtree['m_IsActive'] = False; gobj.save_typetree(gtree)
                found.add(p); print('disabled:', p)
                continue
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
        # Unity Connect (analytics, config fetches): off, no URLs
        for o in env.objects:
            if o.type.name == 'UnityConnectSettings':
                t = o.read_typetree()
                t['m_Enabled'] = False
                for k in ('m_EventOldUrl', 'm_EventUrl', 'm_ConfigUrl', 'm_DashboardUrl'):
                    t[k] = ''
                t['CrashReportingSettings']['m_EventUrl'] = ''
                t['CrashReportingSettings']['m_Enabled'] = False
                t['UnityAnalyticsSettings']['m_InitializeOnStartup'] = False
                t['UnityAdsSettings']['m_InitializeOnStartup'] = False
                o.save_typetree(t)
                print('unity connect: off')
        # I2 Localization "live sync": the language source downloads updated translations from a
        # Google Apps Script at start. Blank the web service URL and sheet key so it never does.
        for o in env.objects:
            if o.type.name != 'MonoBehaviour':
                continue
            raw = o.get_raw_data()
            at = raw.find(b'https://script.google.com/')
            if at < 0:
                continue
            for _ in range(2):  # Google_WebServiceURL, then Google_SpreadsheetKey right after it
                n = struct.unpack_from('<i', raw, at - 4)[0]
                padded = (n + 3) & ~3
                raw = raw[:at - 4] + b'\0\0\0\0' + raw[at + padded:]
                at += 4  # the next string's text starts after its own length prefix
            o.set_raw_data(raw)
            found.add('i2-live-sync')
            print('i2 localization live sync: off')
        # Blank the "Port by ..." credit text itself (its object is also hidden above).
        for o in env.objects:
            if o.type.name != 'MonoBehaviour':
                continue
            raw = o.get_raw_data()
            at = raw.find(b'Port by 98corbins')
            if at < 0:
                continue
            n = struct.unpack_from('<i', raw, at - 4)[0]
            raw = raw[:at - 4] + b'\0\0\0\0' + raw[at + ((n + 3) & ~3):]
            o.set_raw_data(raw)
            found.add('port-credit')
            print('credit text: blanked')
        missing = set(HIDE + DISABLE + ['port-credit'] + list(MOVE) + list(SCALE) + ['i2-live-sync']) - found
        if missing:
            sys.exit('not found in scene: ' + ', '.join(sorted(missing)))
        bundle = next(iter(env.files.values()))
        return bundle.save(packer='none')


# Startup hooks that only serve Unity Services / Analytics / IAP (all phone-store features that
# send data off the device or fail on the web). The localisation hooks stay.
DROP_ON_LOAD = ('Unity.Services.', 'UnityEngine.Purchasing')


def patch_onloads(data):
    j = json.loads(data)
    keep = [e for e in j['root'] if not e['assemblyName'].startswith(DROP_ON_LOAD)]
    for e in j['root']:
        if e not in keep:
            print('startup hook dropped:', e['className'] + '.' + e['methodName'])
    j['root'] = keep
    return json.dumps(j, separators=(',', ':')).encode()


def main(src, dst):
    entries = read_webdata(open(src, 'rb').read())
    fix = {'data.unity3d': patch_bundle, 'RuntimeInitializeOnLoads.json': patch_onloads}
    entries = [(n, fix[n](d) if n in fix else d) for n, d in entries]
    open(dst, 'wb').write(write_webdata(entries))


if __name__ == '__main__':
    main(*sys.argv[1:3])
