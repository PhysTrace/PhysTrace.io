#!/usr/bin/env python3
"""Build data.json + video clips for the PhysTrace qualitative-results page (v1).

Scenes: 4 IntPhys2 Impossible clips. Models: Wan2.1-1.3B (seed-42 trial WAN_T), Cosmos-Predict2-2B 93f
(seed-42 trial COS_T). Sigma 0.8. Hit rule = tables.py band rule, k=3, strict edges, GT = videotrace_v2 demo GT.

Outputs under OUT/: data.json, media/<cid>/input.mp4, media/<cid>/<model>_s05.mp4 (full recon),
media/<cid>/<model>_s05_w04.mp4 (2 s window clips).
"""
import csv, glob, json, os, subprocess, sys

sys.path.insert(0, "/nas5/users/kyunghun/workspace/world-model/recon_scoring/score")
from tables import lowest, scores_of, overlaps, candidates  # noqa: E402

W = "/nas5/users/kyunghun/workspace/world-model"
OUT = sys.argv[1]
WAN_T, COS_T = int(os.environ.get("WAN_T", 4)), int(os.environ.get("COS_T", 2))
GT_CSV = f"{W}/PHYSTRACE/code/videotrace_v2/demo/gt/intphys2_gt.csv"
GT = {r["group"]: r for r in csv.DictReader(open(GT_CSV)) if r["onset_sec"]}

SCENES = [
    ("25-1", "continuity", "Ball on the wire track",
     "A red ball rolls along a wire track. It is missing from the back wire where it should be, then shows up on the front rail."),
    ("imm-109-1", "immutability", "Hot-air balloon basket",
     "The basket of a hot-air balloon leaves the view. When it comes back, the orange object it carried has turned green."),
    ("perm-229-1", "permanence", "Ball behind the cloth",
     "A gold ball rolls along a rail behind a hanging cloth and never comes out from under it."),
    ("sol-1-1", "solidity", "Crate on the pedestal",
     "A falling crate lands flat on the pedestal, passing through the brick instead of tilting on it."),
]
MODELS = [("wan", "Wan2.1-1.3B", f"results_wan_wohint_s42_t{WAN_T}", "demo_sweep/wan"),
          ("cosmos", "Cosmos-Predict2-2B", f"results_cosmos93_wohint_s42_t{COS_T}", "demo_sweep_cosmos93/cosmos20")]
SIGMAS = [0.8]
NPICK = 4


def load(resdir, cid, sg):
    best = None
    for f in glob.glob(f"{W}/recon_scoring/score/{resdir}/scores_b*.jsonl"):
        for line in open(f):
            r = json.loads(line)
            if r["clip"] == cid and r["sigma"] == sg and r.get("side", "bad") == "bad":
                if best is None or r["scored_at"] > best["scored_at"]:
                    best = r
    return best


def picks(wins, gt, lo_idx, cand_idx):
    """Up to 4 windows: an early context window, the last window before the GT, the lowest window, one inside the GT."""
    n = len(wins)
    mid = lambda i: (wins[i]["start"] + wins[i]["end"]) / 2
    inside = [i for i in range(1, n) if wins[i]["start"] < gt[1] and wins[i]["end"] > gt[0]]
    before = [i for i in range(1, n) if wins[i]["end"] <= gt[0] + 0.5]
    chosen = [1]
    if before: chosen.append(before[-1])
    chosen.append(lo_idx)
    if inside: chosen.append(min(inside, key=lambda i: abs(mid(i) - (gt[0] + gt[1]) / 2)))
    for i in cand_idx + list(range(n)):
        if len(set(chosen)) >= NPICK: break
        chosen.append(i)
    return sorted(set(chosen))[:NPICK]


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


ENC = ["-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "30", "-movflags", "+faststart"]

data = {"trials": {"wan": WAN_T, "cosmos": COS_T}, "sigmas": SIGMAS,
        "models": [[m, name] for m, name, _, _ in MODELS], "scenes": []}
for cid, attr, title, desc in SCENES:
    os.makedirs(f"{OUT}/media/{cid}", exist_ok=True)
    first = load(MODELS[0][2], cid, SIGMAS[0])
    g = GT[first["group"]]
    gt = [float(g["onset_sec"]), float(g["end_sec"])]
    inp = f"{W}/recon_scoring/demo_sweep/original/{cid}.mp4"
    ffmpeg(["-i", inp, "-vf", "scale=256:256", "-r", "30", *ENC, f"{OUT}/media/{cid}/input.mp4"])
    scene = {"id": cid, "attribute": attr, "title": title, "desc": desc, "group": first["group"], "gt": gt,
             "duration": float(g["duration_sec"]), "input": f"media/{cid}/input.mp4", "runs": {}}
    for m, name, resdir, recdir in MODELS:
        for sg in SIGMAS:
            r = load(resdir, cid, sg)
            if r is None:
                print("MISSING", m, cid, sg); continue
            sc = scores_of(r)
            band = lowest(sc, "band", 3)
            cands = candidates(sc, 3)
            lo_idx = min(cands, key=lambda c: (c[3], c[1]))[0]
            hit = overlaps(band[0], band[1], gt, False)
            wins = r["windows"]
            pk = picks(wins, gt, lo_idx, [c[0] for c in cands])
            tag = f"{m}_s{str(sg).replace('.', '')}"
            src = f"{W}/recon_scoring/{recdir}/{cid}/sigma_{sg:.2f}.mp4"
            ffmpeg(["-i", src, *ENC, f"{OUT}/media/{cid}/{tag}.mp4"])
            clips = {}
            for i in pk:
                s, e = wins[i]["start"], wins[i]["end"]
                p = f"media/{cid}/{tag}_w{i + 1:02d}.mp4"
                ffmpeg(["-ss", f"{s:.3f}", "-i", src, "-t", f"{e - s:.3f}", *ENC, f"{OUT}/{p}"])
                clips[i] = p
            scene["runs"][tag] = {
                "model": m, "sigma": sg, "video": f"media/{cid}/{tag}.mp4", "hit": bool(hit),
                "band": [band[0], band[1]], "lowest": lo_idx, "candidates": [c[0] for c in cands],
                "windows": [{"start": w["start"], "end": w["end"], "score": w["score"],
                             "prediction": (w.get("prediction") or [""])[0], "state": (w.get("state") or [""])[0]}
                            for w in wins],
                "picks": pk, "clips": {str(k): v for k, v in clips.items()}, "scored_at": r["scored_at"],
                "source": f"{resdir}"}
            print(cid, tag, "hit" if hit else "miss", "picks", pk, "band", [round(band[0], 2), round(band[1], 2)], "gt", gt)
    data["scenes"].append(scene)

json.dump(data, open(f"{OUT}/data.json", "w"), indent=1, ensure_ascii=False)
print("done", OUT)
