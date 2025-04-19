#!/bin/bash

# Erstelle temporäres Verzeichnis
mkdir -p /tmp/ffmpeg

# Lade FFmpeg herunter
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz

# Entpacke FFmpeg
cd /tmp
tar xf ffmpeg.tar.xz
mv ffmpeg-*-amd64-static/ffmpeg /tmp/ffmpeg/
mv ffmpeg-*-amd64-static/ffprobe /tmp/ffmpeg/

# Mache die Binärdateien ausführbar
chmod +x /tmp/ffmpeg/ffmpeg
chmod +x /tmp/ffmpeg/ffprobe

# Aufräumen
rm -rf /tmp/ffmpeg.tar.xz /tmp/ffmpeg-*-amd64-static

# Setze Umgebungsvariablen
export FFMPEG_BINARY=/tmp/ffmpeg/ffmpeg
export FFPROBE_BINARY=/tmp/ffmpeg/ffprobe

# Erstelle notwendige Verzeichnisse
mkdir -p /tmp/uploads
mkdir -p /tmp/converted
mkdir -p /tmp/temp

# Teste FFmpeg-Installation
$FFMPEG_BINARY -version 