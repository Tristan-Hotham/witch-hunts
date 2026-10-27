"""Step 2: annual series, panics, temperature tests, geography, people and outcomes.
Writes ../data/annual.csv, ../data/places.csv, ../data/parishes.csv,
../data/counties.csv, ../data/kde.geojson, ../data/results.json and
../work/site.json (compact data for the page).
Run: python3 02_analyse.py
"""
import json, os, math, collections
import numpy as np, pandas as pd
from scipy import stats
from pyproj import Transformer
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data"); WK = os.path.join(HERE, "..", "work")
os.makedirs(WK, exist_ok=True)
rng = np.random.default_rng(1736)
cs = pd.read_csv(os.path.join(D, "cases.csv"))
tc = pd.read_csv(os.path.join(D, "europe_temperature.csv")).set_index("year")
Y0, Y1 = 1563, 1736
PANICS = [("1590 to 1591", 1590, 1591, "North Berwick and the royal voyage"),
          ("1597", 1597, 1597, "The great hunt of 1597"),
          ("1628 to 1631", 1628, 1631, "The Lothians and the Borders"),
          ("1649 to 1650", 1649, 1650, "The Covenanters' hunt"),
          ("1661 to 1662", 1661, 1662, "The Restoration panic")]
ONSETS = [p[1] for p in PANICS]
PANIC_YEARS = sorted({y for p in PANICS for y in range(p[1], p[2] + 1)})
R = {}

# ---------------- annual series
dated = cs[cs.year.notna()].copy(); dated["year"] = dated.year.astype(int)
R["total"] = {"cases": int(len(cs)), "people": int(cs.people.sum()), "named": int(cs.named.sum()),
              "unnamed_people": int(cs[cs.named == 0].people.sum()), "unnamed_cases": int((cs.named == 0).sum()),
              "undated_cases": int(cs.year.isna().sum()), "undated_people": int(cs[cs.year.isna()].people.sum()),
              "first_year": int(dated.year.min()), "last_year": int(dated.year.max()),
              "before_1563_people": int(dated[dated.year < Y0].people.sum()),
              "unnamed_default3_cases": int(((cs.named == 0) & cs.name.astype(str).str.startswith("3 unnamed")).sum()),
              "start_year_differs": int(((cs.start_year != cs.year) & cs.start_year.notna()).sum())}
years = np.arange(Y0, Y1 + 1)
ann = dated.groupby("year").agg(people=("people", "sum"), cases=("case_ref", "size"), named=("named", "sum"))
ann = ann.reindex(years, fill_value=0)
ann_start = dated.assign(y=dated.start_year.astype(int)).groupby("y").people.sum().reindex(years, fill_value=0)
women = dated[dated.sex == "Female"].groupby("year").size().reindex(years, fill_value=0)
men = dated[dated.sex == "Male"].groupby("year").size().reindex(years, fill_value=0)
exe = dated[dated.outcome == "Executed"].groupby("year").size().reindex(years, fill_value=0)
T = tc.loc[Y0 - 10:Y1 + 10]
seasons = ["winter", "spring", "summer", "autumn", "annual"]
anom = {s: (T[s] - T.loc[Y0:Y1, s].mean()) for s in seasons}
hp = {s: (T[s] - T[s].rolling(31, center=True, min_periods=15).mean()) for s in seasons}  # year-to-year part
annual = pd.DataFrame({"year": years, "people": ann.people.values, "cases": ann.cases.values,
                       "people_by_start_year": ann_start.values, "women": women.values, "men": men.values,
                       "executed": exe.values, "panic": [int(y in PANIC_YEARS) for y in years]})
for s in seasons:
    annual[f"t_{s}"] = T.loc[years, s].values.round(3)
    annual[f"anom_{s}"] = anom[s].loc[years].values.round(3)
    annual[f"hp_{s}"] = hp[s].loc[years].values.round(3)
