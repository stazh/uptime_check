# Uptime Monitor

Dieses Projekt prüft regelmässig die Erreichbarkeit der Seite
<https://www.zentraleserien-hybridesuche.zh.ch> und stellt die Ergebnisse
über GitHub Pages bereit.

## Funktionsweise

* Alle 2 Stunden startet ein GitHub&nbsp;Actions&nbsp;Workflow das
  Python‑Skript `src/monitor.py`.
* Der aktuelle Status wird in `status.json` gespeichert und zusätzlich in
  `history.json` archiviert.
* Bei zweimaligem Fehlschlag versucht `monitor.py` automatisch, ein GitHub-Issue anzulegen.
* Hierzu wird das Standard-Token `GITHUB_TOKEN` genutzt, das der Workflow mit den Rechten `contents: write` und `issues: write` bereitstellt.
* Änderungen an diesen Dateien werden automatisch committet. Dadurch
  löst jeder Lauf eine Aktualisierung der GitHub&nbsp;Pages‑Seite aus.

## Lokaler Test

```bash
pip install -r requirements.txt
python3 src/monitor.py
```

Die Ergebnisse finden sich anschliessend in `status.json` und
`history.json`.
