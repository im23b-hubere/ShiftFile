from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
import logging
from pydub import AudioSegment
import shutil
import tempfile

app = Flask(__name__)

# Konfiguration
UPLOAD_FOLDER = '/tmp/uploads'
CONVERTED_FOLDER = '/tmp/converted'
TEMP_FOLDER = '/tmp/temp'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# Erstelle temporäre Verzeichnisse
for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Erlaubte Dateitypen
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'tiff', 'bmp', 'ico'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'wma'}

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
    
    # Generiere eindeutige Dateinamen
    unique_id = str(uuid.uuid4())
    temp_input_path = os.path.join(TEMP_FOLDER, f"input_{unique_id}.{input_ext}")
    output_filename = f"output_{unique_id}.{target_format.lower()}"
    output_path = os.path.join(CONVERTED_FOLDER, output_filename)
    
    try:
        # Speichere Upload
        file.save(temp_input_path)
        
        # Prüfe Dateityp
        if input_ext in ALLOWED_IMAGE_EXTENSIONS and target_format.lower() in ALLOWED_IMAGE_EXTENSIONS:
            # Bildkonvertierung
            if not optimize_image(temp_input_path, output_path, FORMAT_MAPPING[target_format.lower()]):
                return jsonify({'error': 'Fehler bei der Bildkonvertierung'}), 500
        
        elif input_ext in ALLOWED_AUDIO_EXTENSIONS and target_format.lower() in ALLOWED_AUDIO_EXTENSIONS:
            # Audio-Konvertierung
            try:
                audio = AudioSegment.from_file(temp_input_path, format=input_ext)
                audio.export(output_path, format=target_format.lower())
            except Exception as e:
                logger.error(f"Fehler bei der Audiokonvertierung: {str(e)}")
                return jsonify({'error': 'Fehler bei der Audiokonvertierung'}), 500
        else:
            return jsonify({'error': 'Nicht unterstütztes Dateiformat'}), 400
        
        # Sende konvertierte Datei
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

def process_audio(file, params):
    if not file:
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400
    
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({'error': 'Ungültiger Dateiname'}), 400
    
    input_ext = filename.rsplit('.', 1)[1].lower()
    if input_ext not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({'error': 'Nicht unterstütztes Audioformat'}), 400
    
    # Generiere eindeutige Dateinamen
    unique_id = str(uuid.uuid4())
    temp_input_path = os.path.join(TEMP_FOLDER, f"input_{unique_id}.{input_ext}")
    output_ext = params.get('format', input_ext)
    output_filename = f"output_{unique_id}.{output_ext}"
    output_path = os.path.join(CONVERTED_FOLDER, output_filename)
    
    try:
        # Speichere Upload
        file.save(temp_input_path)
        
        # Lade Audio
        audio = AudioSegment.from_file(temp_input_path, format=input_ext)
        
        # Wende Audioeffekte an
        volume_db = float(params.get('volume', 0))
        speed = float(params.get('speed', 1.0))
        fade_in = int(params.get('fadeIn', 0)) * 1000  # Konvertiere zu Millisekunden
        fade_out = int(params.get('fadeOut', 0)) * 1000
        
        if volume_db != 0:
            audio = audio.apply_gain(volume_db)
        
        if speed != 1.0:
            audio = audio._spawn(audio.raw_data, overrides={
                "frame_rate": int(audio.frame_rate * speed)
            }).set_frame_rate(audio.frame_rate)
        
        if fade_in > 0:
            audio = audio.fade_in(fade_in)
        
        if fade_out > 0:
            audio = audio.fade_out(fade_out)
        
        if params.get('normalize', False):
            audio = audio.normalize()
        
        if params.get('mono', False):
            audio = audio.set_channels(1)
        
        # Exportiere mit spezifischen Einstellungen
        export_params = {}
        if output_ext == 'mp3':
            bitrate = params.get('bitrate', '192k')
            export_params['bitrate'] = bitrate
        
        audio.export(output_path, format=output_ext, **export_params)
        
        # Sende verarbeitete Datei
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    
    except Exception as e:
        logger.error(f"Fehler bei der Audioverarbeitung: {str(e)}")
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

@app.route('/api/process-audio', methods=['POST'])
def process():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei im Request'}), 400
    
    file = request.files['file']
    params = {
        'volume': request.form.get('volume', 0),
        'speed': request.form.get('speed', 1.0),
        'fadeIn': request.form.get('fadeIn', 0),
        'fadeOut': request.form.get('fadeOut', 0),
        'normalize': request.form.get('normalize', 'false').lower() == 'true',
        'mono': request.form.get('mono', 'false').lower() == 'true',
        'format': request.form.get('format'),
        'bitrate': request.form.get('bitrate')
    }
    
    return process_audio(file, params)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200 