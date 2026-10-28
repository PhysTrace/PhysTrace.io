#!/usr/bin/env python3
"""Add the IntPhys2-section window clips the page shows to an already built site, without the figure8_picks export.

For every Possible / Impossible pair in <site_dir>/1_timing_eval.json the page shows three windows of the Impossible video,
the first one, its lowest-scoring one and the one two after it, and the same three windows of the Possible twin.
This cuts any of them that has no clip yet out of the site's own 256 px video (media/1_timing_eval/<attribute>/<side>.mp4)
and records them in 1_timing_eval.json as `shown`.

  python3 build/add_1_timing_eval_clips.py <site_dir>

Needs ffmpeg. build_1_timing_eval.py cuts the same windows from the export when the site is rebuilt from scratch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

# Same encoding as build_1_timing_eval.py, so added clips match the existing ones.
ENCODE = ['-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', '30', '-movflags', '+faststart']
FRAME_RATE = '30'


def shown_windows(windows: list[dict], lowest: int) -> list[int]:
    """The first window, the lowest one and the one two after it; nearer ones stand in when the video ends sooner."""
    later = [index for index in (lowest + 2, lowest + 1, lowest - 1) if 0 < index < len(windows) and index != lowest]
    return sorted({0, lowest, later[0]})


def cut_clip(source: Path, start: float, end: float, target: Path) -> None:
    """Cut [start, end) seconds of `source` into `target`."""
    command = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', str(source), '-t', f'{end - start:.3f}',
               '-r', FRAME_RATE, *ENCODE, str(target)]
    subprocess.run(command, check=True)


def add_clips(site: Path) -> None:
    """Cut the missing clips of every scene and side, then rewrite 1_timing_eval.json."""
    data_path = site / '1_timing_eval.json'
    data = json.loads(data_path.read_text(encoding='utf-8'))
    for scene in data['scenes']:
        impossible = scene['sides']['impossible']
        shown = shown_windows(impossible['windows'], impossible['lowest'])
        for side_name, side in scene['sides'].items():
            side['shown'] = shown
            source = site / side['video']
            if not source.is_file():
                raise FileNotFoundError(f'{source} is missing; rebuild the site with build_1_timing_eval.py first')
            for index in side['shown']:
                if str(index) in side['clips']:
                    continue
                window = side['windows'][index]
                relative = f'media/1_timing_eval/{scene["attribute"]}/{side_name}_w{index + 1:02d}.mp4'
                cut_clip(source, window['start'], min(window['end'], scene['duration']), site / relative)
                side['clips'][str(index)] = relative
                print('cut', relative)
            print(scene['attribute'], side_name, 'shown', [index + 1 for index in side['shown']])
    data_path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')


def main() -> None:
    """Parse the site directory and add its clips."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('site_dir', type=Path)
    add_clips(parser.parse_args().site_dir)


if __name__ == '__main__':
    main()
