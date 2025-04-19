#!/bin/bash

# Erstelle temporäres Verzeichnis
mkdir -p /tmp/ffmpeg

# Lade FFmpeg herunter
curl -L https://github.com/eugeneware/ffmpeg-static/releases/download/b5.0/ffmpeg-linux-x64 -o /tmp/ffmpeg/ffmpeg
curl -L https://github.com/eugeneware/ffmpeg-static/releases/download/b5.0/ffprobe-linux-x64 -o /tmp/ffmpeg/ffprobe

# Mache die Binärdateien ausführbar
chmod +x /tmp/ffmpeg/ffmpeg
chmod +x /tmp/ffmpeg/ffprobe

# Setze Umgebungsvariablen
export FFMPEG_BINARY=/tmp/ffmpeg/ffmpeg
export FFPROBE_BINARY=/tmp/ffmpeg/ffprobe 