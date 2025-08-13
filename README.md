# ShiftFile

Ein einfacher Online-Bildkonverter für die Konvertierung zwischen verschiedenen Bildformaten.

## Features

- Drag & Drop Bildupload
- Konvertierung zwischen JPG, PNG, WEBP, GIF, TIFF, BMP, ICO
- Direkter Download der konvertierten Dateien
- Automatische Bereinigung temporärer Dateien
- Optimiert für Vercel Deployment

## 🚀 Schnelles Deployment auf Vercel

### Voraussetzungen
- Node.js und npm installiert
- Vercel CLI: `npm i -g vercel`

### Deployment-Schritte

1. **Repository klonen:**
```bash
git clone <your-repo-url>
cd ShiftFile-1
```

2. **Deployment ausführen:**
```bash
# Automatisches Deployment-Script verwenden
chmod +x deploy.sh
./deploy.sh

# Oder manuell:
vercel --prod
```

3. **Umgebungsvariablen setzen (optional):**
   - Gehe zu deinem Vercel Dashboard
   - Wähle dein Projekt
   - Unter "Settings" → "Environment Variables"
   - Füge hinzu: `CLOUDCONVERT_API_KEY` (falls Audio-Konvertierung später hinzugefügt wird)

### Lokale Entwicklung

1. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

2. **Server starten:**
```bash
python backend/app.py
```

3. **Browser öffnen:**
```
http://localhost:5000
```

## Projektstruktur

```
ShiftFile-1/
├── api/
│   └── index.py          # Vercel API-Endpunkte
├── frontend/
│   ├── index.html        # Hauptseite
│   ├── script.js         # Frontend-Logik
│   ├── style.css         # Styling
│   ├── datenschutz.html  # Datenschutz
│   └── impressum.html    # Impressum
├── backend/
│   └── app.py            # Lokaler Flask-Server
├── vercel.json           # Vercel-Konfiguration
├── requirements.txt      # Python-Abhängigkeiten
├── deploy.sh            # Deployment-Script
└── env.example          # Beispiel-Umgebungsvariablen
```

## Technische Details

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: Flask (Python)
- **Bildverarbeitung**: Pillow (PIL)
- **Deployment**: Vercel Serverless Functions
- **Dateigrößen-Limit**: 10MB (Vercel-Optimiert)

## Unterstützte Formate

### Eingabe
- JPG/JPEG
- PNG
- WEBP
- GIF
- TIFF
- BMP
- ICO

### Ausgabe
- JPG/JPEG
- PNG
- WEBP
- GIF
- TIFF
- BMP
- ICO

## Vercel-spezifische Optimierungen

- Reduzierte Dateigrößen-Limits (10MB)
- Entfernung von FFmpeg-Abhängigkeiten
- Optimierte Lambda-Funktion-Konfiguration
- Verwendung von `/tmp` Verzeichnis für temporäre Dateien

## Lizenz

© 2024 ShiftFile - Kostenloser Online-Bildkonverter
