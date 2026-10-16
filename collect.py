"""Raccolta dati per lo Spot Board: misure delle centraline (ogni ora) e
previsione del mattino di Open-Meteo (una volta al giorno, dopo le 8).

Uso: python collect.py            -> fa quello che serve all'ora attuale
     python collect.py --force-fc -> rifà comunque la previsione di oggi
"""
import csv, json, math, os, re, sys, time, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "stations.json"), encoding="utf-8"))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
DIRS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
HOUR_FROM, HOUR_TO = 7, 21          # ore locali in cui si raccolgono le misure
FC_FROM_HOUR, FC_UNTIL_HOUR = 8, 12 # finestra per la previsione del mattino
MAX_AGE_MIN = 70                    # misure più vecchie vengono scartate
KMH = 1.852

def get(url, tries=3):
    sep = "&" if "?" in url else "?"
    for k in range(tries):
        try:
            u = url + sep + "_t=" + str(int(time.time()))
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            err = e; time.sleep(3 * (k + 1))
    raise err

def deg_of(d16):
    d16 = (d16 or "").upper().replace("O", "W")
    return DIRS.index(d16) * 22.5 if d16 in DIRS else None

def d16_of(deg):
    return None if deg is None else DIRS[int(round((deg % 360) / 22.5)) % 16]

def local(y, mo, d, h, mi, s=0):
    return datetime(y, mo, d, h, mi, s, tzinfo=ROME)

def read_vedetta(txt):
    m = re.search(r"(\d\d):(\d\d):(\d\d)\s+(\d\d)/(\d\d)/(\d{4})", txt)
    k = re.search(r"Vento Attuale:\s*([\d.]+)\s*(kts|km/h)?", txt, re.I)
    d = re.search(r"Direzione:\s*([A-Z]+)", txt, re.I)
    g = re.search(r"Raffica MAX OGGI:\s*([\d.]+)", txt, re.I)
    if not (m and k): return None
    f = KMH if (k.group(2) or "kts").lower() == "km/h" else 1
    return dict(t=local(int(m[6]), int(m[5]), int(m[4]), int(m[1]), int(m[2]), int(m[3])),
                kn=float(k[1]) / f, gust=None, gmax=float(g[1]) / f if g else None, dir=d[1].upper().replace("O", "W") if d else None)

def read_soluzionimeteo(txt):
    j = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    if str(j.get("SensorContactLost")) == "1": return None
    y, mo, d, h, mi, s = [int(x) for x in str(j["timeUTC"]).split(",")]
    f = {"kts": 1, "m/s": 1 / 1.944}.get(j.get("windunit"), KMH)
    return dict(t=datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc).astimezone(ROME), kn=float(j["wspeed"]) / f,
                gust=float(j["wgust"]) / f if j.get("wgust") not in (None, "") else None,
                gmax=float(j["wgustTM"]) / f if j.get("wgustTM") not in (None, "") else None, dir=d16_of(float(j["bearing"])))

def read_windsurfmaniac(txt):
    j = json.loads(txt[txt.index("["): txt.rindex("]") + 1])[0]
    m = re.search(r"(\d\d):(\d\d):(\d\d)\s+(\d\d)/(\d\d)/(\d{4})", j.get("data", ""))
    if not m: return None
    f = 1 if j.get("unita_misura") == "nodi" else KMH
    return dict(t=local(int(m[6]), int(m[5]), int(m[4]), int(m[1]), int(m[2]), int(m[3])), kn=float(j["velocita"]) / f,
                gust=None, gmax=None, dir=str(j.get("direzione") or "").upper().replace("O", "W") or None)

def read_meteosystem(html):
    if re.search(r"OFFLINE", html, re.I): return None
    txt = re.sub(r"&nbsp;|&#160;", " ", re.sub(r"<[^>]+>", " ", html)); txt = re.sub(r"&[a-z]+;", "", txt); txt = re.sub(r"\s+", " ", txt)
    m = re.search(r"aggiornati il (\d\d)/(\d\d)/(\d\d) alle ore (\d\d)[.:](\d\d)", txt)
    v = re.search(r"VENTO.*?Velocit\w*\s+([\d.]+)\s*(kts|km/h)\s+([\d.]+)\s*(?:kts|km/h)?\s*-?\s*([\d.]+)?", txt, re.I)
    d = re.search(r"Direzione\s+da\s+([A-Z]{1,3})", txt)
    if not (m and v): return None
    f = KMH if v[2].lower() == "km/h" else 1
    return dict(t=local(2000 + int(m[3]), int(m[2]), int(m[1]), int(m[4]), int(m[5])), kn=float(v[1]) / f,
                gust=float(v[3]) / f if v[3] else None, gmax=float(v[4]) / f if v[4] else None, dir=d[1].replace("O", "W") if d else None)