annual.to_csv(os.path.join(D, "annual.csv"), index=False)
in_win = int(annual.people.sum())
R["series"] = {"people_1563_1736": in_win, "years": len(years), "zero_years": int((annual.people == 0).sum()),
               "median_year": float(annual.people.median()), "mean_year": round(float(annual.people.mean()), 1),
               "peak_year": int(annual.people.idxmax() + Y0), "peak_people": int(annual.people.max()),
               "years_over_100": [int(y) for y in years[annual.people.values >= 100]],
               "panic_people": int(annual[annual.panic == 1].people.sum()), "panic_year_count": len(PANIC_YEARS),
               "panic_share": round(float(annual[annual.panic == 1].people.sum() / in_win), 4),
               "corr_case_vs_start_year": round(float(np.corrcoef(annual.people, annual.people_by_start_year)[0, 1]), 3)}
top = annual.sort_values("people", ascending=False).head(12)
R["series"]["top_years"] = [{"year": int(r.year), "people": int(r.people)} for r in top.itertuples()]
thr = annual.people.mean() + 2 * annual.people.std()
R["series"]["spike_threshold"] = round(float(thr), 1)
R["series"]["spike_years"] = [int(y) for y in years[annual.people.values > thr]]

# ---------------- panics: people, women, outcomes, geography
EDI = (55.9533, -3.1883)


def hav(lat, lon, la2, lo2):
    t = math.pi / 180
    h = np.sin((la2 - lat) * t / 2) ** 2 + np.cos(lat * t) * np.cos(la2 * t) * np.sin((lo2 - lon) * t / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))


dated["edi_km"] = hav(dated.lat, dated.lon, *EDI)


def summary(sub):
    nm = sub[sub.named == 1]
    sx = nm.sex.value_counts()
    known = nm[~nm.outcome.isin(["Not recorded", "No trial record"])]
    geo = nm[nm.lat.notna()]
    cty = nm.county.fillna("").replace("", np.nan).dropna().value_counts()
    return {"people": int(sub.people.sum()), "named": int(len(nm)), "women": int(sx.get("Female", 0)), "men": int(sx.get("Male", 0)),
            "women_share": round(float(sx.get("Female", 0) / max(1, sx.get("Female", 0) + sx.get("Male", 0))), 4),
            "outcome_known": int(len(known)), "executed": int((nm.outcome == "Executed").sum()),
            "executed_share_known": round(float((known.outcome == "Executed").mean()), 4) if len(known) else None,
            "tortured": int(nm.tortured.sum()), "pricked": int(nm.ordeal.fillna("").str.contains("Pricking").sum()),
            "geocoded": int(len(geo)), "within50_edinburgh": int((geo.edi_km <= 50).sum()),
            "within50_share": round(float((geo.edi_km <= 50).mean()), 4) if len(geo) else None,
            "median_km_edinburgh": round(float(geo.edi_km.median()), 1) if len(geo) else None,
            "top_counties": [{"county": k, "n": int(v)} for k, v in cty.head(5).items()],
            "counties_n": int(len(cty))}


R["panics"] = []
for lab, a, b, title in PANICS:
    sub = dated[(dated.year >= a) & (dated.year <= b)]
    s = summary(sub); s.update({"label": lab, "start": a, "end": b, "title": title,
                                "t_annual_onset": round(float(anom["annual"].loc[a]), 3),
                                "t_winter_onset": round(float(anom["winter"].loc[a]), 3),
                                "t_annual_prev": round(float(anom["annual"].loc[a - 1]), 3),
                                "hp_annual_onset": round(float(hp["annual"].loc[a]), 3),
                                "hp_annual_prev": round(float(hp["annual"].loc[a - 1]), 3)})
    # rank of onset-year annual temperature among 1563-1736 (1 = coldest)
    s["onset_cold_rank"] = int((T.loc[Y0:Y1, "annual"] < T.loc[a, "annual"]).sum() + 1)
    s["prev_cold_rank"] = int((T.loc[Y0:Y1, "annual"] < T.loc[a - 1, "annual"]).sum() + 1)
    R["panics"].append(s)
