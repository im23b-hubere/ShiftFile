# ShiftFile

Ein einfaches Webprojekt zur Konvertierung von Bildern zwischen JPG und PNG Formaten.

## Features
- Drag & Drop Bildupload
- Konvertierung zwischen JPG und PNG
- Direkter Download der konvertierten Dateien
- Automatische Bereinigung temporärer Dateien

## Installation

1. Klone das Repository
2. Installiere die Python-Abhängigkeiten:
```bash
pip install -r requirements.txt
```
3. Starte den Server:
```bash
python backend/app.py
```
4. Öffne http://localhost:5000 im Browser

## Projektstruktur
- `frontend/`: Enthält die HTML/CSS/JS Dateien
- `backend/`: Flask-Server und Bildverarbeitung
- `uploads/`: Temporärer Speicher für hochgeladene Dateien
- `converted/`: Temporärer Speicher für konvertierte Dateien
