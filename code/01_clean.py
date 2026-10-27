"""Step 1: read the Survey of Scottish Witchcraft tables, the Wikidata residence
coordinates and the European seasonal temperature reconstruction, and write
clean CSV files to ../data/.

The Survey's text export has no header row, so the schema is inferred: the
column names below are my reconstruction of the Survey's database fields, and I
checked each column I use against its contents (counts and typical values, e.g.
"Female"/"Male" for Sex, "Guilty"/"Execution" for Verdict/Sentence, "Burn" or
"Strangle & Burn" for Executionmethod). Columns I do not use may be misnamed. From the WDB_Ref_Parish table I use only its
reference (column 0) and parish name (column 3), which are unambiguous.

Inputs (read in place, not copied):
  /home/claude/hist/_data2/witches/WDB_*.txt
  /home/claude/hist/_data2/wikidata/witches.json
  /home/claude/hist/_data2/luterbacher_europe_seasonal.txt
Run: python3 01_clean.py
"""
import csv, json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
SRC = os.environ.get("SSW_DIR", "/home/claude/hist/_data2/witches")
WD = os.environ.get("WD_FILE", "/home/claude/hist/_data2/wikidata/witches.json")
CLIM = os.environ.get("CLIM_FILE", "/home/claude/hist/_data2/luterbacher_europe_seasonal.txt")

ACCUSED = ("AccusedRef AccusedSystemId AccusedID FirstName LastName M_Firstname M_Surname Alias Patronymic DesTitle "
           "Sex Age Age_estcareer Age_estchild Res_settlement Res_parish Res_presbytery Res_county Res_burgh "
           "Res_NGR_Letters Res_NGR_Easting Res_NGR_Northing Ethnic_origin MaritalStatus SocioecStatus Occupation Notes "
           "Createdby Createdate Lastupdatedby Lastupdatedon").split()
# first 17 Case fields (the rest are characterisation flags I do not use)
CASE = ("CaseRef CaseId CaseSystemId NamedIndividual AccusedRef CaseStart_date CaseStart_date_as_date Case_date "
        "Case_date_as_date Age_at_case CaseCommonName Commission Complaint Correspondence Chronicle Other Suspects_text").split()
TRIAL = ("Trialref TrialId TrialSystemId CaseRef TrialType Trial_settlement Trial_parish Trial_presbytery Trial_county "
         "Trial_burgh Trial_NGR_Letters Trial_NGR_Easting Trial_NGR_Northing Watching WatchingDate WatchingDate_as_date "
         "Arrest ArrestDate ArrestDate_as_date Fled FledDate FledDate_as_date ActionDropped Actiondropdate "
         "Actiondropdate_as_date Actiondroppedby Actionbody Confrontingsuspects PretrialNotes ProcessType TrialDate "
         "TrialDate_as_date TrialPlace Female_accusers Male_accusers High_status Defence Verdict Sentence Cjtorder "
         "Cjtdate Cjtdate_as_date Circuit Circuitname Localwithcrep Noreftocentral TrialNotes Execution Executionmethod "
         "ExecutionDate ExecutionDate_as_date ExecutionPlace Exec_settlement Exec_parish Exec_presbytery Exec_county "
         "Exec_burgh Exec_NGR_Letters Exec_NGR_Easting Exec_NGR_Northing PostTrialNotes Createdby Createdate "
         "Lastupdatedby Lastupdatedon").split()
TORTURE = "TortureRef TortureSystemId TortureID Trialref Tortureexists Torturedate Torturedate_as_date Torturetype".split()
# Ordeal follows the same pattern as Torture (checked against the values: "Pricking", "Searching" ...)
ORDEAL = "OrdealRef OrdealSystemId OrdealID Trialref Ordealexists Ordealdate Ordealdate_as_date Ordealtype".split()


def table(name, cols, ncol):
    rows = list(csv.reader(open(os.path.join(SRC, name), encoding="utf-8", newline="")))
    assert all(len(r) == ncol for r in rows), name
    return [dict(zip(cols, r)) for r in rows]


def year(s):
    m = re.findall(r"(\d{4})", s or "")
    return int(m[-1]) if m else None


A = table("WDB_Accused.txt", ACCUSED, 31)
C = table("WDB_Case.txt", CASE, 111)
T = table("WDB_Trial.txt", TRIAL, 65)
TO = table("WDB_Torture.txt", TORTURE, 12)
OR = table("WDB_Ordeal.txt", ORDEAL + ["Createdby", "Createdate", "Lastupdatedby", "Lastupdatedon"], 12)
P = {r[0]: r[3] for r in csv.reader(open(os.path.join(SRC, "WDB_Ref_Parish.txt"), encoding="utf-8", newline=""))}

# ---- Wikidata residence coordinates (CC0), join on the Survey accused reference
W = {}
for w in json.load(open(WD)):
    if w["sswid"] in W and W[w["sswid"]].get("rc"):
        continue
    W[w["sswid"]] = w