win = dated[(dated.year >= Y0) & (dated.year <= Y1)]
R["all"] = summary(win)
R["all_incl_undated"] = summary(cs.assign(edi_km=hav(cs.lat, cs.lon, *EDI)))
R["nonpanic"] = summary(win[~win.year.isin(PANIC_YEARS)])
R["panic_all"] = summary(win[win.year.isin(PANIC_YEARS)])

nm = cs[cs.named == 1]
oc = nm.outcome.value_counts()
R["outcomes"] = {k: int(v) for k, v in oc.items()}
R["outcomes_known"] = int(nm[~nm.outcome.isin(["Not recorded", "No trial record"])].shape[0])
R["executed"] = int(oc.get("Executed", 0))
R["executed_share_known"] = round(R["executed"] / R["outcomes_known"], 4)
R["execution_methods"] = {k: int(v) for k, v in nm[nm.execution_method.notna()].execution_method.value_counts().items()}
R["tortured"] = int(nm.tortured.sum())
tt = collections.Counter(t for s in nm.torture_types.dropna() for t in s.split("; "))
R["torture_types"] = dict(tt.most_common())
R["pricked"] = int(nm.ordeal.fillna("").str.contains("Pricking").sum())
R["marital"] = {k: int(v) for k, v in nm.marital.value_counts().items()}
ages = pd.to_numeric(nm.age, errors="coerce").dropna()
R["age"] = {"n": int(len(ages)), "median": float(ages.median()), "share_50plus": round(float((ages >= 50).mean()), 3)}
R["socio"] = {k: int(v) for k, v in nm.socio.value_counts().items()}
R["occupation_n"] = int(nm.occupation.notna().sum())
R["sex"] = {"female": int((nm.sex == "Female").sum()), "male": int((nm.sex == "Male").sum()), "unknown": int(nm.sex.isna().sum()),
            "women_share": round(float((nm.sex == "Female").sum() / ((nm.sex == "Female").sum() + (nm.sex == "Male").sum())), 4)}
# women share in panic vs other years: two-proportion test
pa, npn = R["panic_all"], R["nonpanic"]
tab = [[pa["women"], pa["men"]], [npn["women"], npn["men"]]]
R["women_panic_vs_other_p"] = float(stats.chi2_contingency(tab)[1])
# executed share in panic vs non-panic among known outcomes
R["exec_panic_vs_other"] = {"panic": pa["executed_share_known"], "other": npn["executed_share_known"]}

# ---------------- geography
geo = nm[nm.lat.notna()]
R["geo"] = {"geocoded": int(len(geo)), "named": int(len(nm)), "share": round(len(geo) / len(nm), 4),
            "places": int(geo.groupby(["residence", "lat", "lon"]).ngroups),
            "within50_edinburgh": int((hav(geo.lat, geo.lon, *EDI) <= 50).sum()),
            "within50_share": round(float((hav(geo.lat, geo.lon, *EDI) <= 50).mean()), 4),
            "north_of_tay": int((geo.lat > 56.45).sum()), "north_of_tay_share": round(float((geo.lat > 56.45).mean()), 4),
            "highlands_west_of_4_5_north_56_5": int(((geo.lat > 56.5) & (geo.lon < -4.5)).sum())}
cty = nm.county.dropna().value_counts()
cty.rename_axis("county").reset_index(name="named_accused").to_csv(os.path.join(D, "counties.csv"), index=False)
R["counties"] = [{"county": k, "n": int(v)} for k, v in cty.items()]
R["county_top3_share"] = round(float(cty.head(3).sum() / cty.sum()), 4)
pl = geo.groupby(["residence", "wd_residence", "lat", "lon"]).agg(
    accused=("case_ref", "size"), women=("sex", lambda s: int((s == "Female").sum())),
    executed=("outcome", lambda s: int((s == "Executed").sum())), first_year=("year", "min"), last_year=("year", "max"),
    county=("county", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else "")).reset_index()
