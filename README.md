# PhysTrace project page

Static project page for **PhysTrace**, in two sections:

1. **Generative reconstructions**: IntPhys2 Impossible clips noised to σ 0.8 and reconstructed by Wan2.1-1.3B and
   Cosmos-Predict2-2B, with per-window PE-AV-Large scores, Qwen3-VL prediction/state sentences and 2 s window clips.
2. **Original videos**: PhysTrace run directly on original IntPhys2 Possible / Impossible pairs (no generative model).

Deployed with GitHub Pages from the repository root.

## Layout
- `index.html` — the page (template + data assembled; do not edit by hand).
- `data.json` — section 1: scores, windows, sentences and media paths for every scene/model/sigma.
- `orig.json` — section 2: scores, windows, sentences, detected intervals and media paths for each Possible / Impossible pair.
- `media/<scene>/` — section 1 input clip, full reconstructions and 2 s window clips (mp4).
- `media/orig/<attribute>/` — section 2 Possible / Impossible videos and their lowest-window clips (mp4).
- `.nojekyll` — tells GitHub Pages to serve files as-is.
- `build/` — build code.
  - `build_data.py` — reads scoring results + reconstructions on the server, writes `data.json` and cuts the videos (needs ffmpeg). Server only.
  - `template.html` — page layout, styles and script. Data is injected at `/*DATA*/null`.
  - `build_orig.py` — reads a `figure8_picks` export (trials.csv, results.csv, video/) and writes `orig.json` + `media/orig/` (needs ffmpeg).
  - `assemble.py` — puts `data.json` and `orig.json` into the template and writes `index.html`.

## Rebuild
```bash
# 1) (server only) data + videos
WAN_T=4 COS_T=2 python3 build/build_data.py .
# 1b) original-video section from a figure8_picks export
python3 build/build_orig.py ~/Downloads/figure8_picks .
# 2) page -> ./index.html
python3 build/assemble.py .
# single self-contained file for quick sharing -> ../PhysTrace.io_inline.html
python3 build/assemble.py . --inline
```

## What to change
- Scenes and one-line descriptions: `SCENES` in `build/build_data.py` (section 1) and `build/build_orig.py` (section 2).
- Which seed-42 trial is shown: env `WAN_T` (default 4), `COS_T` (default 2).
- Sigmas: `SIGMAS` in `build/build_data.py`.
- Links, title, text: `build/template.html` (Code link → https://github.com/PhysTrace/PhysTrace).
