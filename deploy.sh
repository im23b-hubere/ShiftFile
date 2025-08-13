#!/bin/bash

echo "🚀 ShiftFile Vercel Deployment Script"
echo "====================================="

# Prüfe ob Vercel CLI installiert ist
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI ist nicht installiert."
    echo "Installiere es mit: npm i -g vercel"
    exit 1
fi

# Prüfe ob alle notwendigen Dateien vorhanden sind
echo "📁 Prüfe Projektstruktur..."
required_files=("api/index.py" "frontend/index.html" "frontend/script.js" "frontend/style.css" "vercel.json" "requirements.txt")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Fehlende Datei: $file"
        exit 1
    fi
done
echo "✅ Alle notwendigen Dateien gefunden"

# Prüfe Python-Abhängigkeiten
echo "🐍 Prüfe Python-Abhängigkeiten..."
if ! python -c "import flask, PIL" 2>/dev/null; then
    echo "⚠️  Einige Python-Abhängigkeiten fehlen. Installiere sie mit: pip install -r requirements.txt"
fi

# Deploy zu Vercel
echo "🚀 Starte Vercel Deployment..."
vercel --prod

echo "✅ Deployment abgeschlossen!"
echo "📝 Nächste Schritte:"
echo "1. Setze Umgebungsvariablen in Vercel Dashboard (falls benötigt)"
echo "2. Teste die Anwendung unter der bereitgestellten URL"
echo "3. Konfiguriere Custom Domain (optional)"