pl = pl.sort_values("accused", ascending=False)
pl.to_csv(os.path.join(D, "places.csv"), index=False)
R["top_places"] = [{"place": r.residence, "n": int(r.accused), "county": r.county} for r in pl.head(12).itertuples()]
par = nm[nm.parish.notna()].groupby("parish").agg(accused=("case_ref", "size"), county=("county", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else ""),
                                                   lat=("lat", "median"), lon=("lon", "median"),
                                                   first_year=("year", "min"), last_year=("year", "max")).reset_index()
par = par.sort_values("accused", ascending=False)
par.round(5).to_csv(os.path.join(D, "parishes.csv"), index=False)
R["parishes"] = {"with_parish": int(nm.parish.notna().sum()), "n_parishes": int(len(par)),
                 "top": [{"parish": r.parish, "n": int(r.accused), "county": r.county} for r in par.head(12).itertuples()],
                 "parishes_10plus": int((par.accused >= 10).sum())}

# kernel density (British National Grid, Gaussian, 8 km bandwidth) -> contour polygons
tr = Transformer.from_crs(4326, 27700, always_xy=True); inv = Transformer.from_crs(27700, 4326, always_xy=True)
gx = np.arange(0, 480001, 2000); gy = np.arange(520000, 1220001, 2000)
GX, GY = np.meshgrid(gx, gy)
BW = 8000


def kde(sub):
    x, y = tr.transform(sub.lon.values, sub.lat.values)
    Z = np.zeros_like(GX, dtype=float)
    for xi, yi in zip(x, y):
        ix = slice(max(0, int((xi - 4 * BW) / 2000)), int((xi + 4 * BW) / 2000) + 1)
        iy = slice(max(0, int((yi - 520000 - 4 * BW) / 2000)), int((yi - 520000 + 4 * BW) / 2000) + 1)
        Z[iy, ix] += np.exp(-((GX[iy, ix] - xi) ** 2 + (GY[iy, ix] - yi) ** 2) / (2 * BW * BW))
    return Z / (2 * math.pi * BW * BW) * 1e6 * 100  # accused per 100 km2


features = []
KDE = {}
sets = [("all", geo)] + [(p[0], geo[(geo.year >= p[1]) & (geo.year <= p[2])]) for p in PANICS]
for name, sub in sets:
    Z = kde(sub); KDE[name] = Z
    levels = [0.05, 0.15, 0.4, 1.0, 2.5]
    cs_ = plt.contourf(GX, GY, Z, levels=levels + [Z.max() + 1])
    for li, segs in enumerate(cs_.allsegs):
        polys = []
        for seg in segs:
            if len(seg) < 4: continue
            lo, la = inv.transform(seg[::2, 0], seg[::2, 1])
            polys.append([[round(a, 4), round(b, 4)] for a, b in zip(lo, la)])
        if polys:
            features.append({"type": "Feature", "properties": {"set": name, "level": levels[li]},
                             "geometry": {"type": "MultiPolygon", "coordinates": [[p] for p in polys]}})
    plt.close("all")
json.dump({"type": "FeatureCollection", "features": features}, open(os.path.join(D, "kde.geojson"), "w"), separators=(",", ":"))
np.savez_compressed(os.path.join(WK, "kde.npz"), gx=gx, gy=gy, **{k.replace(" ", "_"): v for k, v in KDE.items()})
R["kde"] = {"bandwidth_km": BW / 1000, "levels_per_100km2": [0.05, 0.15, 0.4, 1.0, 2.5], "grid_km": 2,
            "peak_all": round(float(KDE["all"].max()), 2)}

