from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
import logging
import tempfile

app = Flask(__name__)

# Konfiguration für Vercel
UPLOAD_FOLDER = '/tmp'  # Vercel erlaubt nur /tmp für Schreibzugriffe
CONVERTED_FOLDER = '/tmp'
TEMP_FOLDER = '/tmp'
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB für Vercel

# Logging-Konfiguration für Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Erlaubte Dateitypen (nur Bilder für bessere Vercel-Kompatibilität)
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'tiff', 'bmp', 'ico'}

# Format-Mapping für Pillow
FORMAT_MAPPING = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'gif': 'GIF',
    'webp': 'WEBP',
    'tiff': 'TIFF',
    'bmp': 'BMP',
    'ico': 'ICO'
}

# Qualitätseinstellungen für verschiedene Bildformate
IMAGE_QUALITY_SETTINGS = {
    'JPEG': {'quality': 92},
    'PNG': {'optimize': True},
    'WEBP': {'quality': 92},
    'GIF': {'optimize': True},
    'TIFF': {'compression': 'tiff_lzw'},
    'BMP': {},
    'ICO': {'sizes': [(32, 32)]}
}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def optimize_image(input_path, output_path, target_format):
    try:
        with Image.open(input_path) as img:
            # Konvertiere RGBA zu RGB für JPEG
            if target_format == 'JPEG' and img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            
            # Spezielle Behandlung für ICO-Format
            if target_format == 'ICO':
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Speichere mit format-spezifischen Einstellungen
            save_kwargs = IMAGE_QUALITY_SETTINGS.get(target_format, {})
            img.save(output_path, format=target_format, **save_kwargs)
            
        return True
    except Exception as e:
        logger.error(f"Fehler bei der Bildoptimierung: {str(e)}")
        return False

def convert_file(file, target_format):
    if not file:
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400
    
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({'error': 'Ungültiger Dateiname'}), 400
    
    input_ext = filename.rsplit('.', 1)[1].lower()
    
    # Generiere eindeutige Dateinamen mit temporärem Verzeichnis
    unique_id = str(uuid.uuid4())
    temp_input_path = os.path.join(TEMP_FOLDER, f"input_{unique_id}.{input_ext}")
    output_filename = f"converted_{secure_filename(file.filename)}"
    output_path = os.path.join(CONVERTED_FOLDER, f"output_{unique_id}.{target_format.lower()}")
    
    try:
        # Speichere Upload
        file.save(temp_input_path)
        logger.info(f"Datei gespeichert: {temp_input_path}")
        
        # Prüfe Dateityp
        if input_ext in ALLOWED_IMAGE_EXTENSIONS and target_format.lower() in ALLOWED_IMAGE_EXTENSIONS:
            # Bildkonvertierung
            logger.info(f"Starte Bildkonvertierung: {input_ext} -> {target_format}")
            if not optimize_image(temp_input_path, output_path, FORMAT_MAPPING[target_format.lower()]):
                return jsonify({'error': 'Fehler bei der Bildkonvertierung'}), 500
        else:
            return jsonify({'error': 'Nicht unterstütztes Dateiformat'}), 400
        
        # Sende konvertierte Datei
        logger.info(f"Sende konvertierte Datei: {output_path}")
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    
    except Exception as e:
        logger.error(f"Fehler bei der Dateikonvertierung: {str(e)}")
        return jsonify({'error': 'Interner Serverfehler'}), 500
    
    finally:
        # Aufräumen
        try:
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            logger.error(f"Fehler beim Aufräumen: {str(e)}")

@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei im Request'}), 400
    
    file = request.files['file']
    target_format = request.form.get('format')
    
    if not target_format:
        return jsonify({'error': 'Kein Zielformat angegeben'}), 400
    
    return convert_file(file, target_format)

@app.route('/api/formats', methods=['GET'])
def get_formats():
    """Get supported formats"""
    return jsonify({
        'image': list(ALLOWED_IMAGE_EXTENSIONS)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Überprüfe Verzeichniszugriffe
        test_file = os.path.join(TEMP_FOLDER, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        return jsonify({
            'status': 'healthy',
            'temp_dir': TEMP_FOLDER,
            'supported_formats': list(ALLOWED_IMAGE_EXTENSIONS)
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 