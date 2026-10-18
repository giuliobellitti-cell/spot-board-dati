# Spot Board – dati vento

Archivio automatico per confrontare le previsioni dei modelli con il vento misurato dalle centraline.

- **Ogni ora dalle 7 alle 21** (ora italiana) GitHub Actions legge le centraline elencate in `stations.json`
  e aggiunge le misure in `data/obs/AAAA-MM.csv`.
- **Ogni mattina, al primo giro dopo le 8**, salva la previsione oraria di ECMWF, AROME, ICON, ALADIN, GFS
  e ICON-2I (Open-Meteo) per ogni centralina in `data/fc/AAAA-MM-GG.json`: è la "previsione del mattino".
- `python analyze.py [--days N]` confronta ogni misura con la previsione del mattino per quell'ora e stampa
  classifica dei modelli, bias per centralina (test t, p<0,05) ed errori per fascia oraria.

Le misure più vecchie di 70 minuti vengono scartate. La direzione si confronta solo con almeno 4 nodi.
Le mede IRBIM (Fano, Senigallia, Portonovo, Porto Recanati) si leggono dal Grafana pubblico del CNR-IRBIM. Wunderground, Ecowitt e la webcam di MMM non sono leggibili da qui e restano nel pulsante Aggiorna dello Spot Board.

## Dati del mare delle mede IRBIM

Ogni giro orario salva anche, in `data/mare/AAAA-MM.csv`, per le mede IRBIM:
temperatura dell'aria (`air_c`), umidità (`rh_pct`), pressione (`bp_hpa`), temperatura dell'acqua (`water_c`),
altezza significativa e massima dell'onda (`hs_m`, `hmax_m`), periodo di picco e periodo medio (`tp_s`, `tm_s`)
e direzione di provenienza dell'onda (`wave_dir_deg`). Ogni gruppo ha il suo orario di misura
(`meteo_time`, `water_time`, `wave_time`); i valori più vecchi di 3 ore restano vuoti.
Onde: solo Fano e Portonovo (l'ondametro di Senigallia è fermo dal 2023, Porto Recanati non lo ha).
Acqua: Fano, Portonovo e Senigallia (sonda a 5 m).
