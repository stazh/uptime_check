# Uptime Monitor

Dieses Projekt prüft regelmäßig die Erreichbarkeit der Seite
<https://www.zentraleserien-hybridesuche.zh.ch> und stellt die Ergebnisse
über GitHub Pages bereit. Die ursprüngliche Node.js-Variante wurde
entfernt, sodass nur noch das Python-Skript `src/monitor.py` zum Einsatz
kommt.

## Funktionsweise

* Alle 15 Minuten startet ein GitHub&nbsp;Actions&nbsp;Workflow das
  Python‑Skript `src/monitor.py`.
* Der aktuelle Status wird in `status.json` gespeichert und zusätzlich in
  `history.json` archiviert.
* Änderungen an diesen Dateien werden automatisch committet. Dadurch
  löst jeder Lauf eine Aktualisierung der GitHub&nbsp;Pages‑Seite aus.

## Lokaler Test

```bash
pip install -r requirements.txt
python3 src/monitor.py
```

Die Ergebnisse finden sich anschließend in `status.json` und
`history.json`.
