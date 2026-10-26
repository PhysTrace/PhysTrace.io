#!/usr/bin/env python3
"""Assemble the project page from template.html + <site_dir>/data.json.

  python3 assemble.py <site_dir>            -> <site_dir>/index.html (media referenced by relative path; deploy this folder)
  python3 assemble.py <site_dir> --inline   -> <site_dir>/../<name>_inline.html (single file, every mp4 embedded as data: URI)
"""
import base64, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2:
    sys.exit(__doc__)
SITE = os.path.abspath(sys.argv[1])
INLINE = "--inline" in sys.argv[2:]
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
data = json.load(open(os.path.join(SITE, "data.json"), encoding="utf-8"))


def inline(d):
    def uri(p):
        return "data:video/mp4;base64," + base64.b64encode(open(os.path.join(SITE, p), "rb").read()).decode()
    d = json.loads(json.dumps(d))
    for sc in d["scenes"]:
        sc["input"] = uri(sc["input"])
        for r in sc["runs"].values():
            r["video"] = uri(r["video"])
            r["clips"] = {k: uri(v) for k, v in r["clips"].items()}
    return d


def put(d, path):
    js = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    open(path, "w", encoding="utf-8").write(tpl.replace("/*DATA*/null", js))
    print(path, f"{os.path.getsize(path) / 1e6:.2f} MB")


if INLINE:
    put(inline(data), os.path.join(os.path.dirname(SITE), os.path.basename(SITE) + "_inline.html"))
else:
    put(data, os.path.join(SITE, "index.html"))