def pt(s):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", s or "")
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)


# ---- trial outcomes, torture and ordeal per case
tri_by_case = collections.defaultdict(list)
for t in T:
    tri_by_case[t["CaseRef"]].append(t)
trial_case = {t["Trialref"]: t["CaseRef"] for t in T}
tortured = collections.defaultdict(set)
for r in TO:
    if r["Trialref"] in trial_case:
        tortured[trial_case[r["Trialref"]]].add(r["Torturetype"] or "Unspecified")
ordeal = collections.defaultdict(set)
for r in OR:
    if r["Trialref"] in trial_case:
        ordeal[trial_case[r["Trialref"]]].add(r["Ordealtype"] or "Unspecified")


def outcome(ts):
    """Executed if any trial records an execution (flag, sentence or method).
    Otherwise the most serious recorded result, else unknown."""
    if any(t["Execution"] == "1" or t["Sentence"] == "Execution" or t["Executionmethod"] for t in ts):
        return "Executed"
    sent = [t["Sentence"] for t in ts if t["Sentence"]]
    verd = [t["Verdict"] for t in ts if t["Verdict"]]
    for s in ["Banishment", "Excommunicated", "Branded", "Public Humiliation", "Prison", "Hang"]:
        if s in sent:
            return "Other punishment"
    if "Declared Fugitive" in sent or "Put to the horn" in sent or any(t["Fled"] == "1" for t in ts):
        return "Fled or declared fugitive"
    if "Released" in sent or any(v in ("Not Guilty", "Not Proven") for v in verd):
        return "Acquitted or released"
    if any(v in ("Guilty", "Half Guilty") for v in verd):
        return "Guilty, sentence not recorded"
    if any(t["ActionDropped"] == "1" for t in ts):
        return "Action dropped"
    return "Not recorded"


acc = {a["AccusedRef"]: a for a in A}
cases = []
for c in C:
    named = c["NamedIndividual"] == "-1"
    y = year(c["Case_date"]) or year(c["CaseStart_date"])
    ys = year(c["CaseStart_date"]) or y
    n = 1 if named else int(c["Suspects_text"] or 0)
    ts = tri_by_case.get(c["CaseRef"], [])
    a = acc.get(c["AccusedRef"], {}) if named else {}
    w = W.get(c["AccusedRef"], {}) if named else {}
    lat, lon = pt(w.get("rc"))
    cases.append({
        "case_ref": c["CaseRef"], "accused_ref": c["AccusedRef"] if named else "",
        "named": int(named), "people": n, "year": y, "start_year": ys,
        "case_date": c["Case_date"], "case_start_date": c["CaseStart_date"],
        "name": (a.get("FirstName", "") + " " + a.get("LastName", "")).strip() if named else c["CaseCommonName"],
        "sex": a.get("Sex", ""), "age": a.get("Age", ""), "marital": a.get("MaritalStatus", ""),
        "socio": a.get("SocioecStatus", ""), "occupation": a.get("Occupation", ""),
        "settlement": a.get("Res_settlement", ""), "parish": P.get(a.get("Res_parish", ""), ""),
        "parish_ref": a.get("Res_parish", ""), "presbytery": a.get("Res_presbytery", ""), "county": a.get("Res_county", ""),
        "wd_item": w.get("p", ""), "wd_residence": w.get("res", ""), "residence": w.get("resLabel", ""),
        "lat": lat, "lon": lon,
        "trials": len(ts), "outcome": outcome(ts) if ts else "No trial record",
        "execution_method": next((t["Executionmethod"] for t in ts if t["Executionmethod"]), ""),
        "tortured": int(bool(tortured.get(c["CaseRef"]))), "torture_types": "; ".join(sorted(tortured.get(c["CaseRef"], []))),
        "ordeal": "; ".join(sorted(ordeal.get(c["CaseRef"], []))),
        "survey_url": "https://witches.hca.ed.ac.uk/case/" + c["CaseRef"],
    })

cols = list(cases[0].keys())
with open(os.path.join(OUT, "cases.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, cols); wr.writeheader(); wr.writerows(cases)
print("cases.csv", len(cases), "cases,", sum(c["people"] for c in cases), "people")

# ---- climate
rows = []
on = False
for line in open(CLIM, encoding="latin-1"):
    p = line.split()
    if p[:2] == ["Year", "DJF"]:
        on = True; continue
    if on and len(p) == 6 and p[0].isdigit():
        rows.append(dict(zip(["year", "winter", "spring", "summer", "autumn", "annual"], [int(p[0])] + [float(x) for x in p[1:]])))
with open(os.path.join(OUT, "europe_temperature.csv"), "w", newline="") as f:
    wr = csv.DictWriter(f, list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
print("europe_temperature.csv", len(rows), rows[0]["year"], rows[-1]["year"])