# ---------------- temperature tests
y = annual.people.values.astype(float)
ly = np.log1p(y)


def circ_p(x, yv, obs, minshift=10, fn=None):
    """Two-sided p from circular shifts of x against y (keeps each series' autocorrelation)."""
    n = len(x); vals = []
    for k in range(minshift, n - minshift + 1):
        vals.append(fn(np.roll(x, k), yv))
    vals = np.array(vals)
    return float((np.abs(vals) >= abs(obs) - 1e-12).mean()), len(vals)


sp = lambda a, b: stats.spearmanr(a, b)[0]
corr = []
for s in seasons:
    for lag in [0, 1, 2]:
        for kind, src in [("anomaly", anom), ("year_to_year", hp)]:
            x = src[s].loc[years - lag].values
            r = sp(x, y)
            p, nsh = circ_p(x, y, r, fn=sp)
            corr.append({"season": s, "lag": lag, "kind": kind, "spearman": round(float(r), 3), "p_circular": round(p, 3)})
R["corr"] = corr
R["corr_n_shifts"] = nsh
R["corr_min_p"] = min(c["p_circular"] for c in corr)
R["corr_n_tests"] = len(corr)
R["corr_n_p05"] = sum(c["p_circular"] < 0.05 for c in corr)
# headline: annual, lag 0 and 1
cget = lambda s, l, k: next(c for c in corr if c["season"] == s and c["lag"] == l and c["kind"] == k)
R["corr_head"] = {"annual_lag0": cget("annual", 0, "anomaly"), "annual_lag1": cget("annual", 1, "anomaly"),
                  "winter_lag0": cget("winter", 0, "anomaly"), "summer_lag1": cget("summer", 1, "anomaly"),
                  "annual_hp_lag0": cget("annual", 0, "year_to_year"), "annual_hp_lag1": cget("annual", 1, "year_to_year")}