READERS = {"vedetta": read_vedetta, "soluzionimeteo": read_soluzionimeteo, "windsurfmaniac": read_windsurfmaniac, "meteosystem": read_meteosystem}

def r1(v): return None if v is None else round(v, 1)

def collect_obs(now):
    path = os.path.join(ROOT, "data", "obs", now.strftime("%Y-%m") + ".csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    rows, notes = [], []
    for st in CFG["stations"]:
        try:
            o = READERS[st["src"]](get(st["url"]))
        except Exception as e:
            notes.append(f"{st['id']}: errore {type(e).__name__}"); continue
        if not o:
            notes.append(f"{st['id']}: nessun dato (offline?)"); continue
        age = (now - o["t"]).total_seconds() / 60
        if age > MAX_AGE_MIN or age < -10:
            notes.append(f"{st['id']}: lettura vecchia ({o['t']:%d/%m %H:%M})"); continue
        rows.append([now.isoformat(timespec="minutes"), st["id"], o["t"].isoformat(timespec="minutes"),
                     r1(o["kn"]), r1(o["gust"]), r1(o["gmax"]), deg_of(o["dir"]), o["dir"] or ""])
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new: w.writerow(["run", "station", "obs_time", "kn", "gust", "gmax_today", "dir_deg", "dir"])
        w.writerows(rows)
    print(f"Misure: {len(rows)} salvate in {os.path.relpath(path, ROOT)}")
    for n in notes: print("  -", n)

def collect_fc(now, force=False):
    date = now.strftime("%Y-%m-%d")
    path = os.path.join(ROOT, "data", "fc", date + ".json")
    if os.path.exists(path) and not force:
        print("Previsione del mattino già salvata:", os.path.relpath(path, ROOT)); return
    sts = CFG["stations"]; models = list(CFG["models"])
    url = ("https://api.open-meteo.com/v1/forecast?latitude=" + ",".join(f"{s['fc'][0]:.3f}" for s in sts)
           + "&longitude=" + ",".join(f"{s['fc'][1]:.3f}" for s in sts)
           + "&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m&wind_speed_unit=kn&timezone=Europe%2FRome"
           + f"&start_date={date}&end_date={date}&models=" + ",".join(models))
    data = json.loads(get(url))
    if isinstance(data, dict): data = [data]
    out = {"date": date, "issued": now.isoformat(timespec="minutes"), "source": "Open-Meteo", "hours": list(range(24)),
           "models": CFG["models"], "stations": {}}
    for st, x in zip(sts, data):
        H = x["hourly"]; m = {}
        for mod in models:
            w = H.get("wind_speed_10m_" + mod)
            if not w or all(v is None for v in w): continue
            g = H.get("wind_gusts_10m_" + mod) or [None] * 24; d = H.get("wind_direction_10m_" + mod) or [None] * 24
            m[mod] = {"w": [r1(v) for v in w], "g": [r1(v) for v in g], "d": [None if v is None else int(round(v)) for v in d]}
        out["stations"][st["id"]] = {"point": st["fc"], "models": m}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), separators=(",", ":"))
    print("Previsione del mattino salvata:", os.path.relpath(path, ROOT))

def main():
    now = datetime.now(ROME)
    force_fc = "--force-fc" in sys.argv
    if FC_FROM_HOUR <= now.hour < FC_UNTIL_HOUR or force_fc:
        try: collect_fc(now, force_fc)
        except Exception as e: print("Previsione non salvata:", type(e).__name__, e)
    if HOUR_FROM <= now.hour <= HOUR_TO or "--force-obs" in sys.argv:
        collect_obs(now)
    else:
        print(f"Ore {now:%H:%M}: fuori dalla fascia {HOUR_FROM}-{HOUR_TO}, nessuna misura.")

if __name__ == "__main__":
    main()
