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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
CONVERTED_DIR = os.path.join(BASE_DIR, 'converted')
LOG_FILE = os.path.join(BASE_DIR, 'conversion.log')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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
def convert_image():
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
        
        with Image.open(input_path) as img:
            target_format = request.form.get('format', 'png').upper()
            if target_format not in ['PNG', 'JPG', 'JPEG']:
                logging.error(f'Ungültiges Zielformat: {target_format}')
                return 'Ungültiges Zielformat', 400

            if img.mode == 'RGBA' and target_format in ['JPG', 'JPEG']:
                img = img.convert('RGB')

            output_filename = f"converted_{uuid.uuid4()}.{target_format.lower()}"
            output_path = os.path.join(CONVERTED_DIR, output_filename)
            img.save(output_path, format=target_format)
            
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