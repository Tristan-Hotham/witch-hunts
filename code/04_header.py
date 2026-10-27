"""Step 4: render ../header.png (1200x630 social card) with Playwright Chromium.

Fonts: pass a folder of TTFs as FONT_DIR (Fraunces, Source Serif 4, IBM Plex
Mono from github.com/google/fonts); otherwise the system serif is used.
Run: FONT_DIR=/path/to/fonts python3 04_header.py
"""
import os, json, math
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
S = json.load(open(os.path.join(ROOT, "work", "site.json"))); R = S["R"]; FD = os.environ.get("FONT_DIR", "")
coast = json.load(open(os.path.join(ROOT, "data", "coast_ne10m.geojson")))
B = dict(w=-7.6, e=-0.7, s=54.6, n=60.9); kx = math.cos(math.radians(57))
H = 590; W = H * (B["e"] - B["w"]) * kx / (B["n"] - B["s"])
px = lambda lo, la: ((lo - B["w"]) * kx / ((B["e"] - B["w"]) * kx) * W, (B["n"] - la) / (B["n"] - B["s"]) * H)
land = ""
for f in coast["features"]:
    g = f["geometry"]; polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for pl in polys:
        for ring in pl:
            if len(ring) > 3: land += "M" + "L".join(f"{px(*c)[0]:.1f} {px(*c)[1]:.1f}" for c in ring) + "Z"
cnt = {}
for p in S["pts"]:
    k = (p[0], p[1]); cnt[k] = cnt.get(k, 0) + 1
dots = "".join(f'<circle cx="{px(lo, la)[0]:.1f}" cy="{px(lo, la)[1]:.1f}" r="{1 + math.sqrt(n) * 1.15:.2f}"/>' for (la, lo), n in cnt.items())
ppl = S["people"]; mx = max(ppl); bw = 520 / len(ppl)
panic = lambda y: any(p["start"] <= y <= p["end"] for p in R["panics"])
bars = "".join(f'<rect x="{i * bw:.2f}" y="{70 - v / mx * 70:.1f}" width="{max(1, bw * .8):.2f}" height="{v / mx * 70:.1f}" fill="{"#E0664F" if panic(1563 + i) else "#5B6873"}"/>' for i, v in enumerate(ppl) if v)
ff = ""
if FD:
    ff = "".join(f"@font-face{{font-family:'{n}';src:url('file://{FD}/{f}');font-weight:{w};}}" for n, f, w in [
        ("Fraunces", "Fraunces[SOFT,WONK,opsz,wght].ttf", "100 900"), ("Source Serif 4", "SourceSerif4[opsz,wght].ttf", "200 900"),
        ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"), ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500")])
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
body{{margin:0;width:1200px;height:630px;background:#151B21;color:#E5E8EA;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}}
.k{{position:absolute;left:70px;top:70px;font:500 15px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#9AA4AD;display:flex;gap:12px;align-items:center}}
.k b{{background:#E0664F;color:#151B21;padding:7px 9px;font-weight:500}}
h1{{position:absolute;left:66px;top:112px;margin:0;font:900 104px/.88 Fraunces,Georgia,serif;letter-spacing:-.02em;font-variation-settings:"SOFT" 50}}
h1 i{{font-style:normal;color:#86B6DE}} h1 em{{font-style:normal;color:#E0664F}}
p{{position:absolute;left:70px;top:330px;width:540px;margin:0;font-size:25px;line-height:1.36;color:#D5DADE}}
.tl{{position:absolute;left:70px;top:470px}}
.f{{position:absolute;left:70px;bottom:36px;font:400 14px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#7F8A94}}
.map{{position:absolute;right:50px;top:20px}}
</style></head><body>
<div class="k"><b>Data study</b><span>History × climate · Scotland</span></div>
<h1><i>Cold</i> years,<br><em>witch</em> years?</h1>
<p>{R['total']['people']:,} people accused of witchcraft, 1563 to 1736. Did the panics follow the cold?</p>
<svg class="tl" width="520" height="80"><g>{bars}</g><line x1="0" x2="520" y1="70.5" y2="70.5" stroke="#3A4652"/></svg>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<svg class="map" width="{W:.0f}" height="{H}" viewBox="0 0 {W:.0f} {H}"><path d="{land}" fill="#1F2932" stroke="#33404B" stroke-width=".8"/><g fill="#E0664F" fill-opacity=".38" stroke="#F08C76" stroke-width=".6" stroke-opacity=".8">{dots}</g></svg>
</body></html>"""
tmp = os.path.join(ROOT, "work", "header.html"); open(tmp, "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + os.path.abspath(tmp)); pg.wait_for_timeout(600)
    pg.screenshot(path=os.path.join(ROOT, "header.png")); b.close()
os.remove(tmp)
print("header.png written")
