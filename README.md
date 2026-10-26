# PhysTrace project page

Static project page for **PhysTrace** (qualitative results: Wan2.1-1.3B and Cosmos-Predict2-2B at σ 0.8,
per-window PE-AV-Large scores, Qwen3-VL prediction/state sentences, 2 s window clips).

Deployed with GitHub Pages from the repository root.

## Layout
- `index.html` — the page (template + data assembled; do not edit by hand).
- `data.json` — scores, windows, sentences and media paths for every scene/model/sigma.
- `media/<scene>/` — input clip, full reconstructions and 2 s window clips (mp4).
- `.nojekyll` — tells GitHub Pages to serve files as-is.
- `build/` — build code.
  - `build_data.py` — reads scoring results + reconstructions on the server, writes `data.json` and cuts the videos (needs ffmpeg). Server only.
  - `template.html` — page layout, styles and script. Data is injected at `/*DATA*/null`.
  - `assemble.py` — puts `data.json` into the template and writes `index.html`.

## Rebuild
```bash
# 1) (server only) data + videos
WAN_T=4 COS_T=2 python3 build/build_data.py .
# 2) page -> ./index.html
python3 build/assemble.py .
# single self-contained file for quick sharing -> ../PhysTrace.io_inline.html
python3 build/assemble.py . --inline
```

## What to change
- Scenes and one-line descriptions: `SCENES` in `build/build_data.py`.
- Which seed-42 trial is shown: env `WAN_T` (default 4), `COS_T` (default 2).
- Sigmas: `SIGMAS` in `build/build_data.py`.
- Links, title, text: `build/template.html` (Code link → https://github.com/PhysTrace/PhysTrace).
