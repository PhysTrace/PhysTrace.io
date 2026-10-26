#!/usr/bin/env python3
"""Build orig.json + video clips for the "original videos" section of the PhysTrace page.

These examples run PhysTrace directly on the original IntPhys2 videos (no generative model, no noising).
Each scene is a Possible / Impossible pair of the same setup.

  python3 build/build_orig.py <picks_dir> <site_dir> [gt_csv]

<picks_dir> holds trials.csv, results.csv and video/<attribute>_<group>_{Possible,Impossible}.mp4
(the figure8_picks export). [gt_csv] is optional: IntPhys2 GT with columns group, onset_sec, end_sec
(build/intphys2_gt.csv, from PhysTrace/PhysTrace IntPhys2Timing/); its violation interval is drawn under the Impossible video. Outputs <site_dir>/orig.json and <site_dir>/media/orig/<attribute>/*.mp4.
Needs ffmpeg.
"""
import csv, json, os, subprocess, sys

csv.field_size_limit(10 ** 9)
if len(sys.argv) not in (3, 4):
    sys.exit(__doc__)
PICKS, OUT = sys.argv[1], sys.argv[2]
# GT rows keyed by (attribute, group), the same pair the clip file names carry.
GT = {}
if len(sys.argv) == 4:
    GT = {(r["attribute"], r["group"]): r for r in csv.DictReader(open(sys.argv[3], encoding="utf-8")) if r.get("onset_sec")}


def gt_for_clip(path, bad_name, good_name):
    """Look up the GT row from a clip file name: <attribute>_<group>_{Possible,Impossible}.mp4."""
    stem = os.path.basename(path)[:-4]
    attr, rest = stem.split("_", 1)
    group = rest.rsplit("_", 1)[0]
    row = GT.get((attr, group))
    if row is None:
        print("NO GT for clip", os.path.basename(path))
        return None
    # The GT row must describe the same videos the scores were computed on.
    assert row["impossible_video"] == bad_name and row["possible_video"] == good_name, f"GT video mismatch for {stem}"
    return [float(row["onset_sec"]), float(row["end_sec"])]

# Scene order and one-line descriptions (what happens in the Impossible video).
SCENES = [
    ("continuity", "Ball between two balloons",
     "Two hot-air balloons drift past each other. The green ball goes missing from its basket and shows up in the other balloon's basket."),
    ("immutability", "Ball along the clothesline",
     "A green ball rolls along the clothesline rail behind the towel and comes out the other side orange."),
    ("permanence", "Ball in the balloon basket",
     "A green ball sits in a hot-air balloon basket. The view moves away and back, and the basket is empty."),
    ("solidity", "Cube into the tub",
     "A wooden board lies in a white tub. A red cube drops into the tub and sinks through the board instead of resting on it."),
]
NPICK = 3  # lowest windows shown as clips per video; the window centred on the GT is added when GT is given

ENC = ["-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "30", "-movflags", "+faststart"]


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def first(s):
    v = json.loads(s) if s else [""]
    return v[0] if v else ""


trials = {}
for t in csv.DictReader(open(os.path.join(PICKS, "trials.csv"), encoding="utf-8")):
    j = json.loads(t["trial_json"])
    trials[j["pair"]["attribute"]] = j

by_video = {}
for r in csv.DictReader(open(os.path.join(PICKS, "results.csv"), encoding="utf-8")):
    by_video.setdefault(os.path.basename(r["video"])[:-4], []).append(r)

params = next(iter(trials.values()))["params"]
data = {"window_seconds": params["window_seconds"], "hop_seconds": params["hop_seconds"],
        "clip_model": params["clip_model"], "mllm": params["mllm_backend"], "scenes": []}

for attr, title, desc in SCENES:
    j = trials[attr]
    pair, group = j["pair"], j["group"]
    os.makedirs(os.path.join(OUT, "media", "orig", attr), exist_ok=True)
    imp_clip = os.path.join(PICKS, "video", f"{attr}_{group}_Impossible.mp4")
    gt = gt_for_clip(imp_clip, pair["bad_name"], pair["good_name"]) if GT else None
    scene = {"attribute": attr, "title": title, "desc": desc, "group": group, "gt": gt, "sides": {}}
    for side, label, hname in (("possible", "Possible", pair["good_name"]), ("impossible", "Impossible", pair["bad_name"])):
        rows = sorted(by_video[hname], key=lambda r: int(r["index"]))
        meta = json.loads(rows[0]["metadata_json"])
        summ = j["summary"]["good" if side == "possible" else "bad"]
        wins = [{"start": float(r["start_sec"]), "end": float(r["end_sec"]), "score": float(r["prediction_score"]),
                 "state": first(r["state"]), "prediction": first(r["prediction"]), "trusted": r["trusted"] == "True"}
                for r in rows]
        order = sorted(range(len(wins)), key=lambda i: wins[i]["score"])
        cands = sorted(order[:NPICK])
        lowest = order[0]
        picks = list(cands)
        if scene["gt"]:
            g0, g1 = scene["gt"]
            inside = [i for i, w in enumerate(wins) if w["start"] < g1 and w["end"] > g0]
            if inside and not any(i in cands for i in inside):
                picks.append(min(inside, key=lambda i: abs((wins[i]["start"] + wins[i]["end"]) / 2 - (g0 + g1) / 2)))
        picks = sorted(set(picks))
        src = os.path.join(PICKS, "video", f"{attr}_{group}_{label}.mp4")
        full = f"media/orig/{attr}/{side}.mp4"
        ffmpeg(["-i", src, "-vf", "scale=256:256", "-r", "30", *ENC, os.path.join(OUT, full)])
        clips = {}
        for i in picks:
            s, e = wins[i]["start"], min(wins[i]["end"], meta["duration_sec"])
            p = f"media/orig/{attr}/{side}_w{i + 1:02d}.mp4"
            ffmpeg(["-ss", f"{s:.3f}", "-i", src, "-t", f"{e - s:.3f}", "-vf", "scale=256:256", "-r", "30", *ENC, os.path.join(OUT, p)])
            clips[str(i)] = p
        scene["duration"] = meta["duration_sec"]
        scene["sides"][side] = {
            "video": full, "windows": wins, "lowest": lowest, "candidates": cands, "picks": picks, "clips": clips,
            "min_score": summ["min_score"], "untrusted": summ["untrusted"],
            "intervals": [[iv["start_sec"], iv["end_sec"]] for iv in summ["intervals"]],
        }
        print(attr, side, "min", round(summ["min_score"], 3), "lowest W%d" % (lowest + 1), "picks", [c + 1 for c in picks])
    scene["trial"] = j["picked_from"]
    data["scenes"].append(scene)

json.dump(data, open(os.path.join(OUT, "orig.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("done", OUT)
