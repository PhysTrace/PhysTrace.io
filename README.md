# PhysTrace project page

Static project page for **PhysTrace**, in two sections:

1. **IntPhys2-Timing Evaluation**: PhysTrace run directly on original IntPhys2 Possible / Impossible pairs (no generative model).
2. **Diffusion Reconstructions**: IntPhys2 Impossible clips noised to σ 0.8 and reconstructed by Wan2.1-1.3B and
   Cosmos-Predict2-2B, with per-window PE-AV-Large scores, Qwen3-VL prediction/state sentences and 2 s window clips.

Deployed with GitHub Pages from the repository root. Every video the page plays is under `media/`; nothing outside this folder is needed.

## Layout
- `index.html` — the page (template + data assembled; do not edit by hand).
- `1_timing_eval.json` — section 1: scores, windows, sentences, GT intervals and media paths for each Possible / Impossible pair.
- `2_diffusion_recon.json` — section 2: scores, windows, sentences and media paths for every scene/model/sigma.
- `media/1_timing_eval/<attribute>/` — section 1 Possible / Impossible videos and their window clips (mp4).
- `media/2_diffusion_recon/<scene>/` — section 2 original Impossible / Possible videos, full reconstructions and 2 s window clips (mp4).
- `media/figure/` — Figure 1 and the method-overview frame.
- `.nojekyll` — tells GitHub Pages to serve files as-is.
- `build/` — build code.
  - `template.html` — page layout, styles and script. Data is injected at `/*DATA*/null` and `/*ORIG*/null`.
  - `build_1_timing_eval.py` — reads a picks export (trials.csv, results.csv, video/) and writes `1_timing_eval.json` +
    `media/1_timing_eval/` (needs ffmpeg). The GT violation is looked up in the GT file by each clip's file name
    (`<attribute>_<group>_Impossible.mp4`), and the video hashes are checked.
  - `add_1_timing_eval_clips.py` — cuts any missing window clip the page shows from the videos already in `media/1_timing_eval/`.
  - `build_2_diffusion_recon.py` — reads scoring results + reconstructions on the server, writes `2_diffusion_recon.json`
    and cuts the videos (needs ffmpeg). Server only.
  - `add_2_diffusion_recon_clips.py` — picks the three windows each section-2 card row shows (`shown`) and cuts any
    missing clip from the full reconstructions already in `media/2_diffusion_recon/`.
  - `intphys2_gt.csv` — IntPhys2-Timing GT, copied from `PhysTrace/PhysTrace` `IntPhys2Timing/intphys2_gt.csv`.
  - `assemble.py` — puts both JSON files into the template and writes `index.html`.

## Rebuild
```bash
# 1) section 1 from a picks export (trials.csv, results.csv and
#    video/<attribute>_<group>_{Possible,Impossible}.mp4 copied or linked from the IntPhys2 videos)
python3 build/build_1_timing_eval.py <picks_dir> . build/intphys2_gt.csv
# 2) (server only) section 2 data + videos
WAN_T=4 COS_T=2 python3 build/build_2_diffusion_recon.py .
python3 build/add_2_diffusion_recon_clips.py .
# 3) page -> ./index.html
python3 build/assemble.py .
# single self-contained file for quick sharing -> ../PhysTrace.io-new_inline.html
python3 build/assemble.py . --inline
```

## What to change
- Scenes and one-line descriptions: `SCENES` in `build/build_1_timing_eval.py` and `build/build_2_diffusion_recon.py`.
- Which seed-42 trial is shown in section 2: env `WAN_T` (default 4), `COS_T` (default 2).
- Sigmas: `SIGMAS` in `build/build_2_diffusion_recon.py`.
- Links, title, text: `build/template.html` (Paper and Code buttons are "coming soon" for now).