# decadal
dec = annual.assign(d=(annual.year // 10) * 10).groupby("d").agg(people=("people", "sum"), t=("t_annual", "mean"), w=("t_winter", "mean"))
dec = dec.loc[1570:1720]
rd = stats.pearsonr(dec.t, np.log1p(dec.people))[0]
pdc, _ = circ_p(dec.t.values, np.log1p(dec.people.values), rd, minshift=2, fn=lambda a, b: stats.pearsonr(a, b)[0])
rdw = stats.pearsonr(dec.w, np.log1p(dec.people))[0]
pdw, _ = circ_p(dec.w.values, np.log1p(dec.people.values), rdw, minshift=2, fn=lambda a, b: stats.pearsonr(a, b)[0])


def phase_surrogates(x, n):
    """Surrogates with the same power spectrum (so the same autocorrelation) as x, random phases."""
    x = np.asarray(x, float); m = x.mean(); F = np.fft.rfft(x - m); out = np.empty((n, len(x)))
    for i in range(n):
        ph = rng.uniform(0, 2 * np.pi, len(F)); ph[0] = 0
        if len(x) % 2 == 0: ph[-1] = 0
        out[i] = np.fft.irfft(np.abs(F) * np.exp(1j * ph), len(x)) + m
    return out


def decadal_test(col, d0, d1, nsim=10000):
    yrs = np.arange(d0, d1 + 10)
    x = T.loc[yrs, col].values
    ppl = np.log1p(annual.set_index("year").loc[yrs, "people"].values.reshape(-1, 10).sum(1))
    obs = stats.pearsonr(x.reshape(-1, 10).mean(1), ppl)[0]
    sur = phase_surrogates(x, nsim).reshape(nsim, -1, 10).mean(2)
    rs = np.array([np.corrcoef(s_, ppl)[0, 1] for s_ in sur])
    return round(float(obs), 3), round(float((np.abs(rs) >= abs(obs)).mean()), 4)


ra, pa_ = decadal_test("annual", 1570, 1720); rw, pw_ = decadal_test("winter", 1570, 1720)
ra2, pa2 = decadal_test("annual", 1570, 1690); rw2, pw2 = decadal_test("winter", 1570, 1690)
# annual-scale check with phase surrogates too
sur = phase_surrogates(anom["annual"].loc[years].values, 5000)
r0 = stats.spearmanr(anom["annual"].loc[years].values, y)[0]
R["annual_phase_p"] = round(float(np.mean([abs(stats.spearmanr(s_, y)[0]) >= abs(r0) for s_ in sur])), 3)
R["decadal"] = {"phase_r_annual": ra, "phase_p_annual": pa_, "phase_r_winter": rw, "phase_p_winter": pw_,
                "pre1700_r_annual": ra2, "pre1700_p_annual": pa2, "pre1700_r_winter": rw2, "pre1700_p_winter": pw2,
                "n": int(len(dec)), "r_annual": round(float(rd), 3), "p_annual": round(pdc, 3), "r_winter": round(float(rdw), 3), "p_winter": round(pdw, 3),
                "rows": [{"decade": int(d), "people": int(r.people), "t_annual": round(float(r.t), 3)} for d, r in dec.iterrows()]}
# temperature level in panic years vs other years
pm = annual.panic == 1
R["panic_vs_other_temp"] = {s: {"panic": round(float(annual.loc[pm, f"anom_{s}"].mean()), 3), "other": round(float(annual.loc[~pm, f"anom_{s}"].mean()), 3)} for s in seasons}

# superposed epoch analysis around the five onsets
LAGS = list(range(-5, 6))
elig = np.arange(Y0 + 5, Y1 - 5 + 1)


def composite(onsets, s, src):
    return np.array([[src[s].loc[o + l] for l in LAGS] for o in onsets]).mean(0)


sea = {}
NSIM = 20000
for s in seasons:
    for kind, src in [("anomaly", anom), ("year_to_year", hp)]:
        comp = composite(ONSETS, s, src)
        sims = np.array([composite(rng.choice(elig, 5, replace=False), s, src) for _ in range(NSIM)])
        i0, im1 = LAGS.index(0), LAGS.index(-1)
        win_obs = comp[LAGS.index(-2):i0 + 1].mean(); win_sim = sims[:, LAGS.index(-2):i0 + 1].mean(1)
        sea[f"{s}|{kind}"] = {"comp": [round(float(v), 3) for v in comp],
                              "lo": [round(float(v), 3) for v in np.percentile(sims, 2.5, axis=0)],
                              "hi": [round(float(v), 3) for v in np.percentile(sims, 97.5, axis=0)],
                              "p_cold_lag0": round(float((sims[:, i0] <= comp[i0]).mean()), 3),
                              "p_cold_lag_1": round(float((sims[:, im1] <= comp[im1]).mean()), 3),
                              "p_cold_window": round(float((win_sim <= win_obs).mean()), 3),
                              "window_mean": round(float(win_obs), 3)}
# family-wise check: how often do five random onsets give a p-value at least this small somewhere among all the composites tried?
SIMS = {}
rng2 = np.random.default_rng(99)
draws = [rng2.choice(elig, 5, replace=False) for _ in range(4000)]
minp_sim = np.ones(len(draws))
for s in seasons:
    for kind, src in [("anomaly", anom), ("year_to_year", hp)]:
        M = np.array([composite(d_, s, src) for d_ in draws])
        stats3 = np.column_stack([M[:, LAGS.index(0)], M[:, LAGS.index(-1)], M[:, LAGS.index(-2):LAGS.index(0) + 1].mean(1)])
        for j in range(3):
            col = stats3[:, j]; srt = np.sort(col)
            pj = np.searchsorted(srt, col, side="right") / len(col)
            minp_sim = np.minimum(minp_sim, pj)
R["sea_familywise_p"] = round(float((minp_sim <= min(min(v["p_cold_lag0"], v["p_cold_lag_1"], v["p_cold_window"]) for v in sea.values())).mean()), 3)
R["sea_n_tests"] = len(sea) * 3
R["onsets_colder_than_mean"] = {"onset_year": sum(anom["annual"].loc[o] < 0 for o in ONSETS),
                                "year_before": sum(anom["annual"].loc[o - 1] < 0 for o in ONSETS),
                                "summer_before": sum(anom["summer"].loc[o - 1] < 0 for o in ONSETS),
                                "winter_onset": sum(anom["winter"].loc[o] < 0 for o in ONSETS)}
R["onsets_colder_than_mean"] = {k: int(v) for k, v in R["onsets_colder_than_mean"].items()}
R["sea_summer_prev"] = [{"onset": o, "summer_prev": round(float(anom["summer"].loc[o - 1]), 3)} for o in ONSETS]
R["sea"] = {"lags": LAGS, "onsets": ONSETS, "n_sim": NSIM, "eligible_years": [int(elig[0]), int(elig[-1])], "res": sea}
R["sea_min_p"] = min(min(v["p_cold_lag0"], v["p_cold_lag_1"], v["p_cold_window"]) for v in sea.values())
# power: how cold would the five onsets need to be (lag 0, annual anomaly) to reach p<0.05?
sims0 = np.array([anom["annual"].loc[rng.choice(elig, 5, replace=False)].mean() for _ in range(NSIM)])
R["sea_power"] = {"needed_annual_lag0": round(float(np.percentile(sims0, 5)), 3), "sd_annual": round(float(anom["annual"].loc[Y0:Y1].std()), 3),
                  "sd_winter": round(float(anom["winter"].loc[Y0:Y1].std()), 3)}
# coldest years of the window and whether panics fall in or after them
cold10 = T.loc[Y0:Y1, "annual"].nsmallest(17).index  # coldest decile (17 of 174)
R["cold_decile"] = {"years": sorted(int(v) for v in cold10),
                    "panic_onsets_in_or_after": [o for o in ONSETS if o in cold10 or (o - 1) in cold10],
                    "people_in_cold_years": int(annual.set_index("year").loc[list(cold10), "people"].sum()),
                    "expected_share": round(17 / len(years), 4)}
R["cold_decile"]["share_people"] = round(R["cold_decile"]["people_in_cold_years"] / in_win, 4)
# permutation test for the coldest-decile share: shift accusations circularly
obs = R["cold_decile"]["share_people"]
mask = np.isin(years, cold10)
shares = np.array([y[np.roll(mask, k)].sum() / y.sum() for k in range(10, len(years) - 9)])
R["cold_decile"]["p_circular"] = round(float((shares >= obs).mean()), 3)
R["climate_window"] = {"mean_annual": round(float(T.loc[Y0:Y1, "annual"].mean()), 3),
                       "mean_annual_1901_2000": round(float(tc.loc[1901:2000, "annual"].mean()), 3),
                       "coldest_year": int(T.loc[Y0:Y1, "annual"].idxmin()), "coldest_value": round(float(T.loc[Y0:Y1, "annual"].min()), 3),
                       "coldest_winter": int(T.loc[Y0:Y1, "winter"].idxmin())}

# Pendle (from the Wikipedia article text, not from the Survey)
R["pendle"] = {"year": 1612, "accused": 12, "executed": 10, "lat": 53.869, "lon": -2.3,
               "coord_source": "Pendle Hill, location map in the Wikipedia article 'Pendle witches'", "source": "Wikipedia, 'Pendle witches' (text as downloaded October 2026)",
               "scotland_1612": int(annual.set_index("year").loc[1612, "people"]),
               "scotland_1610_1614": int(annual.set_index("year").loc[1610:1614, "people"].sum())}

# headline values used in the text (all derived from the blocks above)
sa = sea["summer|anomaly"]; aa = sea["annual|anomaly"]; wa = sea["winter|anomaly"]
R["head"] = {"outcomes_unknown": R["outcomes"].get("Not recorded", 0) + R["outcomes"].get("No trial record", 0),
             "summer_prev_mean": sa["comp"][LAGS.index(-1)], "summer_prev_p": sa["p_cold_lag_1"],
             "summer_window_mean": sa["window_mean"], "summer_window_p": sa["p_cold_window"],
             "annual_onset_mean": aa["comp"][LAGS.index(0)], "annual_onset_p": aa["p_cold_lag0"],
             "annual_prev_mean": aa["comp"][LAGS.index(-1)], "annual_prev_p": aa["p_cold_lag_1"],
             "winter_onset_mean": wa["comp"][LAGS.index(0)], "winter_onset_p": wa["p_cold_lag0"],
             "band_annual_lag0": [aa["lo"][LAGS.index(0)], aa["hi"][LAGS.index(0)]],
             "pendle_lat": 53.869, "pendle_lon": -2.3,
             "unnamed_share_people": round(R["total"]["unnamed_people"] / R["total"]["people"], 4),
             "places_mapped": R["geo"]["places"],
             "people_1643": int(annual.set_index("year").loc[1643, "people"]),
             "people_1644": int(annual.set_index("year").loc[1644, "people"]),
             "people_1658_1659": int(annual.set_index("year").loc[1658:1659, "people"].sum()),
             "people_after_1662": int(annual[annual.year > 1662].people.sum()),
             "people_after_1662_share": round(float(annual[annual.year > 1662].people.sum() / in_win), 4)}

R["meta"] = {"window": [Y0, Y1], "panics_defined": [p[0] for p in PANICS],
             "doi": "10.5281/zenodo.23677167", "slug": "witch-hunts"}
json.dump(R, open(os.path.join(D, "results.json"), "w"), indent=1)

# ---------------- compact page data
pts = nm[nm.lat.notna() & nm.year.notna()]
site = {"R": R,
        "years": years.tolist(), "people": annual.people.tolist(), "women": annual.women.tolist(), "men": annual.men.tolist(),
        "exe": annual.executed.tolist(),
        "t": {s: [round(float(v), 2) for v in anom[s].loc[years]] for s in seasons},
        "hp": {s: [round(float(v), 2) for v in hp[s].loc[years]] for s in seasons},
        # point list: lat, lon, year, sex(0 f,1 m,2 ?), outcome code, name, place, case ref
        "oc": ["Executed", "Acquitted or released", "Fled or declared fugitive", "Other punishment", "Guilty, sentence not recorded", "Action dropped", "Not recorded", "No trial record"],
        "pts": [[round(r.lat, 4), round(r.lon, 4), int(r.year), 0 if r.sex == "Female" else 1 if r.sex == "Male" else 2,
                 ["Executed", "Acquitted or released", "Fled or declared fugitive", "Other punishment", "Guilty, sentence not recorded", "Action dropped", "Not recorded", "No trial record"].index(r.outcome),
                 r.name, r.residence, r.case_ref.split("/", 1)[1], int(r.tortured)] for r in pts.itertuples()]}
json.dump(site, open(os.path.join(WK, "site.json"), "w"), separators=(",", ":"))
print(json.dumps({k: R[k] for k in ["decadal", "sea_familywise_p", "sea_summer_prev", "annual_phase_p", "corr_n_p05", "corr_min_p"]}, indent=0)[:3000])
for p in R["panics"]: print(p["label"], p["people"], p["women_share"], p["executed"], p["within50_share"], p["t_annual_onset"], p["onset_cold_rank"], p["prev_cold_rank"], p["top_counties"][:3])
for k, v in sea.items(): print(k, v["comp"][4:7], v["p_cold_lag0"], v["p_cold_lag_1"], v["p_cold_window"])
