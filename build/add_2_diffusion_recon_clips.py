#!/usr/bin/env python3
"""Add the section-2 window clips the page shows to an already built site, without the scoring results.

For every scene and model run in <site_dir>/2_diffusion_recon.json the page shows three windows: the first window the
detection counts (W2, since W1 is excluded), the lowest one and the one two after it. This cuts any of them that has no
clip yet out of the site's own full reconstruction (media/2_diffusion_recon/<scene>/<run>.mp4) and records them in
2_diffusion_recon.json as `shown`.

  python3 build/add_2_diffusion_recon_clips.py <site_dir>

Needs ffmpeg. build_2_diffusion_recon.py cuts the same windows from the original reconstructions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

# Same encoding as build_2_diffusion_recon.py, so added clips match the existing ones.
ENCODE = ['-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', '30', '-movflags', '+faststart']
FIRST_COUNTED = 1  # the detection skips the first window
SHOWN_COUNT = 3


def shown_windows(window_count: int, lowest: int) -> list[int]:
    """The first counted window, the lowest one and the one two after it; nearer ones fill in near the ends."""
    shown = {FIRST_COUNTED, lowest}
    for index in (lowest + 2, lowest + 1, lowest - 1, lowest + 3, lowest - 2):
        if len(shown) == SHOWN_COUNT:
            break
        if FIRST_COUNTED <= index < window_count:
            shown.add(index)
    return sorted(shown)


def cut_clip(source: Path, start: float, end: float, target: Path) -> None:
    """Cut [start, end) seconds of `source` into `target`."""
    command = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', str(source), '-t', f'{end - start:.3f}',
               *ENCODE, str(target)]
    subprocess.run(command, check=True)


def add_clips(site: Path) -> None:
    """Cut the missing clips of every run, then rewrite 2_diffusion_recon.json."""
    data_path = site / '2_diffusion_recon.json'
    data = json.loads(data_path.read_text(encoding='utf-8'))
    for scene in data['scenes']:
        for tag, run in scene['runs'].items():
            run['shown'] = shown_windows(len(run['windows']), run['lowest'])
            source = site / run['video']
            if not source.is_file():
                raise FileNotFoundError(f'{source} is missing; rebuild the site with build_2_diffusion_recon.py first')
            for index in run['shown']:
                if str(index) in run['clips']:
                    continue
                window = run['windows'][index]
                relative = f'media/2_diffusion_recon/{scene["id"]}/{tag}_w{index + 1:02d}.mp4'
                cut_clip(source, window['start'], window['end'], site / relative)
                run['clips'][str(index)] = relative
                print('cut', relative)
            print(scene['id'], tag, 'shown', [index + 1 for index in run['shown']])
    data_path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')


def main() -> None:
    """Parse the site directory and add its clips."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('site_dir', type=Path)
    add_clips(parser.parse_args().site_dir)


if __name__ == '__main__':
    main()
