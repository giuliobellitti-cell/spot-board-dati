"""Analisi: misure delle centraline contro la previsione del mattino.

Uso: python analyze.py [--days N]   -> stampa un rapporto in Markdown
"""
import csv, glob, json, math, os, sys
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome"); ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "stations.json"), encoding="utf-8"))
NAMES = {s["id"]: s["name"] for s in CFG["stations"]}; MODELS = CFG["models"]
SLOTS = [("Mattina", 0, 12), ("Pranzo", 12, 15), ("Pomeriggio", 15, 19), ("Sera", 19, 24)]

def tcrit(df):
    z = 1.959964
    if df < 1: return math.inf
    return z + (z**3 + z) / (4 * df) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * df**2) + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * df**3)

def stats(e):
    n = len(e)
    if not n: return None
    m = sum(e) / n; mae = sum(abs(x) for x in e) / n; rmse = math.sqrt(sum(x * x for x in e) / n)
    sd = math.sqrt(sum((x - m) ** 2 for x in e) / (n - 1)) if n > 1 else 0
    t = m / (sd / math.sqrt(n)) if n > 1 and sd > 0 else 0
    return dict(n=n, bias=m, mae=mae, rmse=rmse, t=t, sig=n >= 5 and abs(t) > tcrit(n - 1), within=sum(abs(x) <= 3 for x in e) / n)

def ang(a, b):
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d

def interp(arr, hf):
    h0 = int(math.floor(hf)); h1 = min(h0 + 1, 23); f = hf - h0
    a, b = arr[h0], arr[h1]
    if a is None: return None
    return a if b is None else a + (b - a) * f

def load(days):
    fc = {}
    for p in glob.glob(os.path.join(ROOT, "data", "fc", "*.json")):
        x = json.load(open(p, encoding="utf-8")); fc[x["date"]] = x
    since = datetime.now(ROME) - timedelta(days=days) if days else None
    pairs = []; seen = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "obs", "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if (r["station"], r["obs_time"]) in seen: continue   # stessa lettura salvata due volte
            seen.add((r["station"], r["obs_time"]))
            t = datetime.fromisoformat(r["obs_time"])
            if since and t < since: continue
            f = fc.get(t.strftime("%Y-%m-%d"))
            if not f or r["kn"] == "": continue
            st = f["stations"].get(r["station"])
            if not st: continue
            kn = float(r["kn"]); dd = float(r["dir_deg"]) if r["dir_deg"] not in ("", None) else None
            hf = t.hour + t.minute / 60
            for mod, a in st["models"].items():
                w = interp(a["w"], hf)
                if w is None: continue
                d = a["d"][int(round(hf)) % 24]
                pairs.append(dict(model=mod, st=r["station"], hour=t.hour, date=t.date(), key=(r["station"], r["obs_time"]),
                                  e=w - kn, de=ang(d, dd) if (d is not None and dd is not None and kn >= 4) else None))
    return fc, pairs

def f1(v): return "—" if v is None else f"{v:.1f}"
def sg(v): return "—" if v is None else f"{v:+.1f}"

def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else None
    fc, P = load(days)
    obs_keys = {p["key"] for p in P}
    print(f"# Verifica modelli — {'ultimi ' + str(days) + ' giorni' if days else 'tutto il periodo'}\n")
    print(f"Previsioni del mattino: {len(fc)} · misure confrontate: {len(obs_keys)} · giorni con misure: {len({p['date'] for p in P})}\n")
    if not P: print("Ancora nessun confronto disponibile."); return
    rows = []
    for mod, lab in MODELS.items():
        e = [p["e"] for p in P if p["model"] == mod]; s = stats(e)
        if not s: continue
        de = [p["de"] for p in P if p["model"] == mod and p["de"] is not None]
        rows.append((s["mae"], lab, s, sum(de) / len(de) if de else None, mod))
    rows.sort()
    print("## Classifica dei modelli\n\n| Modello | n | Errore medio (kn) | Bias (kn) | RMSE | Entro ±3 kn | Errore direzione |\n|---|---|---|---|---|---|---|")
    for _, lab, s, de, _m in rows:
        print(f"| {lab} | {s['n']} | {f1(s['mae'])} | {sg(s['bias'])}{' *' if s['sig'] else ''} | {f1(s['rmse'])} | {s['within']*100:.0f}% | {'—' if de is None else f'{de:.0f}°'} |")
    # confronto appaiato tra il migliore e gli altri (stesse misure)
    best = rows[0][4]; print(f"\n### Il migliore ({MODELS[best]}) è davvero migliore? Test appaiato sugli errori assoluti\n")
    bym = defaultdict(dict)
    for p in P: bym[p["model"]][p["key"]] = abs(p["e"])
    for _, lab, s, _, mod in rows[1:]:
        common = set(bym[best]) & set(bym[mod]); diff = [bym[mod][k] - bym[best][k] for k in common]; d = stats(diff)
        if d: print(f"- {lab}: sbaglia in media {d['bias']:+.2f} kn in più ({d['n']} misure in comune) → {'differenza significativa' if d['sig'] else 'differenza non significativa'}")
    print("\n## Centralina per centralina (bias in kn; * = significativo, p<0,05)\n")
    labs = [r[1] for r in rows]; mods = [r[4] for r in rows]
    print("| Centralina | " + " | ".join(labs) + " | Migliore |\n|---|" + "---|" * (len(labs) + 1))
    for sid in [s["id"] for s in CFG["stations"]]:
        cells, best_m = [], None
        for mod in mods:
            s = stats([p["e"] for p in P if p["model"] == mod and p["st"] == sid])
            cells.append("—" if not s else f"{sg(s['bias'])}{' *' if s['sig'] else ''} (±{f1(s['mae'])}, n{s['n']})")
            if s and s["n"] >= 3 and (best_m is None or s["mae"] < best_m[0]): best_m = (s["mae"], MODELS[mod])
        if any(c != "—" for c in cells): print(f"| {NAMES[sid]} | " + " | ".join(cells) + f" | {best_m[1] if best_m else '—'} |")
    print("\n## Per fascia oraria (errore medio in kn)\n")
    print("| Fascia | " + " | ".join(labs) + " |\n|---|" + "---|" * len(labs))
    for name, a, b in SLOTS:
        cells = []
        for mod in mods:
            s = stats([p["e"] for p in P if p["model"] == mod and a <= p["hour"] < b])
            cells.append("—" if not s else f"{f1(s['mae'])} (n{s['n']})")
        print(f"| {name} | " + " | ".join(cells) + " |")

if __name__ == "__main__":
    main()
