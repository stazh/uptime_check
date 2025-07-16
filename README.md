# Uptime Monitor

Diese App überwacht die Verfügbarkeit der Webseite https://www.zentraleserien-hybridesuche.zh.ch und erstellt automatisch einen Status-Report.

## Funktionsweise

- **Automatische Überprüfung**: GitHub Actions führt alle 15 Minuten eine Überprüfung durch
- **Status-Tracking**: Speichert Ergebnisse in `status.json`
- **Historische Daten**: Alle Überprüfungen werden in `history.json` gespeichert
- **Automatische Commits**: Änderungen werden automatisch in das Repository committed

## Dateien

- `src/monitor.py` - Hauptscript für die Überwachung (Python)
- `requirements.txt` - Python-Abhängigkeiten
- `status.json` - Aktueller Status der Webseite
- `history.json` - Historische Daten aller Überprüfungen
- `.github/workflows/monitor.yml` - GitHub Actions Workflow

## Lokale Ausführung

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Uptime-Check ausführen
python3 src/monitor.py
```

## Status

Der aktuelle Status wird automatisch in der `status.json` Datei aktualisiert.

## Verlauf

Alle Überprüfungen werden mit Zeitstempel in der `history.json` Datei gespeichert.

## Setup

1. Repository zu GitHub pushen
2. GitHub Actions wird automatisch aktiviert
3. Der Workflow läuft alle 15 Minuten und überprüft die Webseite
4. Ergebnisse werden automatisch committed
