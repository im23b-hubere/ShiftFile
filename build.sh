#!/bin/bash

# FFmpeg installieren
apt-get update && apt-get install -y ffmpeg

# Python-Abhängigkeiten installieren
pip install -r requirements.txt 