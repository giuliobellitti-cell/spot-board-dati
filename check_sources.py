"""Prova: le centraline e Open-Meteo rispondono da un server GitHub?"""
import re, json, time, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
T = str(int(time.time()))
SOURCES = {
 "Vedetta Marotta": "https://vedetta.org/image-client/marotta/meteo/dati_meteo.html",
 "Vedetta Senigallia": "https://vedetta.org/image-client/senigallia-marzocca/meteo/dati_meteo.html",
 "Vedetta Portonovo": "https://vedetta.org/image-client/portonovo-spiaggia/meteo/dati_meteo.html",
 "Vedetta Numana (Pratone)": "https://vedetta.org/image-client/numana/meteo/dati_meteo.html",
 "Vedetta Marina Palmense": "https://vedetta.org/image-client/marina-palmense/meteo/dati_meteo.html",
 "Soluzioni Meteo Numana": "https://stazioni5.soluzionimeteo.it/numana/plugins/steelSeries/ssMeteotemplate.php",
 "Meteo System Marina Dorica": "https://www.meteosystem.com/stazione/marinadorica/dati.php",
 "Windsurf Maniac Riccione": "https://www.windsurf-maniac.it/grub_meteo.php?151=ok&id=ok",
 "Wunderground IPESAR14": "https://www.wunderground.com/dashboard/pws/IPESAR14",
 "Wunderground IFANO17": "https://www.wunderground.com/dashboard/pws/IFANO17",
 "Ecowitt Bagni Venerucci": "https://www.ecowitt.net/home/share?authorize=UB1MKB&device_id=MDJsaVpjZ2JXZGErMzdtcjJqR2RsUT09",
 "Meteobridge MMM (immagine)": "https://content.meteobridge.com/cam/8ad92698194f285f962065f4002bb913/camplus.jpg",
 "Open-Meteo": "https://api.open-meteo.com/v1/forecast?latitude=43.477&longitude=13.645&hourly=wind_speed_10m&wind_speed_unit=kn&forecast_days=1&models=ecmwf_ifs025,icon_seamless,gfs_seamless,chmi_aladin_seamless,meteofrance_arome_france_hd,italia_meteo_arpae_icon_2i",
}
TIME_RE = re.compile(r"(\d{2}:\d{2}(?::\d{2})?\s+\d{2}/\d{2}/\d{2,4})|\"timeUTC\":\"[^\"]+\"|\"data\":\"[^\"]+\"|alle ore\s+\d{2}[.:]\d{2}")
for name, url in SOURCES.items():
    u = url + ("&" if "?" in url else "?") + "_t=" + T
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
        body = r.read()
        txt = body.decode("utf-8", "replace")
        m = TIME_RE.search(txt)
        print(f"OK   {name}: HTTP {r.status}, {len(body)} byte, orario trovato: {m.group(0) if m else '—'}")
    except Exception as e:
        print(f"ERR  {name}: {type(e).__name__}: {e}")
