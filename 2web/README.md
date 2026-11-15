# Flying Gorilla: 2Web build

`python3 2web/build.py` (needs `pip install UnityPy`) turns the Unity WebGL export in `Build/`
into `dist/flying-gorilla-<version>.zip`, ready to send to 2Web.

What it does to the export:

- **Size:** joins the split `.data`/`.wasm`, gzips them and splits into parts under 21 MB
  (72 MB to about 44 MB). `index.html` downloads the parts and unpacks them in the browser.
- **Scene patch** (`patch_scene.py`):
  - hides the "Port by" credit line, the Remove Ads shop items, the rewarded-ad button, Share, the rate-us popup and the
    online ranking button and panel;
  - switches off `FirebaseController`;
  - turns off Unity Connect (analytics) and I2 Localization's Google Sheets sync;
  - drops the Unity Services, Analytics and IAP startup hooks;
  - fixes the layout for upright phones and the 40 px edge rule.
- **`index.html`:**
  - loads the 2Web SDK and calls `TwoWeb.ready()` once the menu is up;
  - pauses and mutes in `onPause`;
  - blocks pop-ups and dialogs;
  - stores saves under `flying-gorilla:` IndexedDB names;
  - logs the version and exposes `window.__game`.

`make_pictures.py` makes `cover.jpg` and `thumb.webp` from the source art in `art/`, unchanged.
To release an update, bump `version` in `2web.json` and rebuild.
