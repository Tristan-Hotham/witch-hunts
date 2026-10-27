"""Step 3: build ../index.html (and README.md) from page_template.html and prose.html.

Every number in the text is a placeholder like {{series.peak_people|int}} filled
from ../data/results.json; the compact page data (../work/site.json), the density
contours (../data/kde.geojson) and the small coastline (../data/coast_ne10m.geojson)
are embedded as `const D = ...`.
Formats: int, pct0, pct1, f1, f2, f3, sg2 (signed), words, ord, raw.
Run: python3 03_build_page.py
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct0": return f"{v * 100:.0f}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    if f == "f3": return f"{v:.3f}"
    if f == "sg2": return ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.2f}"
    if f == "words":
        w = "zero one two three four five six seven eight nine ten eleven twelve".split()
        return w[int(v)] if int(v) < len(w) else f"{int(v):,}"
    if f == "ord":
        n = int(v); suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suf}"
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


def fill(t):
    return re.sub(r"\{\{(.+?)\}\}", sub, t)


if __name__ == "__main__":
    site = json.load(open(os.path.join(ROOT, "work", "site.json")))
    site["kde"] = json.load(open(os.path.join(ROOT, "data", "kde.geojson")))
    site["coast"] = json.load(open(os.path.join(ROOT, "data", "coast_ne10m.geojson")))
    t = open(os.path.join(HERE, "page_template.html")).read().replace("<!--PROSE-->", open(os.path.join(HERE, "prose.html")).read())
    t = fill(t)
    t = t.replace("/*DATA*/", "const D = " + json.dumps(site, separators=(",", ":"), ensure_ascii=False) + ";")
    open(os.path.join(ROOT, "index.html"), "w").write(t)
    print("index.html", len(t.encode()) // 1024, "KB")
    rt = os.path.join(HERE, "README_template.md")
    if os.path.exists(rt):
        open(os.path.join(ROOT, "README.md"), "w").write(fill(open(rt).read()))
        print("README.md written")
