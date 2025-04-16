#!/bin/bash

# FFmpeg installieren
apt-get update
apt-get install -y ffmpeg

# Python-Abhängigkeiten installieren
pip install -r requirements.txt

# Berechtigungen für FFmpeg setzen
chmod 755 /usr/bin/ffmpeg
chmod 755 /usr/bin/ffprobe

# Verzeichnisse erstellen
mkdir -p /tmp/uploads
mkdir -p /tmp/converted
chmod 777 /tmp/uploads
chmod 777 /tmp/converted 