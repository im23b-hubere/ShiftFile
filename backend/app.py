import os
from flask import Flask, request, send_file, render_template
from PIL import Image
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import logging
import sys
import atexit
import glob
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
CONVERTED_DIR = os.path.join(BASE_DIR, 'converted')
LOG_FILE = os.path.join(BASE_DIR, 'conversion.log')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'tiff'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_AUDIO_EXTENSIONS)

FORMAT_MAPPING = {
    'JPG': 'JPEG',
    'JPEG': 'JPEG',
    'PNG': 'PNG',
    'WEBP': 'WEBP',
    'GIF': 'GIF',
    'TIFF': 'TIFF'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

for directory in [FRONTEND_DIR, UPLOAD_DIR, CONVERTED_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f'Verzeichnis erstellt: {directory}')
    else:
        logging.info(f'Verzeichnis existiert bereits: {directory}')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def is_audio_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def get_ffmpeg_path():
    """Sucht nach dem FFmpeg-Executable im System"""
    possible_paths = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg.exe",
        "ffmpeg"  
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                return path
        except:
            continue
    
    return None

def convert_audio(input_path, output_path, target_format):
    try:
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            logging.error("FFmpeg wurde nicht gefunden. Bitte installieren Sie FFmpeg.")
            return False
            
        if target_format.lower() == 'mp3':
            command = [ffmpeg_path, '-y', '-i', input_path, '-acodec', 'libmp3lame', '-ab', '192k', output_path]
        else:  
            command = [ffmpeg_path, '-y', '-i', input_path, '-acodec', 'pcm_s16le', output_path]
        
        logging.info(f"Ausführung des Befehls: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f'FFmpeg Fehler: {result.stderr}')
            return False
        return True
    except Exception as e:
        logging.error(f'Fehler bei der Audio-Konvertierung: {str(e)}')
        return False

def clean_old_files():
    """Lösche alte temporäre Dateien"""
    try:
        for folder in [UPLOAD_DIR, CONVERTED_DIR]:
            files = glob.glob(os.path.join(folder, '*'))
            for f in files:
                try:
                    os.remove(f)
                    logging.info(f'Gelöschte temporäre Datei: {f}')
                except Exception as e:
                    logging.warning(f'Konnte Datei nicht löschen: {f} - {str(e)}')
    except Exception as e:
        logging.error(f'Fehler beim Bereinigen der temporären Dateien: {str(e)}')

atexit.register(clean_old_files)

@app.route('/')
def index():
    logging.info('Hauptseite aufgerufen')
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        logging.error(f'Fehler beim Laden der index.html: {str(e)}')
        return f'Fehler beim Laden der Seite: {str(e)}', 500

@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        logging.error('Keine Datei im Request gefunden')
        return 'Keine Datei gefunden', 400
    
    file = request.files['file']
    if file.filename == '':
        logging.error('Leerer Dateiname')
        return 'Keine Datei ausgewählt', 400
    
    if not allowed_file(file.filename):
        logging.error(f'Nicht unterstütztes Format: {file.filename}')
        return 'Nicht unterstütztes Dateiformat', 400

    try:
        input_filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        input_path = os.path.join(UPLOAD_DIR, input_filename)
        
        file.save(input_path)
        logging.info(f'Datei hochgeladen: {file.filename}')
        
        target_format = request.form.get('format', 'png').upper()
        output_filename = f"converted_{uuid.uuid4()}.{target_format.lower()}"
        output_path = os.path.join(CONVERTED_DIR, output_filename)

        if is_image_file(file.filename):
            if target_format not in FORMAT_MAPPING:
                logging.error(f'Ungültiges Bildformat: {target_format}')
                return 'Ungültiges Bildformat', 400

            with Image.open(input_path) as img:
                if img.mode == 'RGBA' and FORMAT_MAPPING[target_format] == 'JPEG':
                    img = img.convert('RGB')
                img.save(output_path, format=FORMAT_MAPPING[target_format])

        elif is_audio_file(file.filename):
            if target_format.lower() not in ALLOWED_AUDIO_EXTENSIONS:
                logging.error(f'Ungültiges Audioformat: {target_format}')
                return 'Ungültiges Audioformat', 400

            if not convert_audio(input_path, output_path, target_format):
                return 'Fehler bei der Audio-Konvertierung', 500

        logging.info(f'Konvertierung erfolgreich: {file.filename} -> {output_filename}')
        
        try:
            os.remove(input_path)
        except Exception as e:
            logging.warning(f'Konnte Upload nicht löschen: {str(e)}')

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"converted_{os.path.splitext(file.filename)[0]}.{target_format.lower()}"
        )

    except Exception as e:
        error_msg = f'Fehler bei der Konvertierung von {file.filename}: {str(e)}'
        logging.error(error_msg)
        return error_msg, 500

if __name__ == '__main__':
    clean_old_files()  
    logging.info('Server gestartet')
    print('Server wird gestartet...')
    print(f'Frontend-Verzeichnis: {FRONTEND_DIR}')
    print('Öffnen Sie http://127.0.0.1:5000 in Ihrem Browser')
    
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,
        use_reloader=True
    ) 